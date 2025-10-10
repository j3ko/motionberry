import time
import logging
from collections import deque
from threading import Thread
import numpy as np
from PIL import Image
import io

from .algorithms import get_motion_algorithm

class MotionDetector:
    """Detects motion in video frames and manages recording based on configured thresholds."""
    
    def __init__(
        self,
        camera_manager,
        motion_threshold,
        blur_strength,
        motion_gap,
        min_clip_length=None,
        max_clip_length=None,
        notifiers=None,
        algorithm="frame_diff",
        buffer_duration=2,
        ae_awb_adjust_interval=300,
        adjustment_duration=3,
    ):
        """Initialize the MotionDetector with camera and motion detection settings.

        Args:
            camera_manager: Object managing camera operations.
            motion_threshold (float): Threshold for motion detection.
            blur_strength (int): Strength of blur applied to frames.
            motion_gap (float): Seconds without motion before stopping recording.
            min_clip_length (float, optional): Minimum recording duration in seconds.
            max_clip_length (float, optional): Maximum recording duration in seconds.
            notifiers (list, optional): List of notifier objects for events.
            algorithm (str): Motion detection algorithm name (default: 'frame_diff').
            buffer_duration (float): Duration of frame buffer in seconds.
            ae_awb_adjust_interval (float): Interval in seconds to re-enable AE/AWB for adjustment.
            adjustment_duration (float): Duration in seconds to allow AE/AWB to adjust before disabling.
        """
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        self.motion_threshold = motion_threshold
        self.motion_gap = motion_gap
        self.algorithm = get_motion_algorithm(algorithm, motion_threshold, blur_strength)
        self.min_clip_length = None if min_clip_length == 0 else min_clip_length
        self.max_clip_length = None if max_clip_length == 0 else max_clip_length
        if min_clip_length == 0:
            self.logger.warning("min_clip_length set to 0, treating as None.")
        if max_clip_length == 0:
            self.logger.warning("max_clip_length set to 0, treating as None.")
        self.notifiers = notifiers or []
        self.frame_buffer = deque(maxlen=int(buffer_duration * self.camera_manager.framerate))
        self.preview_frame = None
        self.is_running = False
        self.last_motion_time = 0
        self.recording_start_time = None
        self.grace_period = 5
        self.start_time = None
        self.thread = None
        self.ae_awb_adjust_interval = ae_awb_adjust_interval
        self.adjustment_duration = adjustment_duration
        self.last_adjustment_time = None
        self.is_adjusting = False
        self.adjustment_start_time = None
        self._notify("application_started")

    def _save_buffer_frame_as_jpeg(self, frame):
        """Convert a frame to JPEG format for preview.

        Args:
            frame (np.ndarray): Frame to convert.

        Returns:
            bytes: JPEG data, or None if conversion fails.
        """
        if frame is None or frame.size == 0 or len(frame.shape) not in (2, 3):
            self.logger.warning("Invalid frame shape or empty frame. Failed to generate preview.")
            return None

        try:
            if len(frame.shape) == 2:
                y_plane = frame
            else:
                y_plane = frame[:, :, 0]
                self.logger.debug(f"Y plane extracted, shape: {y_plane.shape}")

            y_plane = np.clip(y_plane, 0, 255).astype(np.uint8)
            pil_img = Image.fromarray(y_plane, mode="L")
            buffer = io.BytesIO()
            pil_img.save(buffer, format="JPEG")
            return buffer.getvalue()

        except Exception as e:
            self.logger.error(f"Failed to generate JPEG from frame: {e}", exc_info=True)
            return None

    def _stop_recording(self, reason, elapsed):
        """Stop recording, reset state, and notify listeners.

        Args:
            reason (str): Reason for stopping (e.g., 'max_clip_length', 'motion_gap').
            elapsed (float): Duration of the recording in seconds.
        """
        self.logger.info(f"Stopping recording due to {reason}.")
        path = self.camera_manager.stop_recording()
        self.recording_start_time = None
        preview_jpeg = self._save_buffer_frame_as_jpeg(self.preview_frame)
        notify_data = {
            "filepath": str(path) if path else None,
            "filename": str(path.name) if path else None,
            "preview_jpeg": preview_jpeg,
            "clip_duration": round(elapsed),
        }
        if path is None:
            self.logger.error("Failed to stop recording: stop_recording returned None")
            self.camera_manager.is_recording = False
        self._notify("motion_stopped", notify_data)

    def _motion_detection_loop(self):
        """Main loop for detecting motion and managing recordings."""
        self.camera_manager.start_camera()
        time.sleep(5)
        self.start_time = time.time()
        self.camera_manager.disable_ae_awb()
        self.last_adjustment_time = time.time()

        while self.is_running:
            try:
                current_time = time.time()

                # Check for periodic AE/AWB adjustment
                if (self.last_adjustment_time is not None and
                    current_time - self.last_adjustment_time > self.ae_awb_adjust_interval and
                    not self.is_adjusting):
                    self.logger.info("Starting AE/AWB adjustment period.")
                    self.camera_manager.enable_ae_awb()
                    self.is_adjusting = True
                    self.adjustment_start_time = current_time

                # Check if adjustment period is over
                if self.is_adjusting:
                    if current_time - self.adjustment_start_time > self.adjustment_duration:
                        self.camera_manager.disable_ae_awb()
                        self.is_adjusting = False
                        self.last_adjustment_time = current_time
                        self.logger.info("AE/AWB adjustment completed.")

                frame = self.camera_manager.capture_image_array("lores")

                if frame is None:
                    self.logger.warning("Captured frame is None. Camera restart?")
                    time.sleep(0.5)
                    continue

                self.frame_buffer.append(frame)

                detected = self.algorithm.detect(frame)

                if self.camera_manager.is_recording:
                    elapsed = current_time - self.recording_start_time
                    time_since_motion = current_time - self.last_motion_time

                    if self.max_clip_length and elapsed > (self.max_clip_length * 2):
                        self.logger.error("Recording stuck beyond max_clip_length. Forcing stop.")
                        self._stop_recording("timeout", elapsed)
                    
                    elif self.max_clip_length and elapsed > self.max_clip_length:
                        self._stop_recording("max_clip_length", elapsed)

                    elif not detected and (
                        time_since_motion > self.motion_gap
                        and (
                            self.min_clip_length is None
                            or elapsed >= self.min_clip_length
                        )
                    ):
                        self._stop_recording("motion_gap", elapsed)

                elif detected:
                    if self.is_adjusting:
                        self.logger.info("AE/AWB adjusting period active: ignoring detected motion.")
                    if current_time - self.start_time < self.grace_period:
                        self.logger.info("Grace period active: ignoring detected motion.")
                    else:
                        if not self.camera_manager.is_recording:
                            self.camera_manager.start_recording()
                            self.recording_start_time = current_time
                            self.preview_frame = self.frame_buffer[-1] if self.frame_buffer else None
                            self._notify("motion_started")
                        self.last_motion_time = current_time

                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in detection loop: {e}", exc_info=True)
                time.sleep(1)

        self.camera_manager.stop_camera()
        self.logger.info("Motion detection loop exited.")

    def start(self):
        """Start the motion detection loop."""
        if not self.is_running:
            self.is_running = True
            self.thread = Thread(target=self._motion_detection_loop, daemon=True)
            self.thread.start()
            self._notify("detection_enabled")
        else:
            self.logger.warning("Motion detection already running.")

    def stop(self):
        """Stop the motion detection loop and clean up."""
        self.is_running = False
        self.camera_manager.enable_ae_awb()
        if self.thread and self.thread.is_alive():
            if self.camera_manager.is_recording:
                elapsed = time.time() - self.recording_start_time if self.recording_start_time else 0
                if self.min_clip_length is None or elapsed >= self.min_clip_length:
                    self._stop_recording("manual_stop", elapsed)
            self.thread.join()
            self._notify("detection_disabled")

    def _notify(self, action, data=None):
        """Notify all registered notifiers of an event.

        Args:
            action (str): The event type (e.g., 'motion_started', 'motion_stopped').
            data (dict, optional): Additional data for the event.
        """
        for notifier in self.notifiers:
            notifier.notify(action, data)