import cv2
import numpy as np
import logging
from collections import deque
from .base_algorithm import BaseAlgorithm

class BackgroundSubtractionAlgorithm(BaseAlgorithm):
    def __init__(
        self,
        normalized_threshold: float,
        blur_strength: int = 0,
        pixel_ratio_min: float = 0.0001,
        pixel_ratio_max: float = 0.10,
        detection_frames: int = 3
    ):
        """Initialize the background subtraction algorithm with temporal smoothing.

        Args:
            normalized_threshold (float): Threshold for motion detection (1 to 10).
            blur_strength (int): Strength of Gaussian blur (0 to disable).
            pixel_ratio_min (float): Minimum pixel ratio for motion detection.
            pixel_ratio_max (float): Maximum pixel ratio for motion detection.
            detection_frames (int): Number of consecutive frames required for motion detection.
        """
        super().__init__(normalized_threshold)
        self.logger = logging.getLogger(__name__)
        self.blur_strength = blur_strength
        self.detection_frames = max(1, detection_frames)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=150,
            varThreshold=16,
            detectShadows=False
        )
        self.pixel_ratio_threshold = np.interp(
            normalized_threshold,
            [1, 10],
            [pixel_ratio_min, pixel_ratio_max]
        )
        self.detection_buffer = deque(maxlen=self.detection_frames)

        self.logger.debug(
            f"Initialized with normalized_threshold={normalized_threshold}, "
            f"pixel_ratio_threshold={self.pixel_ratio_threshold:.4f}, "
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
        fg_mask = self.bg_subtractor.apply(blurred)

        motion_pixels = cv2.countNonZero(fg_mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        ratio = motion_pixels / total_pixels if total_pixels else 0

        self.detection_buffer.append(ratio > self.pixel_ratio_threshold)
        detected = len(self.detection_buffer) == self.detection_frames and all(self.detection_buffer)

        self.logger.debug(
            f"Motion pixel ratio: {ratio:.4f}, Threshold: {self.pixel_ratio_threshold:.4f}, "
            f"Detection buffer: {list(self.detection_buffer)}, Detected: {detected}"
        )
        return detected