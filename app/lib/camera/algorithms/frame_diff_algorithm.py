import cv2
import numpy as np
from .base_algorithm import BaseAlgorithm


class FrameDiffAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold):
        super().__init__(normalized_threshold)
        self.prev_frame = None
        # Map normalized scale (1-10) to raw MSE threshold
        self.raw_threshold = np.interp(normalized_threshold, [1, 10], [50, 1500])

    def detect(self, frame):
        w, h = frame.shape[1], frame.shape[0]
        gray = frame[:w * h].reshape(h, w)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        detected = False
        if self.prev_frame is not None:
            prev_blur = cv2.GaussianBlur(self.prev_frame, (5, 5), 0)
            mse = np.square(np.subtract(gray, prev_blur)).mean()
            detected = mse > self.raw_threshold

        self.prev_frame = gray
        return detected