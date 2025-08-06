import time
import logging
from threading import Thread

from .algorithms import get_motion_algorithm


class MotionDetector:
    def __init__(
        self,
        camera_manager,
        motion_threshold,
        blur_strength,
        motion_gap,
        min_clip_length=None,
        max_clip_length=None,
        notifiers=None,
        algorithm="frame_diff",  # "frame_diff" or "background"
    ):
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

        self.is_running = False
        self.last_motion_time = 0
        self.recording_start_time = None
        self.grace_period = 5
        self.start_time = None
        self.thread = None
        self._notify("application_started")

    def _motion_detection_loop(self):
        self.camera_manager.start_camera()
        time.sleep(5)
        self.start_time = time.time()

        while self.is_running:
            try:
                frame = self.camera_manager.capture_frame("lores")

                if frame is None:
                    self.logger.warning("Captured frame is None. Camera restart?")
                    time.sleep(0.5)
                    continue

                detected = self.algorithm.detect(frame)

                current_time = time.time()

                if self.camera_manager.is_recording:
                    elapsed = current_time - self.recording_start_time
                    time_since_motion = current_time - self.last_motion_time

                    if self.max_clip_length and elapsed > self.max_clip_length:
                        self.logger.info("Max clip length reached. Stopping recording.")
                        path = self.camera_manager.stop_recording()
                        self._notify("motion_stopped", {"filename": str(path.name)})
                        self.recording_start_time = None
                        continue

                    if not detected and (
                        time_since_motion > self.motion_gap
                        and (
                            self.min_clip_length is None
                            or elapsed >= self.min_clip_length
                        )
                    ):
                        self.logger.info("No motion for threshold. Stopping.")
                        path = self.camera_manager.stop_recording()
                        self._notify("motion_stopped", {"filename": str(path.name)})
                        self.recording_start_time = None

                if detected:
                    if time.time() - self.start_time < self.grace_period:
                        self.logger.info("Grace period active: ignoring detected motion.")
                    else:
                        if not self.camera_manager.is_recording:
                            self.camera_manager.start_recording()
                            self.recording_start_time = current_time
                            self._notify("motion_started")
                        self.last_motion_time = current_time

                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in detection loop: {e}", exc_info=True)
                time.sleep(1)

        self.camera_manager.stop_camera()
        self.logger.info("Motion detection loop exited.")

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = Thread(target=self._motion_detection_loop, daemon=True)
            self.thread.start()
            self._notify("detection_enabled")
        else:
            self.logger.warning("Motion detection already running.")

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            if self.camera_manager.is_recording:
                elapsed = time.time() - self.recording_start_time
                if self.min_clip_length is None or elapsed >= self.min_clip_length:
                    path = self.camera_manager.stop_recording()
                    self._notify("motion_stopped", {"filename": str(path.name)})
            self.thread.join()
            self._notify("detection_disabled")

    def _notify(self, action, data=None):
        for notifier in self.notifiers:
            notifier.notify(action, data)
