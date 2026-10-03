from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RegimeBreak:
    index: int | None
    score: float
    detected: bool


class ResidualRegimeDetector:
    """Detect a structural break from a rise in model error around a boundary."""

    def __init__(self, window: int = 24, threshold: float = 2.4) -> None:
        self.window = window
        self.threshold = threshold

    def detect(self, residuals: np.ndarray) -> RegimeBreak:
        r = np.abs(np.asarray(residuals, dtype=float).reshape(-1))
        if len(r) < self.window * 2 + 1:
            return RegimeBreak(index=None, score=0.0, detected=False)

        best_index = None
        best_score = -np.inf
        w = self.window
        for boundary in range(w, len(r) - w):
            before = r[boundary - w : boundary]
            after = r[boundary : boundary + w]
            pooled = np.sqrt((before.var(ddof=1) + after.var(ddof=1)) / 2 + 1e-9)
            score = (after.mean() - before.mean()) / (pooled / np.sqrt(w))
            if score > best_score:
                best_score = float(score)
                best_index = boundary

        detected = bool(best_score >= self.threshold)
        return RegimeBreak(
            index=int(best_index) if detected and best_index is not None else None,
            score=float(best_score if np.isfinite(best_score) else 0.0),
            detected=detected,
        )
