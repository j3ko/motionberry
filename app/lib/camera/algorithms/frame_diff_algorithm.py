import cv2
import numpy as np
import logging
from .base_algorithm import BaseAlgorithm


class FrameDiffAlgorithm(BaseAlgorithm):
    def __init__(self, normalized_threshold):
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.prev_frame = None
        self.raw_threshold = np.interp(
            normalized_threshold,
            [1, 10],        # normalized user scale
            [0.0, 10.0]     # actual MSE threshold scale
        )
        self.logger.debug(f"[FrameDiffAlgorithm] Initialized with normalized_threshold={normalized_threshold}, raw_threshold={self.raw_threshold:.4f}")

    def detect(self, frame: np.ndarray) -> bool:
        if frame is None or frame.ndim < 2:
            self.logger.warning(f"[FrameDiffAlgorithm] Invalid frame: {type(frame)}, shape={getattr(frame, 'shape', 'N/A')}")
            return False

        self.logger.debug(f"[FrameDiffAlgorithm] Frame shape: {frame.shape}, dtype: {frame.dtype}")
        gray = cv2.GaussianBlur(frame, (5, 5), 0)

        detected = False
        if self.prev_frame is not None:
            prev_blur = cv2.GaussianBlur(self.prev_frame, (5, 5), 0)
            mse = np.square(np.subtract(gray, prev_blur)).mean()
            self.logger.debug(f"[FrameDiffAlgorithm] MSE={mse:.4f}, Threshold={self.raw_threshold:.4f}")
            detected = mse > self.raw_threshold
            self.logger.debug(f"[FrameDiffAlgorithm] Motion detected: {detected}")
        else:
            self.logger.debug("[FrameDiffAlgorithm] No previous frame available; skipping motion comparison.")

        self.prev_frame = gray
        return detected
