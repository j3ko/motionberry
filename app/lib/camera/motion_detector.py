import time
import logging
import numpy as np
from threading import Thread

class MotionDetector:
    def __init__(self, camera_manager, motion_threshold, max_encoding_time, notifiers=None):
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        self.motion_threshold = motion_threshold
        self.max_encoding_time = max_encoding_time
        self.is_running = False
        self.last_motion_time = 0
        self.notifiers = notifiers or []
        self.thread = None
        self._notify("application_started")

    def _motion_detection_loop(self):
        prev_frame = None
        w, h = self.camera_manager.detect_size

        while self.is_running:
            try:
                if not self.camera_manager.is_camera_running:
                    self.camera_manager.start_camera()

                cur_frame = self.camera_manager.capture_frame("lores")
                cur_frame = cur_frame[:w * h].reshape(h, w)

                if prev_frame is not None:
                    mse = np.square(np.subtract(cur_frame, prev_frame)).mean()
                    if mse > self.motion_threshold:  # Motion detected
                        if not self.camera_manager.is_recording:
                            self.camera_manager.start_recording()
                            self._notify("motion_started")
                            self.last_motion_time = time.time()
                        else:
                            self.last_motion_time = time.time()

                    elif self.camera_manager.is_recording and time.time() - self.last_motion_time > self.max_encoding_time:
                        final_path = self.camera_manager.stop_recording()
                        self._notify("motion_stopped", {"filename": str(final_path.name)})

                prev_frame = cur_frame
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error during motion detection: {e}", exc_info=True)
                if self.camera_manager.is_camera_running:
                    self.camera_manager.stop_camera()
                time.sleep(10)

        if self.camera_manager.is_camera_running:
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