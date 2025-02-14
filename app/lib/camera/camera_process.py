import multiprocessing as mp
import logging
import time
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


class CameraProcess(mp.Process):
    def __init__(
        self,
        command_queue,
        result_queue,
        file_manager,
        video_processor,
        config,
        status_dict,
        ready_event,
    ):
        super().__init__()
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.status_dict = status_dict
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.config = config
        self.framerate = config.get("framerate", 30)
        self.record_size = config.get("record_size", (1280, 720))
        self.detect_size = config.get("detect_size", (320, 240))
        self.encoder_bitrate = config.get("encoder_bitrate", 1000000)
        self.tuning_file = config.get("tuning_file", None)
        self.picam2 = None
        self.encoder = None
        self.status_dict["is_camera_running"] = False
        self.status_dict["is_recording"] = False
        self.ready_event = ready_event
        self.logger = logging.getLogger(__name__)

    def run(self):
        """Main process loop handling camera commands."""
        self._initialize_camera()

        while True:
            try:
                command, args = self.command_queue.get()
                if command == "exit":
                    break
                elif command == "start_camera":
                    self.start_camera()
                elif command == "stop_camera":
                    self.stop_camera()
                elif command == "capture_buffer":
                    self.result_queue.put(self.picam2.capture_buffer(*args))
                elif command == "capture_array":
                    self.result_queue.put(self.picam2.capture_array(*args))
                elif command == "start_recording":
                    self.start_recording()
                elif command == "stop_recording":
                    self.stop_recording()
                elif command == "record_for_duration":
                    self.record_for_duration(*args)
                elif command == "take_snapshot":
                    self.take_snapshot()
                elif command == "restart_camera":
                    self.restart_camera()
            except Exception as e:
                self.logger.error(f"Error in camera process: {e}", exc_info=True)
                self.result_queue.put(None)
                self.ready_event.clear()

    def _initialize_camera(self):
        """Initializes the camera and configures video settings."""
        try:
            self.picam2 = Picamera2()
            video_config = self.picam2.create_video_configuration(
                main={"size": self.record_size, "format": "RGB888"},
                lores={"size": self.detect_size, "format": "YUV420"},
                controls={"FrameRate": self.framerate},
            )
            self.encoder = H264Encoder(
                bitrate=self.encoder_bitrate,
                framerate=self.framerate,
                enable_sps_framerate=True,
            )
            self.picam2.configure(video_config)
            self.picam2.set_controls({"FrameRate": self.framerate})
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {e}", exc_info=True)
            self.ready_event.clear()

    def start_camera(self):
        """Starts the camera if not already running."""
        if not self.status_dict["is_camera_running"]:
            try:
                self.picam2.start()
                self.status_dict["is_camera_running"] = True
                self.ready_event.set()
                self.logger.info("Camera started successfully.")
            except Exception as e:
                self.logger.error(f"Failed to start camera: {e}", exc_info=True)
                self.ready_event.clear()

    def stop_camera(self):
        """Stops the camera if it is running and not recording."""
        if (
            self.status_dict["is_camera_running"]
            and not self.status_dict["is_recording"]
        ):
            self.picam2.stop()
            self.status_dict["is_camera_running"] = False
            self.logger.info("Camera stopped.")

    def restart_camera(self):
        """Restarts the camera cleanly."""
        self.logger.warning("Restarting camera...")
        self.stop_camera()
        self.picam2.close()
        self._initialize_camera()
        self.start_camera()

    def start_recording(self):
        """Starts video recording."""
        if not self.status_dict["is_recording"]:
            try:
                self.current_raw_path, self.current_pts_path = (
                    self.file_manager.save_raw_file()
                )
                self.picam2.start_encoder(
                    encoder=self.encoder,
                    output=str(self.current_raw_path),
                    pts=str(self.current_pts_path),
                )
                self.status_dict["is_recording"] = True
                self.result_queue.put((self.current_raw_path, self.current_pts_path))
                self.logger.info(f"Recording started: {self.current_raw_path}")
            except Exception as e:
                self.logger.error(f"Failed to start recording: {e}", exc_info=True)
                self.result_queue.put(None)

    def stop_recording(self):
        """Stops video recording."""
        if self.status_dict["is_recording"]:
            try:
                self.picam2.stop_encoder()
                self.status_dict["is_recording"] = False
                self.result_queue.put((self.current_raw_path, self.current_pts_path))
                self.logger.info("Recording stopped.")
            except Exception as e:
                self.logger.error(f"Failed to stop recording: {e}", exc_info=True)
                self.result_queue.put(None)

    def record_for_duration(self, duration):
        """Records for a specified duration, then stops automatically."""
        if not self.status_dict["is_camera_running"]:
            self.start_camera()
        self.start_recording()
        self.logger.info(f"Recording for {duration} seconds...")
        self._wait_with_timeout(duration)
        self.stop_recording()

    def take_snapshot(self):
        """Captures a snapshot and saves it as a JPEG file."""
        filename = f"snapshot_{time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        full_path = self.file_manager.output_dir / filename
        try:
            with self.picam2.capture_request() as request:
                request.save("main", str(full_path))
            self.logger.info(f"Snapshot taken: {full_path}")
            self.result_queue.put(filename)
        except Exception as e:
            self.logger.error(f"Failed to capture snapshot: {e}", exc_info=True)
            self.result_queue.put(None)

    def _wait_with_timeout(self, timeout):
        """Waits for the specified duration without blocking the process."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(0.1)
