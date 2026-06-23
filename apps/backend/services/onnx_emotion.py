"""Pluggable ONNX facial-emotion classifier.

This is the production "real ML" path. The signal classifier in
``vision_signal.py`` recovers fatigue/gaze but deliberately does not fabricate a
facial *emotion*; a trained model does. Rather than pull in a multi-gigabyte
PyTorch stack, we run inference through ONNX Runtime (a small, fast, CPU-capable
engine) against an exported FER model.

Usage: export any facial-emotion classifier to ONNX (e.g. convert
``dima806/facial_emotions_image_detection`` or an FER-2013 CNN) and point
``settings.vision_onnx_model_path`` at the ``.onnx`` file. The classifier
introspects the model's expected input shape, preprocesses the frame to match
(grayscale vs RGB, target H×W, NCHW vs NHWC), runs inference, and softmaxes the
logits into a labelled emotion + confidence.

Everything is defensive: if onnxruntime is missing, the file is absent, or
inference fails for any reason, ``load()`` / ``classify()`` return ``None`` and
the pipeline falls back to the signal classifier. This keeps the default test
suite hermetic (no model download required) while making the swap-in real.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from models.emotion import VisionResult

logger = logging.getLogger(__name__)

# FER-2013 / HuggingFace facial-emotion label order (override via constructor).
DEFAULT_FER_LABELS = ("angry", "disgust", "fear", "happy", "sad", "surprise", "neutral")

# FER+ (ONNX Model Zoo emotion-ferplus) output order, mapped to the fusion
# service's emotion vocabulary (happiness→happy, sadness→sad, anger→angry).
# FER+ also expects raw 0–255 pixel values, so it sets pixel_scale=1.0 below.
FERPLUS_LABELS = ("neutral", "happy", "surprise", "sad", "angry", "disgust", "fear", "contempt")


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)


class OnnxVisionClassifier:
    """Runs a facial-emotion ONNX model, with graceful failure to None.

    ``labels`` and ``pixel_scale`` may be given explicitly. When left as
    ``None`` they are auto-selected after the model loads based on the number of
    output classes, so the two common pretrained models work with nothing more
    than a model path:

    * 8 classes → FER+ (``FERPLUS_LABELS``, raw 0–255 input);
    * otherwise → FER-2013 order with ``[0, 1]``-scaled input.
    """

    def __init__(
        self,
        model_path: str,
        labels: tuple[str, ...] | None = None,
        pixel_scale: float | None = None,
    ) -> None:
        self._model_path = model_path
        self._labels = labels          # None → auto-select on load
        self._pixel_scale = pixel_scale  # None → auto-select on load
        self._session = None
        self._input_name: str | None = None
        self._input_shape: tuple | None = None

    def load(self) -> bool:
        """Attempt to load the ONNX model. Returns False on any failure."""
        path = Path(self._model_path)
        if not path.is_file():
            logger.info("ONNX vision model not found at %s — using signal classifier", path)
            return False
        try:
            import onnxruntime as ort  # lazy: optional dependency

            self._session = ort.InferenceSession(
                str(path), providers=["CPUExecutionProvider"]
            )
            inp = self._session.get_inputs()[0]
            self._input_name = inp.name
            self._input_shape = tuple(inp.shape)
            self._auto_configure()
            logger.info(
                "Loaded ONNX vision model %s input=%s classes=%d scale=%s",
                path.name, self._input_shape, len(self._labels), self._pixel_scale,
            )
            return True
        except Exception:
            logger.exception("Failed to load ONNX vision model %s", path)
            self._session = None
            return False

    def _auto_configure(self) -> None:
        """Pick labels / pixel scaling from the model when not set explicitly."""
        num_classes = None
        try:
            out_shape = self._session.get_outputs()[0].shape
            if out_shape and isinstance(out_shape[-1], int):
                num_classes = out_shape[-1]
        except Exception:
            pass

        if self._labels is None:
            self._labels = FERPLUS_LABELS if num_classes == 8 else DEFAULT_FER_LABELS
        if self._pixel_scale is None:
            # FER+ consumes raw 0–255; most other FER models expect [0, 1].
            self._pixel_scale = 1.0 if num_classes == 8 else 255.0

    @property
    def ready(self) -> bool:
        return self._session is not None

    def _target_hw_and_channels(self) -> tuple[int, int, int, str]:
        """Infer (H, W, channels, layout) from the model's input shape."""
        shape = self._input_shape or (1, 3, 48, 48)
        dims = [d if isinstance(d, int) and d > 0 else None for d in shape]
        # Common layouts: NCHW (1,C,H,W) or NHWC (1,H,W,C).
        if len(dims) == 4:
            if dims[1] in (1, 3):  # NCHW
                c, h, w = dims[1], dims[2] or 48, dims[3] or 48
                return h, w, c, "NCHW"
            if dims[3] in (1, 3):  # NHWC
                h, w, c = dims[1] or 48, dims[2] or 48, dims[3]
                return h, w, c, "NHWC"
        return 48, 48, 1, "NCHW"

    def classify(self, rgb: np.ndarray) -> VisionResult | None:
        """Run inference on an HxWx3 (or HxW) array. Returns None on failure."""
        if self._session is None:
            return None
        try:
            from PIL import Image

            h, w, channels, layout = self._target_hw_and_channels()
            arr = np.asarray(rgb)
            mode = "L" if channels == 1 else "RGB"
            if arr.ndim == 2:
                img = Image.fromarray(arr.astype(np.uint8), mode="L").convert(mode)
            else:
                img = Image.fromarray(arr.astype(np.uint8), mode="RGB").convert(mode)
            img = img.resize((w, h))

            x = np.asarray(img, dtype=np.float32) / (self._pixel_scale or 255.0)
            if channels == 1 and x.ndim == 2:
                x = x[..., None]
            if layout == "NCHW":
                x = np.transpose(x, (2, 0, 1))
            x = x[None, ...]  # batch dim

            outputs = self._session.run(None, {self._input_name: x})
            logits = np.asarray(outputs[0]).reshape(-1)
            probs = _softmax(logits)
            idx = int(np.argmax(probs))
            label = self._labels[idx] if idx < len(self._labels) else "neutral"
            return VisionResult(
                emotion=label,
                confidence=round(float(probs[idx]), 3),
                fatigue_score=0.0,  # filled in by the signal classifier
                gaze_direction="center",
                landmarks_detected=True,
            )
        except Exception:
            logger.exception("ONNX vision inference failed; falling back")
            return None
