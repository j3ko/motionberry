import cv2
import numpy as np
import logging
from .base_algorithm import BaseAlgorithm


class BackgroundSubtractionAlgorithm(BaseAlgorithm):
    def __init__(
        self,
        normalized_threshold: float,
        blur_strength: int = 0,
        pixel_ratio_min: float = 0.0001,
        pixel_ratio_max: float = 0.10,
        history: int = 100,
        var_threshold: float = 25,
    ):
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.blur_strength = blur_strength

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=False
        )

        self.pixel_ratio_threshold = np.interp(
            normalized_threshold,
            [1, 10],
            [pixel_ratio_min, pixel_ratio_max]
        )

        self.logger.debug(
            f"Initialized with normalized_threshold={normalized_threshold}, "
            f"pixel_ratio_threshold={self.pixel_ratio_threshold:.4f}, "
            f"blur_strength={self.blur_strength}"
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

        current_mean = float(frame.mean())
        self.logger.info(f"[A] Global mean: {current_mean:.2f}")
        if not hasattr(self, "prev_mean"):
            self.prev_mean = current_mean

        blurred = self.apply_blur(frame)
        fg_mask = self.bg_subtractor.apply(blurred)

        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        ratio = motion_pixels / total_pixels if total_pixels else 0

        self.logger.debug(f"Motion pixel ratio: {ratio:.4f}, Threshold: {self.pixel_ratio_threshold:.4f}")
        detected = ratio > self.pixel_ratio_threshold
        self.logger.debug(f"Motion detected: {detected}")

        return detected
