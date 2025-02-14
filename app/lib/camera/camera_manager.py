import multiprocessing as mp
import logging
import queue

from .camera_process import CameraProcess


class CameraManager:
    def __init__(self, file_manager, video_processor, **config):
        self.logger = logging.getLogger(__name__)
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.config = config
        self.command_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.status_dict = mp.Manager().dict()  # Shared dictionary for status
        self.process = CameraProcess(
            self.command_queue,
            self.result_queue,
            file_manager,
            video_processor,
            config,
            self.status_dict,
        )
        self.process.start()

    @property
    def is_camera_running(self):
        return self.status_dict.get("is_camera_running", False)

    @property
    def is_recording(self):
        return self.status_dict.get("is_recording", False)

    def start_camera(self):
        self.command_queue.put(("start_camera", []))

    def stop_camera(self):
        self.command_queue.put(("stop_camera", []))

    def restart_camera(self):
        self.command_queue.put(("restart_camera", []))
        self._force_restart_if_needed()

    def capture_buffer(self, stream="lores"):
        if not self.is_camera_running:
            self.start_camera()
        self.command_queue.put(("capture_buffer", [stream]))
        return self._get_result()

    def capture_array(self, stream="main"):
        if not self.is_camera_running:
            self.start_camera()
        self.command_queue.put(("capture_array", [stream]))
        return self._get_result()

    def start_recording(self):
        self.command_queue.put(("start_recording", []))
        return self._get_result()

    def stop_recording(self):
        self.command_queue.put(("stop_recording", []))
        return self._get_result()

    def record_for_duration(self, duration):
        if not self.is_camera_running:
            self.start_camera()
        self.command_queue.put(("record_for_duration", [duration]))
        return self._get_result()

    def take_snapshot(self):
        if not self.is_camera_running:
            self.start_camera()
        self.command_queue.put(("take_snapshot", []))
        filename = self._get_result()
        if not filename:
            self.logger.error("Failed to capture snapshot.")
            return None
        self.logger.info(f"Snapshot taken: {filename}")
        return filename

    def _get_result(self, timeout=10):
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            self.logger.error(
                "Camera process did not respond in time. Restarting process..."
            )
            self._force_restart_if_needed()
            return None

    def _force_restart_if_needed(self):
        self.process.terminate()
        self.process.join()
        self.process = CameraProcess(
            self.command_queue,
            self.result_queue,
            self.file_manager,
            self.video_processor,
            self.config,
            self.status_dict,
        )
        self.process.start()
