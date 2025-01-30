import time
import logging
import numpy as np
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
        self.min_clip_length = min_clip_length
        self.max_clip_length = max_clip_length
        self.is_running = False
        self.last_motion_time = 0
        self.recording_start_time = None
        self.notifiers = notifiers or []
        self.thread = None
        self._notify("application_started")

    def _motion_detection_loop(self):
        prev_frame = None
        w, h = self.camera_manager.detect_size
        self.camera_manager.start_camera()
        time.sleep(5)
        
        while self.is_running:
            try:
                cur_frame = self.camera_manager.capture_frame("lores")
                cur_frame = cur_frame[:w * h].reshape(h, w)

                if prev_frame is not None:
                    mse = np.square(np.subtract(cur_frame, prev_frame)).mean()
                    if mse > self.motion_threshold:  # Motion detected
                        current_time = time.time()
                        if not self.camera_manager.is_recording:
                            self.camera_manager.start_recording()
                            self.recording_start_time = current_time
                            self._notify("motion_started")
                            self.last_motion_time = current_time
                        else:
                            self.last_motion_time = current_time

                    elif self.camera_manager.is_recording:
                        current_time = time.time()
                        elapsed_recording_time = current_time - self.recording_start_time
                        time_since_last_motion = current_time - self.last_motion_time

                        # Enforce max_clip_length if set
                        if (
                            self.max_clip_length
                            and elapsed_recording_time > self.max_clip_length
                        ):
                            self.logger.info(
                                f"Max clip length of {self.max_clip_length}s reached. Stopping recording."
                            )
                            final_path = self.camera_manager.stop_recording()
                            self._notify(
                                "motion_stopped", {"filename": str(final_path.name)}
                            )
                            continue

                        # Enforce stopping based on motion_gap and min_clip_length
                        if (
                            time_since_last_motion > self.motion_gap
                            and (
                                not self.min_clip_length
                                or elapsed_recording_time > self.min_clip_length
                            )
                        ):
                            self.logger.info("No motion detected for encoding period.")
                            final_path = self.camera_manager.stop_recording()
                            self._notify(
                                "motion_stopped", {"filename": str(final_path.name)}
                            )

                prev_frame = cur_frame
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error during motion detection: {e}", exc_info=True)
                self.camera_manager.stop_camera()
                time.sleep(5)
                self.camera_manager.start_camera()
                time.sleep(5)

        # end while
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
                self.camera_manager.stop_recording()
                self._notify("motion_stopped")
            self.thread.join()
            self._notify("detection_disabled")

    def _notify(self, action, data=None):
        for notifier in self.notifiers:
            notifier.notify(action, data)
