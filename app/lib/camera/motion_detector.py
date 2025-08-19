import time
import logging
from collections import deque
from threading import Thread, Condition
from ...utils import config_lock 
from .algorithms import get_motion_algorithm
import numpy as np
from PIL import Image
import io


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
        algorithm="frame_diff",
        buffer_duration=2,
        enabled=False,
    ):
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        self.motion_threshold = motion_threshold
        self.blur_strength = blur_strength
        self.motion_gap = motion_gap
        self.min_clip_length = None if min_clip_length == 0 else min_clip_length
        self.max_clip_length = None if max_clip_length == 0 else max_clip_length
        if min_clip_length == 0:
            self.logger.warning("min_clip_length set to 0, treating as None.")
        if max_clip_length == 0:
            self.logger.warning("max_clip_length set to 0, treating as None.")
        self.notifiers = notifiers or []
        self.algorithm = get_motion_algorithm(algorithm, motion_threshold, blur_strength)
        self.buffer_duration = buffer_duration
        self.enabled = enabled
        self.frame_buffer = deque(maxlen=int(buffer_duration * self.camera_manager.framerate))
        self.preview_frame = None
        self.is_running = False
        self.is_restarting = False
        self.restart_condition = Condition()
        self.last_motion_time = 0
        self.recording_start_time = None
        self.grace_period = 5
        self.start_time = None
        self.thread = None
        self._notify("application_started")
        if self.enabled:
            self.logger.info("Motion detection enabled on startup.")
            self.start()

    def _save_buffer_frame_as_jpeg(self, frame):
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

    def update_config(
        self,
        camera_manager,
        motion_threshold,
        blur_strength,
        motion_gap,
        min_clip_length,
        max_clip_length,
        notifiers,
        algorithm,
        buffer_duration,
        enabled,
    ):
        """Update configuration and reinitialize components."""
        with config_lock:
            with self.restart_condition:
                if self.is_restarting:
                    self.logger.warning("Restart already in progress. Waiting...")
                    self.restart_condition.wait()

                self.is_restarting = True
                try:
                    was_running = self.is_running
                    if self.is_running:
                        self.logger.info("Stopping motion detection for config update.")
                        self.stop()

                    self.camera_manager = camera_manager
                    self.motion_threshold = motion_threshold
                    self.blur_strength = blur_strength
                    self.motion_gap = motion_gap
                    self.min_clip_length = None if min_clip_length == 0 else min_clip_length
                    self.max_clip_length = None if max_clip_length == 0 else max_clip_length
                    self.notifiers = notifiers or []
                    self.algorithm = get_motion_algorithm(algorithm, motion_threshold, blur_strength)
                    self.buffer_duration = buffer_duration
                    self.enabled = enabled
                    self.frame_buffer = deque(maxlen=int(buffer_duration * self.camera_manager.framerate))
                    self.logger.debug(
                        f"Updated config: motion_threshold={motion_threshold}, "
                        f"blur_strength={blur_strength}, motion_gap={motion_gap}, "
                        f"algorithm={algorithm}, buffer_duration={buffer_duration}, "
                        f"enabled={enabled}"
                    )

                    if self.enabled and not was_running:
                        self.logger.info("Starting motion detection due to enabled=true.")
                        self.start()
                    elif not self.enabled and was_running:
                        self.logger.info("Stopping motion detection due to enabled=false.")
                        self.stop()

                except Exception as e:
                    self.logger.error(f"Failed to update configuration: {e}", exc_info=True)
                    raise
                finally:
                    self.is_restarting = False
                    self.restart_condition.notify_all()

    def _motion_detection_loop(self):
        self.camera_manager.start_camera()
        time.sleep(5)
        self.start_time = time.time()

        while self.is_running:
            try:
                with self.restart_condition:
                    while self.is_restarting:
                        self.logger.debug("Pausing detection for config update...")
                        self.restart_condition.wait()

                frame = self.camera_manager.capture_image_array("lores")

                if frame is None:
                    self.logger.warning("Captured frame is None. Camera restart?")
                    time.sleep(0.5)
                    continue

                self.frame_buffer.append(frame)

                detected = self.algorithm.detect(frame)
                current_time = time.time()

                if self.camera_manager.is_recording:
                    elapsed = current_time - self.recording_start_time
                    time_since_motion = current_time - self.last_motion_time

                    if self.max_clip_length and elapsed > self.max_clip_length:
                        self.logger.info("Max clip length reached. Stopping recording.")
                        path = self.camera_manager.stop_recording()
                        preview_jpeg = self._save_buffer_frame_as_jpeg(self.preview_frame)
                        self._notify(
                            "motion_stopped",
                            {
                                "filepath": str(path),
                                "filename": str(path.name) if path else None,
                                "preview_jpeg": preview_jpeg,
                                "clip_duration": round(elapsed),
                            },
                        )
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
                        preview_jpeg = self._save_buffer_frame_as_jpeg(self.preview_frame)
                        self._notify(
                            "motion_stopped",
                            {
                                "filepath": str(path),
                                "filename": str(path.name) if path else None,
                                "preview_jpeg": preview_jpeg,
                                "clip_duration": round(elapsed),
                            },
                        )
                        self.recording_start_time = None

                if detected:
                    if time.time() - self.start_time < self.grace_period:
                        self.logger.info("Grace period active: ignoring detected motion.")
                    else:
                        if not self.camera_manager.is_recording:
                            self.camera_manager.start_recording()
                            self.preview_frame = self.frame_buffer[-1] if self.frame_buffer else None
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
        if self.is_running:
            self.is_running = False
            if self.thread and self.thread.is_alive():
                if self.camera_manager.is_recording:
                    elapsed = time.time() - self.recording_start_time if self.recording_start_time else 0
                    if self.min_clip_length is None or elapsed >= self.min_clip_length:
                        path = self.camera_manager.stop_recording()
                        preview_jpeg = self._save_buffer_frame_as_jpeg(self.preview_frame)
                        self._notify(
                            "motion_stopped",
                            {
                                "filepath": str(path),
                                "filename": str(path.name) if path else None,
                                "preview_jpeg": preview_jpeg,
                                "clip_duration": round(elapsed),
                            },
                        )
                self.thread.join()
                self.thread = None
            self._notify("detection_disabled")
        else:
            self.logger.warning("Motion detection already stopped.")

    def _notify(self, action, data=None):
        for notifier in self.notifiers:
            notifier.notify(action, data)