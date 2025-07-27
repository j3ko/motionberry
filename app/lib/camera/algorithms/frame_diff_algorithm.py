import cv2
import numpy as np
from .base_algorithm import BaseAlgorithm


class FrameDiffAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold):
        super().__init__(normalized_threshold)
        self.prev_frame = None
        self.raw_threshold = np.interp(
            normalized_threshold,
            [1, 10],        # normalized user scale
            [0.0, 10.0]     # actual MSE threshold scale
        )

    def detect(self, frame: np.ndarray) -> bool:
        if frame is None or frame.ndim < 2:
            return False  # Skip processing if frame is invalid

        gray = cv2.GaussianBlur(frame, (5, 5), 0)

        detected = False
        if self.prev_frame is not None:
            prev_blur = cv2.GaussianBlur(self.prev_frame, (5, 5), 0)
            mse = np.square(np.subtract(gray, prev_blur)).mean()
            detected = mse > self.raw_threshold

        self.prev_frame = gray
        return detected