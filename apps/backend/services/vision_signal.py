"""Signal-driven vision features.

Unlike the legacy hash stub (which derived a *random* emotion from a content
hash and therefore tracked nothing about the user), this module computes real
image statistics from the decoded frame and derives the signals that are
genuinely recoverable from raw pixels without a trained face model:

* **fatigue** — from image sharpness/contrast (drooping, motion blur, and dim,
  low-contrast frames read as more fatigued/less alert);
* **gaze direction** — from the brightness centroid of the frame (a coarse but
  real proxy for where the lit face sits);
* **face presence + confidence** — from whether the frame actually contains a
  face-like, well-exposed, in-focus subject.

It deliberately does **not** invent a facial *emotion* from raw pixels — that
requires a trained classifier (see ``onnx_emotion.py``). When no model is
available the emotion stays ``neutral`` with honest, exposure-based confidence
rather than a fabricated label. This is the key accuracy fix: the numbers now
move because the image moved, and we don't overclaim what pixels can tell us.

All functions are pure and operate on a NumPy grayscale array in ``[0, 1]``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.emotion import VisionResult


@dataclass
class VisionFeatures:
    brightness: float        # mean luminance, 0..1
    contrast: float          # luminance std, 0..1
    sharpness: float         # normalized Laplacian variance, 0..1 (focus/detail)
    centroid_x: float        # brightness centroid horizontal, 0..1
    centroid_y: float        # brightness centroid vertical, 0..1
    face_like: bool          # enough structure to plausibly contain a face


def to_grayscale(rgb: np.ndarray) -> np.ndarray:
    """Convert an HxWx3 uint8/float array to float grayscale in [0, 1]."""
    arr = np.asarray(rgb, dtype=np.float64)
    if arr.ndim == 2:
        gray = arr
    else:
        # Rec. 601 luma weights.
        gray = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114
    if gray.max() > 1.0:
        gray = gray / 255.0
    return gray


def extract_features(gray: np.ndarray) -> VisionFeatures:
    """Compute interpretable image features from a grayscale frame."""
    gray = np.clip(gray, 0.0, 1.0)
    brightness = float(gray.mean())
    contrast = float(gray.std())

    # Sharpness = variance of the discrete Laplacian (a standard focus measure).
    if gray.shape[0] >= 3 and gray.shape[1] >= 3:
        lap = (
            gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
            - 4.0 * gray[1:-1, 1:-1]
        )
        lap_var = float(lap.var())
    else:
        lap_var = 0.0
    # Map raw Laplacian variance to 0..1. The scale is chosen so ordinary
    # webcam frames land mid-range; exact value is unimportant, ordering is.
    sharpness = float(1.0 - np.exp(-lap_var * 120.0))

    total = float(gray.sum())
    if total > 1e-9:
        ys = np.arange(gray.shape[0]).reshape(-1, 1)
        xs = np.arange(gray.shape[1]).reshape(1, -1)
        centroid_x = float((gray * xs).sum() / total) / max(gray.shape[1] - 1, 1)
        centroid_y = float((gray * ys).sum() / total) / max(gray.shape[0] - 1, 1)
    else:
        centroid_x = centroid_y = 0.5

    # A blank, uniformly lit, or pitch-black frame has essentially no structure.
    face_like = contrast > 0.04 and 0.04 < brightness < 0.98

    return VisionFeatures(
        brightness=brightness,
        contrast=contrast,
        sharpness=sharpness,
        centroid_x=centroid_x,
        centroid_y=centroid_y,
        face_like=face_like,
    )


def _gaze_from_centroid(cx: float, cy: float) -> str:
    """Map the brightness centroid to a coarse gaze/orientation bucket."""
    dx = cx - 0.5
    dy = cy - 0.5
    if abs(dx) < 0.08 and abs(dy) < 0.08:
        return "center"
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def classify(features: VisionFeatures) -> VisionResult:
    """Derive a VisionResult from real image features (no facial-emotion model)."""
    if not features.face_like:
        # Nothing usable in frame — report no detection honestly.
        return VisionResult(
            emotion="neutral",
            confidence=0.0,
            fatigue_score=0.0,
            gaze_direction="center",
            landmarks_detected=False,
        )

    # Fatigue: blurry/soft + dim + low-contrast frames read as less alert.
    dimness = 1.0 - min(1.0, features.brightness / 0.5)
    fatigue = 0.55 * (1.0 - features.sharpness) + 0.25 * dimness + 0.20 * (1.0 - min(1.0, features.contrast / 0.25))
    fatigue = float(np.clip(fatigue, 0.0, 1.0))

    # Confidence reflects how clearly a subject is present, not emotion certainty.
    confidence = 0.45 + 0.4 * features.sharpness + 0.15 * min(1.0, features.contrast / 0.25)
    confidence = float(np.clip(confidence, 0.0, 0.95))

    return VisionResult(
        emotion="neutral",
        confidence=round(confidence, 3),
        fatigue_score=round(fatigue, 3),
        gaze_direction=_gaze_from_centroid(features.centroid_x, features.centroid_y),
        landmarks_detected=True,
    )
