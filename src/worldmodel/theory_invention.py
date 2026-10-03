from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .compiler import MechanismCompiler


@dataclass(frozen=True)
class InventedTheory:
    program: str
    terms: tuple[str, ...]
    baseline_mse: float
    augmented_mse: float
    relative_improvement: float
    accepted: bool


class ResidualTheoryInventor:
    """Invent a compact correction when all incumbent mechanisms fail.

    Instead of forcing a winner from a closed hypothesis set, the inventor models the
    systematic residual left by an incumbent prediction. The correction is itself an
    executable symbolic program, so the proposed new theory is inspectable and can be
    preregistered before a new holdout test.
    """

    def __init__(
        self,
        *,
        max_terms: int = 4,
        beam_width: int = 48,
        top_k: int = 16,
        min_relative_improvement: float = 0.20,
    ) -> None:
        self.compiler = MechanismCompiler(
            max_terms=max_terms,
            beam_width=beam_width,
            top_k=top_k,
            interactions=True,
            squares=True,
        )
        self.min_relative_improvement = float(min_relative_improvement)

    def invent(
        self,
        x: np.ndarray,
        y: np.ndarray,
        baseline_prediction: np.ndarray,
        feature_names: list[str] | tuple[str, ...],
        *,
        train_fraction: float = 0.7,
    ) -> InventedTheory:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        baseline = np.asarray(baseline_prediction, dtype=float).reshape(-1)
        if x.ndim != 2 or len(x) != len(y) or len(y) != len(baseline):
            raise ValueError("x, y and baseline_prediction must align")
        if len(y) < 40:
            raise ValueError("at least 40 observations are required")

        split = max(24, int(len(y) * train_fraction))
        split = min(split, len(y) - 8)
        residual = y - baseline
        compiled = self.compiler.fit(
            x[:split],
            residual[:split],
            feature_names,
        )
        model = compiled.best
        correction = model.predict(x[split:])
        augmented = baseline[split:] + correction

        baseline_mse = float(np.mean((y[split:] - baseline[split:]) ** 2))
        augmented_mse = float(np.mean((y[split:] - augmented) ** 2))
        improvement = (
            (baseline_mse - augmented_mse) / max(baseline_mse, 1e-12)
        )
        return InventedTheory(
            program=model.as_program(),
            terms=model.term_names,
            baseline_mse=baseline_mse,
            augmented_mse=augmented_mse,
            relative_improvement=float(improvement),
            accepted=bool(improvement >= self.min_relative_improvement),
        )

    def invent_if_unknown(
        self,
        *,
        unknown_probability: float,
        x: np.ndarray,
        y: np.ndarray,
        baseline_prediction: np.ndarray,
        feature_names: list[str] | tuple[str, ...],
        threshold: float = 0.5,
    ) -> InventedTheory | None:
        if unknown_probability < threshold:
            return None
        return self.invent(x, y, baseline_prediction, feature_names)
