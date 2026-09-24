"""
Random-key encoding: each particle is a vector of continuous values in [0, 1),
one per customer. Sorting the keys gives a customer visiting order which the
decoder then splits across vehicles.
"""
from __future__ import annotations

import numpy as np


def initial_population(num_particles: int, num_customers: int, rng: np.random.Generator) -> np.ndarray:
    """Shape: (num_particles, num_customers), values in [0, 1)."""
    return rng.random((num_particles, num_customers))


def keys_to_order(keys: np.ndarray) -> list[int]:
    """Sort customer indices by their random key -> visiting order."""
    return list(np.argsort(keys))
