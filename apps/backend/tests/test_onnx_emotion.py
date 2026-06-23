"""Tests for the pluggable ONNX facial-emotion classifier.

These exercise the *real* inference plumbing: a tiny ONNX model is built on the
fly (no external download) and run through OnnxVisionClassifier and the
VisionService integration. Tests skip cleanly when onnxruntime/onnx are absent,
keeping the default suite hermetic.
"""

from __future__ import annotations

import base64
import io
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ort = pytest.importorskip("onnxruntime")
onnx = pytest.importorskip("onnx")

from services.onnx_emotion import DEFAULT_FER_LABELS, FERPLUS_LABELS, OnnxVisionClassifier
from services.vision_service import VisionService

_FERPLUS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "ml_models", "emotion-ferplus-8.onnx"
)


def _build_tiny_fer_model(path, h=48, w=48, num_labels=7, bias_index=3):
    """Build a minimal NCHW grayscale→logits ONNX model.

    The model flattens the input and applies a fixed linear layer whose bias
    strongly favors ``bias_index`` so argmax is deterministic — enough to prove
    preprocessing + inference + softmax wiring works end to end.
    """
    from onnx import TensorProto, helper, numpy_helper

    inp = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 1, h, w])
    out = helper.make_tensor_value_info("logits", TensorProto.FLOAT, [1, num_labels])

    weight = np.zeros((h * w, num_labels), dtype=np.float32)
    bias = np.zeros((num_labels,), dtype=np.float32)
    bias[bias_index] = 10.0

    reshape_shape = numpy_helper.from_array(np.array([1, h * w], dtype=np.int64), name="shape")
    w_init = numpy_helper.from_array(weight, name="W")
    b_init = numpy_helper.from_array(bias, name="B")

    reshape = helper.make_node("Reshape", ["input", "shape"], ["flat"])
    matmul = helper.make_node("MatMul", ["flat", "W"], ["mm"])
    add = helper.make_node("Add", ["mm", "B"], ["logits"])

    graph = helper.make_graph(
        [reshape, matmul, add], "tiny_fer", [inp], [out],
        initializer=[reshape_shape, w_init, b_init],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 9
    onnx.save(model, str(path))
    return path


def _jpeg_b64(arr: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), mode="RGB").save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()


def _structured_frame() -> np.ndarray:
    base = np.indices((120, 120)).sum(axis=0) % 2
    return np.where(base[..., None] == 0, 210, 90).repeat(3, axis=2)


class TestOnnxVisionClassifier:
    def test_missing_model_does_not_load(self, tmp_path):
        clf = OnnxVisionClassifier(str(tmp_path / "nope.onnx"))
        assert clf.load() is False
        assert clf.ready is False
        assert clf.classify(np.zeros((48, 48, 3), dtype=np.uint8)) is None

    def test_loads_and_infers(self, tmp_path):
        model_path = _build_tiny_fer_model(tmp_path / "tiny.onnx", bias_index=3)
        clf = OnnxVisionClassifier(str(model_path))
        assert clf.load() is True
        assert clf.ready is True

        result = clf.classify(np.full((120, 120, 3), 200, dtype=np.uint8))
        assert result is not None
        # bias_index=3 → "happy" in the default FER label order.
        assert result.emotion == DEFAULT_FER_LABELS[3]
        assert 0.0 <= result.confidence <= 1.0
        assert result.landmarks_detected is True


class TestVisionServiceWithOnnx:
    def test_service_layers_onnx_emotion_over_signal(self, tmp_path):
        model_path = _build_tiny_fer_model(tmp_path / "tiny.onnx", bias_index=0)
        service = VisionService(onnx_model_path=str(model_path))

        result = service.infer(_jpeg_b64(_structured_frame()))
        # Emotion comes from the ONNX model (bias_index=0 → "angry")...
        assert result.emotion == DEFAULT_FER_LABELS[0]
        # ...while fatigue/gaze still come from the real signal classifier.
        assert result.landmarks_detected is True
        assert 0.0 <= result.fatigue_score <= 1.0

    def test_service_without_model_uses_signal(self, tmp_path):
        service = VisionService(onnx_model_path=str(tmp_path / "absent.onnx"))
        result = service.infer(_jpeg_b64(_structured_frame()))
        # No model loaded → signal classifier keeps emotion neutral.
        assert result.emotion == "neutral"


@pytest.mark.skipif(
    not os.path.isfile(_FERPLUS_PATH),
    reason="real FER+ model not downloaded (ml_models/emotion-ferplus-8.onnx)",
)
class TestRealFerPlusModel:
    """Exercises the actual downloaded FER+ model end to end."""

    def test_auto_configures_ferplus(self):
        clf = OnnxVisionClassifier(_FERPLUS_PATH)
        assert clf.load() is True
        # 8-class output → FER+ labels and raw 0–255 input, auto-detected.
        assert clf._labels == FERPLUS_LABELS
        assert clf._pixel_scale == 1.0

    def test_real_inference_returns_valid_label(self):
        clf = OnnxVisionClassifier(_FERPLUS_PATH)
        clf.load()
        result = clf.classify(np.full((120, 120, 3), 160, dtype=np.uint8))
        assert result is not None
        assert result.emotion in FERPLUS_LABELS
        assert 0.0 <= result.confidence <= 1.0

    def test_vision_service_uses_real_model(self):
        service = VisionService(onnx_model_path=_FERPLUS_PATH)
        result = service.infer(_jpeg_b64(_structured_frame()))
        # Emotion comes from the real model; fatigue/gaze from the signal path.
        assert result.emotion in FERPLUS_LABELS
        assert result.landmarks_detected is True
        assert 0.0 <= result.fatigue_score <= 1.0
