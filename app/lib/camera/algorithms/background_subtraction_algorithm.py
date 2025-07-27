import cv2
import numpy as np
from .base_algorithm import BaseAlgorithm


class BackgroundSubtractionAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold):
        super().__init__(normalized_threshold)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()
        self.pixel_ratio_threshold = np.interp(
            normalized_threshold,
            [1, 10],        # normalized threshold scale
            [0.005, 0.10]   # raw motion pixel ratio (0.5% to 10%)
        )

    def detect(self, frame):
        if frame is None or frame.ndim < 2:
            return False  # Skip invalid frame

        # Convert to grayscale if needed
        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        fg_mask = self.bg_subtractor.apply(gray)

        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = gray.shape[0] * gray.shape[1]
        ratio = motion_pixels / total_pixels if total_pixels else 0

        return ratio > self.pixel_ratio_threshold
