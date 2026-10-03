from __future__ import annotations

from dataclasses import dataclass, replace
from math import log
from typing import Sequence

import numpy as np

from .mechanisms import BasisTerm, build_terms, design_matrix


@dataclass(frozen=True)
class CompiledMechanism:
    terms: tuple[BasisTerm, ...]
    coefficients: np.ndarray
    intercept: float
    score: float
    mse: float
    posterior: float = 0.0

    @property
    def term_names(self) -> tuple[str, ...]:
        return tuple(term.name for term in self.terms)

    @property
    def complexity(self) -> int:
        return 1 + sum(term.complexity for term in self.terms)

    def predict(self, x: np.ndarray) -> np.ndarray:
        z = design_matrix(np.asarray(x, dtype=float), list(self.terms))
        if z.shape[1] == 0:
            return np.full(len(x), self.intercept, dtype=float)
        return self.intercept + z @ self.coefficients

    def as_program(self, precision: int = 3) -> str:
        pieces = [f"{self.intercept:.{precision}f}"]
        for coefficient, term in zip(self.coefficients, self.terms):
            sign = "+" if coefficient >= 0 else "-"
            pieces.append(f" {sign} {abs(coefficient):.{precision}f}*{term.name}")
        return "y =" + "".join(pieces)


@dataclass(frozen=True)
class CompilerResult:
    feature_names: tuple[str, ...]
    models: tuple[CompiledMechanism, ...]

    @property
    def best(self) -> CompiledMechanism:
        return self.models[0]

    def ensemble_predictions(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(x, dtype=float)
        preds = np.vstack([model.predict(x) for model in self.models])
        weights = np.asarray([model.posterior for model in self.models], dtype=float)
        if not np.isfinite(weights).all() or weights.sum() <= 0:
            weights = np.full(len(self.models), 1 / len(self.models))
        else:
            weights = weights / weights.sum()
        return preds, weights


class MechanismCompiler:
    """Searches for compact executable mechanisms using an MDL/BIC-like objective.

    The compiler deliberately searches a small symbolic language instead of fitting an
    unrestricted black-box predictor. This makes the recovered mechanism inspectable,
    testable and comparable across regimes.
    """

    def __init__(
        self,
        *,
        max_terms: int = 4,
        beam_width: int = 32,
        top_k: int = 16,
        complexity_penalty: float = 0.55,
        interactions: bool = True,
        squares: bool = True,
        posterior_temperature: float = 12.0,
    ) -> None:
        self.max_terms = max_terms
        self.beam_width = beam_width
        self.top_k = top_k
        self.complexity_penalty = complexity_penalty
        self.interactions = interactions
        self.squares = squares
        self.posterior_temperature = posterior_temperature

    def _fit_subset(
        self,
        x: np.ndarray,
        y: np.ndarray,
        terms: list[BasisTerm],
        subset: tuple[int, ...],
    ) -> CompiledMechanism:
        chosen = [terms[i] for i in subset]
        z = design_matrix(x, chosen)
        a = np.column_stack([np.ones(len(x)), z])
        beta, *_ = np.linalg.lstsq(a, y, rcond=None)
        pred = a @ beta
        mse = float(np.mean((y - pred) ** 2))
        complexity = 1 + sum(term.complexity for term in chosen)
        score = len(y) * log(max(mse, 1e-12)) + self.complexity_penalty * complexity * log(max(len(y), 2))
        return CompiledMechanism(
            terms=tuple(chosen),
            coefficients=np.asarray(beta[1:], dtype=float),
            intercept=float(beta[0]),
            score=float(score),
            mse=mse,
        )

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        feature_names: Sequence[str],
    ) -> CompilerResult:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        if x.ndim != 2:
            raise ValueError("x must be a 2D array")
        if len(x) != len(y):
            raise ValueError("x and y must contain the same number of rows")
        if x.shape[1] != len(feature_names):
            raise ValueError("feature_names must match x columns")
        if len(y) < 8:
            raise ValueError("At least 8 observations are required")

        terms = build_terms(
            feature_names,
            interactions=self.interactions,
            squares=self.squares,
        )

        beam: list[tuple[int, ...]] = [tuple()]
        all_models: dict[tuple[int, ...], CompiledMechanism] = {}

        constant = self._fit_subset(x, y, terms, tuple())
        all_models[tuple()] = constant

        for _depth in range(1, self.max_terms + 1):
            expanded: set[tuple[int, ...]] = set()
            for subset in beam:
                start = subset[-1] + 1 if subset else 0
                for idx in range(start, len(terms)):
                    expanded.add(subset + (idx,))

            scored: list[tuple[float, tuple[int, ...]]] = []
            for subset in expanded:
                model = self._fit_subset(x, y, terms, subset)
                all_models[subset] = model
                scored.append((model.score, subset))
            scored.sort(key=lambda item: item[0])
            beam = [subset for _, subset in scored[: self.beam_width]]
            if not beam:
                break

        ranked = sorted(all_models.values(), key=lambda model: model.score)[: self.top_k]
        scores = np.asarray([model.score for model in ranked], dtype=float)
        temperature = max(self.posterior_temperature, 1e-6)
        shifted = -0.5 * (scores - scores.min()) / temperature
        shifted -= shifted.max()
        weights = np.exp(np.clip(shifted, -80, 0))
        weights /= weights.sum()
        ranked = [replace(model, posterior=float(weight)) for model, weight in zip(ranked, weights)]
        return CompilerResult(feature_names=tuple(feature_names), models=tuple(ranked))
