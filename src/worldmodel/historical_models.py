from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence
import warnings

import numpy as np
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .compiler import MechanismCompiler, CompilerResult


_Z80 = 1.2815515655446004


@dataclass(frozen=True)
class PredictionBundle:
    mean: np.ndarray
    low: np.ndarray
    high: np.ndarray
    sigma: np.ndarray


class FingerprintModel(Protocol):
    name: str

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        feature_names: Sequence[str],
        outcome_names: Sequence[str],
    ) -> "FingerprintModel": ...

    def predict(self, x: np.ndarray) -> PredictionBundle: ...


def _residual_scale(y: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    residuals = np.asarray(y, dtype=float) - np.asarray(prediction, dtype=float)
    if residuals.ndim == 1:
        residuals = residuals[:, None]
    ddof = 1 if len(residuals) > 1 else 0
    sigma = residuals.std(axis=0, ddof=ddof)
    return np.maximum(sigma, 1e-4)


class HistoricalMechanismModel:
    name = "rmc"

    def __init__(
        self,
        *,
        max_terms: int = 5,
        beam_width: int = 40,
        top_k: int = 12,
        complexity_penalty: float = 0.65,
    ) -> None:
        self.compiler_kwargs = {
            "max_terms": max_terms,
            "beam_width": beam_width,
            "top_k": top_k,
            "complexity_penalty": complexity_penalty,
        }
        self.results: list[CompilerResult] = []
        self.residual_sigma: np.ndarray | None = None

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        feature_names: Sequence[str],
        outcome_names: Sequence[str],
    ) -> "HistoricalMechanismModel":
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if y.ndim == 1:
            y = y[:, None]

        self.results = []
        train_prediction = np.zeros_like(y, dtype=float)
        for column in range(y.shape[1]):
            result = MechanismCompiler(**self.compiler_kwargs).fit(
                x,
                y[:, column],
                feature_names,
            )
            self.results.append(result)
            preds, weights = result.ensemble_predictions(x)
            train_prediction[:, column] = np.sum(
                preds * weights[:, None],
                axis=0,
            )

        self.residual_sigma = _residual_scale(y, train_prediction)
        return self

    def predict(self, x: np.ndarray) -> PredictionBundle:
        if not self.results or self.residual_sigma is None:
            raise RuntimeError("Model must be fitted before prediction")

        x = np.asarray(x, dtype=float)
        if x.ndim == 1:
            x = x[None, :]

        means: list[np.ndarray] = []
        lows: list[np.ndarray] = []
        highs: list[np.ndarray] = []
        sigmas: list[np.ndarray] = []

        for column, result in enumerate(self.results):
            preds, weights = result.ensemble_predictions(x)
            mean = np.sum(preds * weights[:, None], axis=0)
            epistemic_var = np.sum(
                weights[:, None] * (preds - mean[None, :]) ** 2,
                axis=0,
            )
            total_sigma = np.sqrt(
                epistemic_var + float(self.residual_sigma[column]) ** 2
            )
            means.append(mean)
            sigmas.append(total_sigma)
            lows.append(mean - _Z80 * total_sigma)
            highs.append(mean + _Z80 * total_sigma)

        return PredictionBundle(
            mean=np.column_stack(means),
            low=np.column_stack(lows),
            high=np.column_stack(highs),
            sigma=np.column_stack(sigmas),
        )

    def programs(self) -> list[str]:
        return [result.best.as_program() for result in self.results]


class SklearnFingerprintModel:
    def __init__(self, name: str, estimator) -> None:
        self.name = name
        self._template = estimator
        self.estimator = None
        self.residual_sigma: np.ndarray | None = None

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        feature_names: Sequence[str],
        outcome_names: Sequence[str],
    ) -> "SklearnFingerprintModel":
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if y.ndim == 1:
            y = y[:, None]
        self.estimator = clone(self._template)
        # The MLP is only a comparison baseline. On small synthetic replay samples
        # sklearn can hit the LBFGS iteration ceiling even when its fitted predictions
        # are perfectly usable for the benchmark. Keep the console focused on Rook's
        # own failures while preserving the baseline result itself.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            self.estimator.fit(x, y)
        prediction = np.asarray(self.estimator.predict(x), dtype=float)
        if prediction.ndim == 1:
            prediction = prediction[:, None]
        self.residual_sigma = _residual_scale(y, prediction)
        return self

    def predict(self, x: np.ndarray) -> PredictionBundle:
        if self.estimator is None or self.residual_sigma is None:
            raise RuntimeError("Model must be fitted before prediction")
        x = np.asarray(x, dtype=float)
        if x.ndim == 1:
            x = x[None, :]
        mean = np.asarray(self.estimator.predict(x), dtype=float)
        if mean.ndim == 1:
            mean = mean[:, None]
        sigma = np.broadcast_to(self.residual_sigma, mean.shape).copy()
        return PredictionBundle(
            mean=mean,
            low=mean - _Z80 * sigma,
            high=mean + _Z80 * sigma,
            sigma=sigma,
        )


class LocalLevelFingerprintModel:
    """Small local-level state-space baseline that ignores event features."""

    name = "local_level"

    def __init__(self, process_ratio: float = 0.08) -> None:
        self.process_ratio = float(process_ratio)
        self.state: np.ndarray | None = None
        self.sigma: np.ndarray | None = None

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        feature_names: Sequence[str],
        outcome_names: Sequence[str],
    ) -> "LocalLevelFingerprintModel":
        y = np.asarray(y, dtype=float)
        if y.ndim == 1:
            y = y[:, None]
        state = y[0].copy()
        measurement_var = np.maximum(y.var(axis=0), 1e-5)
        process_var = self.process_ratio * measurement_var
        covariance = measurement_var.copy()

        innovations: list[np.ndarray] = []
        for observation in y[1:]:
            covariance = covariance + process_var
            gain = covariance / (covariance + measurement_var)
            innovation = observation - state
            state = state + gain * innovation
            covariance = (1.0 - gain) * covariance
            innovations.append(innovation)

        self.state = state
        if innovations:
            self.sigma = np.maximum(np.std(np.vstack(innovations), axis=0), 1e-4)
        else:
            self.sigma = np.sqrt(measurement_var)
        return self

    def predict(self, x: np.ndarray) -> PredictionBundle:
        if self.state is None or self.sigma is None:
            raise RuntimeError("Model must be fitted before prediction")
        x = np.asarray(x, dtype=float)
        rows = 1 if x.ndim == 1 else len(x)
        mean = np.tile(self.state, (rows, 1))
        sigma = np.tile(self.sigma, (rows, 1))
        return PredictionBundle(
            mean=mean,
            low=mean - _Z80 * sigma,
            high=mean + _Z80 * sigma,
            sigma=sigma,
        )


def build_historical_models(seed: int = 7) -> dict[str, FingerprintModel]:
    return {
        "rmc": HistoricalMechanismModel(),
        "ridge": SklearnFingerprintModel(
            "ridge",
            make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        ),
        "random_forest": SklearnFingerprintModel(
            "random_forest",
            RandomForestRegressor(
                n_estimators=220,
                max_depth=6,
                min_samples_leaf=3,
                random_state=seed,
                n_jobs=1,
            ),
        ),
        "mlp": SklearnFingerprintModel(
            "mlp",
            make_pipeline(
                StandardScaler(),
                MLPRegressor(
                    hidden_layer_sizes=(24, 12),
                    activation="tanh",
                    solver="lbfgs",
                    alpha=0.01,
                    max_iter=800,
                    random_state=seed,
                ),
            ),
        ),
        "local_level": LocalLevelFingerprintModel(),
    }
