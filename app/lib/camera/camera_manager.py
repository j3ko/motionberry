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
        self.record_size = config.get("record_size", (1280, 720))
        self.detect_size = config.get("detect_size", (320, 240))
        self.command_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.status_dict = mp.Manager().dict()
        self.restart_event = mp.Event()

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

    def wait_for_restart(self, timeout=10):
        """Waits for the camera to restart and be ready."""
        restarted = self.restart_event.wait(timeout)
        if restarted:
            self.restart_event.clear()
        return restarted

    def restart_camera(self):
        self.command_queue.put(("restart_camera", []))
        self._force_restart()

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
        raw_path, pts_path = self._get_result()
        final_path = self.video_processor.process_and_save(raw_path, pts_path)
        self.status_dict["is_recording"] = False
        return final_path

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
            self.logger.error("Camera process did not respond in time. Restarting process...")
            self._force_restart()
            return None

    def _force_restart(self):
        self.logger.warning("Restarting Camera Process...")
        self.restart_event.set()

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

        self.restart_event.set()
