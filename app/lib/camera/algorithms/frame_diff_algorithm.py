import cv2
import numpy as np
import logging
from .base_algorithm import BaseAlgorithm


class FrameDiffAlgorithm(BaseAlgorithm):
    def __init__(
        self,
        normalized_threshold: float,
        blur_strength: int = 0,
        mse_min: float = 0.2,
        mse_max: float = 10.0
    ):
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing FrameDiffAlgorithm")
        self.prev_frame: np.ndarray | None = None
        self.blur_strength = blur_strength

        self.raw_threshold = np.interp(
            normalized_threshold,
            [1, 10],
            [mse_min, mse_max]
        )

        self.logger.debug(
            f"Initialized with normalized_threshold={normalized_threshold}, "
            f"raw_threshold={self.raw_threshold:.4f}, blur_strength={self.blur_strength}"
        )


    def apply_blur(self, frame: np.ndarray) -> np.ndarray:
        if self.blur_strength <= 0:
            return frame

        k = int(round(self.blur_strength))
        ksize = max(3, k | 1)
        return cv2.GaussianBlur(frame, (ksize, ksize), 0)


    def detect(self, frame: np.ndarray) -> bool:
        if frame is None or frame.ndim != 2:
            self.logger.warning(
                f"Invalid frame: {type(frame)}, shape={getattr(frame, 'shape', 'N/A')}"
            )
            return False

        blurred = self.apply_blur(frame)
        detected = False

        if self.prev_frame is not None:
            prev_blurred = self.apply_blur(self.prev_frame)
            mse = np.mean((blurred - prev_blurred) ** 2)
            self.logger.debug(f"MSE: {mse:.4f}, Threshold: {self.raw_threshold:.4f}")
            detected = mse > self.raw_threshold
            self.logger.debug(f"Motion detected: {detected}")
        else:
            self.logger.debug("No previous frame available; skipping comparison.")

        self.prev_frame = frame.copy()
        return detected
