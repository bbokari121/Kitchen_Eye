"""Image preprocessing utilities."""
import numpy as np


def resize(frame: np.ndarray, size: tuple) -> np.ndarray:
    raise NotImplementedError


def normalise(frame: np.ndarray) -> np.ndarray:
    raise NotImplementedError


def to_tensor(frame: np.ndarray):
    raise NotImplementedError
