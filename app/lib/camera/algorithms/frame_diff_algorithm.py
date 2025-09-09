import cv2
import numpy as np
import logging
from collections import deque
from .base_algorithm import BaseAlgorithm

class FrameDiffAlgorithm(BaseAlgorithm):
    def __init__(
        self,
        normalized_threshold: float,
        blur_strength: int = 0,
        mse_min: float = 0.2,
        mse_max: float = 10.0,
        detection_frames: int = 3
    ):
        """Initialize the frame difference algorithm with temporal smoothing.

        Args:
            normalized_threshold (float): Threshold for motion detection (1 to 10).
            blur_strength (int): Strength of Gaussian blur (0 to disable).
            mse_min (float): Minimum MSE threshold for motion detection.
            mse_max (float): Maximum MSE threshold for motion detection.
            detection_frames (int): Number of consecutive frames required for motion detection.
        """
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.prev_frame: np.ndarray | None = None
        self.blur_strength = blur_strength
        self.detection_frames = max(1, detection_frames)
        self.detection_buffer = deque(maxlen=self.detection_frames)

        self.raw_threshold = np.interp(
            normalized_threshold,
            [1, 10],
            [mse_min, mse_max]
        )

        self.logger.debug(
            f"Initialized with normalized_threshold={normalized_threshold}, "
            f"raw_threshold={self.raw_threshold:.4f}, "
            f"blur_strength={self.blur_strength}, "
            f"detection_frames={self.detection_frames}"
        )

    def apply_blur(self, frame: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur to reduce noise.

        Args:
            frame (np.ndarray): Input frame.

        Returns:
            np.ndarray: Blurred frame.
        """
        if self.blur_strength <= 0:
            return frame
        k = int(round(self.blur_strength))
        ksize = max(3, k | 1)
        return cv2.GaussianBlur(frame, (ksize, ksize), 0)

    def detect(self, frame: np.ndarray) -> bool:
        """Detect motion in the frame, requiring multiple consecutive detections.

        Args:
            frame (np.ndarray): Input grayscale frame.

        Returns:
            bool: True if motion is detected in detection_frames consecutive frames.
        """
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
            self.detection_buffer.append(mse > self.raw_threshold)
            detected = len(self.detection_buffer) == self.detection_frames and all(self.detection_buffer)
            self.logger.debug(
                f"MSE: {mse:.4f}, Threshold: {self.raw_threshold:.4f}, "
                f"Detection buffer: {list(self.detection_buffer)}, Detected: {detected}"
            )
        else:
            self.logger.debug("No previous frame available; skipping comparison.")
            self.detection_buffer.append(False)

        self.prev_frame = frame.copy()
        return detected