import numpy as np


class BaseAlgorithm:
    def __init__(self, normalized_threshold: float):
        """
        Accepts a normalized threshold from 1 to 10.
        Each subclass must map this to a raw value.
        """
        if not (1 <= normalized_threshold <= 10):
            raise ValueError("motion_threshold must be between 1 and 10")
        self.normalized_threshold = normalized_threshold

    def detect(self, frame) -> bool:
        raise NotImplementedError()
