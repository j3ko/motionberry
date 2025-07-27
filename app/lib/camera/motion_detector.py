import time
import logging
import numpy as np
import cv2
from threading import Thread


class MotionDetector:
    def __init__(
        self,
        camera_manager,
        motion_threshold,
        motion_gap,
        min_clip_length=None,
        max_clip_length=None,
        notifiers=None,
    ):
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        self.motion_threshold = motion_threshold
        self.motion_gap = motion_gap
        self.min_clip_length = None if min_clip_length == 0 else min_clip_length
        self.max_clip_length = None if max_clip_length == 0 else max_clip_length
        if min_clip_length == 0:
            self.logger.warning("min_clip_length set to 0, treating as None (no minimum clip length enforced).")
        if max_clip_length == 0:
            self.logger.warning("max_clip_length set to 0, treating as None (no maximum clip length enforced).")
        self.is_running = False
        self.last_motion_time = 0
        self.recording_start_time = None
        self.notifiers = notifiers or []
        self.thread = None
        self.consecutive_motion_count = 0  # For temporal smoothing
        self.min_consecutive_frames = 3  # Require 3 consecutive motion detections
        self._notify("application_started")

    def _motion_detection_loop(self):
        prev_frame = None
        w, h = self.camera_manager.detect_size
        self.camera_manager.start_camera()
        time.sleep(5)

        while self.is_running:
            try:
                cur_frame = self.camera_manager.capture_frame("lores")

                if cur_frame is None:
                    self.logger.warning(
                        "Captured frame is None. Possible camera restart in progress."
                    )
                    time.sleep(0.5)
                    continue

                cur_frame = cur_frame[: w * h].reshape(h, w)
                # Apply stronger Gaussian blur to reduce noise
                cur_frame = cv2.GaussianBlur(cur_frame, (9, 9), 0)

                if prev_frame is not None:
                    prev_frame_blurred = cv2.GaussianBlur(prev_frame, (9, 9), 0)
                    mse = np.square(np.subtract(cur_frame, prev_frame_blurred)).mean()
                    self.logger.debug(f"MSE: {mse:.4f}")

                    # Dynamic threshold based on frame brightness
                    avg_intensity = np.mean(cur_frame)
                    dynamic_threshold = self.motion_threshold * (avg_intensity / 255.0)
                    dynamic_threshold = max(dynamic_threshold, 0.5)  # Minimum threshold
                    self.logger.debug(f"Dynamic threshold: {dynamic_threshold:.4f}")

                    # Check max_clip_length first, if recording
                    if self.camera_manager.is_recording:
                        current_time = time.time()
                        elapsed_recording_time = (
                            current_time - self.recording_start_time
                            if self.recording_start_time is not None
                            else 0
                        )
                        self.logger.debug(
                            f"Elapsed: {elapsed_recording_time:.1f}s, No motion: {current_time - self.last_motion_time:.1f}s"
                        )

                        # Enforce max_clip_length if set
                        if (
                            self.max_clip_length is not None
                            and elapsed_recording_time > self.max_clip_length
                        ):
                            self.logger.info(
                                f"Max clip length of {self.max_clip_length}s reached. Stopping recording."
                            )
                            final_path = self.camera_manager.stop_recording()
                            self._notify(
                                "motion_stopped", {"filename": str(final_path.name)}
                            )
                            self.recording_start_time = None
                            self.consecutive_motion_count = 0
                            continue

                    # Check for motion with temporal smoothing
                    if mse > dynamic_threshold:
                        self.consecutive_motion_count += 1
                        if self.consecutive_motion_count >= self.min_consecutive_frames:
                            current_time = time.time()
                            if not self.camera_manager.is_recording:
                                self.camera_manager.start_recording()
                                self.recording_start_time = current_time
                                self._notify("motion_started")
                                self.last_motion_time = current_time
                            else:
                                self.last_motion_time = current_time
                    else:
                        self.consecutive_motion_count = 0

                    # Check for stopping based on motion_gap and min_clip_length
                    if self.camera_manager.is_recording:
                        current_time = time.time()
                        elapsed_recording_time = (
                            current_time - self.recording_start_time
                            if self.recording_start_time is not None
                            else 0
                        )
                        time_since_last_motion = current_time - self.last_motion_time
                        self.logger.debug(f"Checking stop: time_since_last_motion={time_since_last_motion:.1f}s, min_clip_length={self.min_clip_length}")
                        if (
                            time_since_last_motion > self.motion_gap
                            and (
                                self.min_clip_length is None
                                or elapsed_recording_time >= self.min_clip_length
                            )
                        ):
                            self.logger.info("No motion detected for encoding period.")
                            final_path = self.camera_manager.stop_recording()
                            self._notify(
                                "motion_stopped", {"filename": str(final_path.name)}
                            )
                            self.recording_start_time = None
                            self.consecutive_motion_count = 0

                prev_frame = cur_frame
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error during motion detection: {e}", exc_info=True)
                time.sleep(1)

        # Cleanup
        self.camera_manager.stop_camera()
        self.logger.info("Motion detection loop terminated and camera stopped.")

    def start(self):
        """Starts motion detection."""
        if not self.is_running:
            self.is_running = True
            self.logger.debug("Starting motion detection thread...")
            self.thread = Thread(target=self._motion_detection_loop, daemon=True)
            self.thread.start()
            self._notify("detection_enabled")
            self.logger.debug("Motion detection thread started.")
        else:
            self.logger.warning("Motion detection is already running.")

    def stop(self):
        """Stops motion detection."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            if self.camera_manager.is_recording:
                current_time = time.time()
                elapsed_recording_time = (
                    current_time - self.recording_start_time
                    if self.recording_start_time is not None
                    else 0
                )
                if (
                    self.min_clip_length is None
                    or elapsed_recording_time >= self.min_clip_length
                ):
                    final_path = self.camera_manager.stop_recording()
                    self._notify("motion_stopped", {"filename": str(final_path.name)})
                    self.recording_start_time = None
                    self.consecutive_motion_count = 0
            self.thread.join()
            self._notify("detection_disabled")

    def _notify(self, action, data=None):
        for notifier in self.notifiers:
            notifier.notify(action, data)