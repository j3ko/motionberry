import cv2
import numpy as np
import logging
from .base_algorithm import BaseAlgorithm


class BackgroundSubtractionAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold: float):
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()
        self.pixel_ratio_threshold = np.interp(
            normalized_threshold,
            [1, 10],        # normalized threshold scale
            [0.0001, 0.10]   # raw motion pixel ratio (0.01% to 10%)
        )
        self.logger.debug(
            f"Initialized with normalized_threshold={normalized_threshold}, "
            f"pixel_ratio_threshold={self.pixel_ratio_threshold:.4f}"
        )

    def detect(self, frame: np.ndarray) -> bool:
        if frame is None or frame.ndim != 2:
            self.logger.warning(
                f"Invalid frame: {type(frame)}, shape={getattr(frame, 'shape', 'N/A')}"
            )
            return False

        fg_mask = self.bg_subtractor.apply(frame)

        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        ratio = motion_pixels / total_pixels if total_pixels else 0

        self.logger.debug(f"Motion pixel ratio: {ratio:.4f}, Threshold: {self.pixel_ratio_threshold:.4f}")
        detected = ratio > self.pixel_ratio_threshold
        self.logger.debug(f"Motion detected: {detected}")

        return detected
