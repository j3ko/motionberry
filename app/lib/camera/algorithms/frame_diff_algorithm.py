import cv2
import numpy as np
import logging
from .base_algorithm import BaseAlgorithm


class FrameDiffAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold: float):
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.prev_frame: np.ndarray | None = None
        self.raw_threshold = np.interp(
            normalized_threshold,
            [1, 10],        # normalized user scale
            [0.5, 10.0]     # actual MSE threshold scale
        )
        self.logger.debug(
            f"Initialized with normalized_threshold={normalized_threshold}, "
            f"raw_threshold={self.raw_threshold:.4f}"
        )

    def detect(self, frame: np.ndarray) -> bool:
        if frame is None or frame.ndim != 2:
            self.logger.warning(
                f"Invalid frame: {type(frame)}, shape={getattr(frame, 'shape', 'N/A')}"
            )
            return False

        blurred = cv2.GaussianBlur(frame, (5, 5), 0)

        detected = False
        if self.prev_frame is not None:
            prev_blurred = cv2.GaussianBlur(self.prev_frame, (5, 5), 0)
            mse = np.mean((blurred - prev_blurred) ** 2)
            self.logger.debug(f"MSE: {mse:.4f}, Threshold: {self.raw_threshold:.4f}")
            detected = mse > self.raw_threshold
            self.logger.debug(f"Motion detected: {detected}")
        else:
            self.logger.debug("No previous frame available; skipping comparison.")

        self.prev_frame = frame.copy()
        return detected
