from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class BasisTerm:
    """A tiny executable piece of a candidate world mechanism."""

    name: str
    kind: str
    indices: tuple[int, ...]
    complexity: int

    def evaluate(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        if self.kind == "identity":
            return x[:, self.indices[0]]
        if self.kind == "square":
            col = x[:, self.indices[0]]
            return col * col
        if self.kind == "interaction":
            a, b = self.indices
            return x[:, a] * x[:, b]
        if self.kind == "abs":
            return np.abs(x[:, self.indices[0]])
        raise ValueError(f"Unsupported basis term kind: {self.kind}")


def build_terms(
    feature_names: Iterable[str],
    *,
    interactions: bool = True,
    squares: bool = True,
    absolute: bool = False,
) -> list[BasisTerm]:
    names = list(feature_names)
    terms: list[BasisTerm] = [
        BasisTerm(name=name, kind="identity", indices=(i,), complexity=1)
        for i, name in enumerate(names)
    ]

    if interactions:
        for i, j in combinations(range(len(names)), 2):
            terms.append(
                BasisTerm(
                    name=f"{names[i]}*{names[j]}",
                    kind="interaction",
                    indices=(i, j),
                    complexity=2,
                )
            )

    if squares:
        for i, name in enumerate(names):
            terms.append(
                BasisTerm(name=f"{name}^2", kind="square", indices=(i,), complexity=2)
            )

    if absolute:
        for i, name in enumerate(names):
            terms.append(
                BasisTerm(name=f"abs({name})", kind="abs", indices=(i,), complexity=2)
            )

    return terms


def design_matrix(x: np.ndarray, terms: list[BasisTerm]) -> np.ndarray:
    if not terms:
        return np.empty((len(x), 0), dtype=float)
    return np.column_stack([term.evaluate(x) for term in terms])
