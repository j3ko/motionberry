import cv2
import numpy as np
from .base_algorithm import BaseAlgorithm


class BackgroundSubtractionAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold):
        super().__init__(normalized_threshold)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()
        # Map normalized scale (1-10) to % pixel change: 0.005 to 0.1 (0.5% to 10%)
        self.pixel_ratio_threshold = np.interp(normalized_threshold, [1, 10], [0.005, 0.1])

    def detect(self, frame):
        w, h = frame.shape[1], frame.shape[0]
        gray = frame[:w * h].reshape(h, w)
        fg_mask = self.bg_subtractor.apply(gray)

        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = gray.shape[0] * gray.shape[1]
        ratio = motion_pixels / total_pixels

        return ratio > self.pixel_ratio_threshold