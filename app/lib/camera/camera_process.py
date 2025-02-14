import multiprocessing as mp
import logging
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
        self.status_dict["is_camera_running"] = False
        self.status_dict["is_recording"] = False
        self.logger = logging.getLogger(__name__)

    def run(self):
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
                elif command == "restart_camera":
                    self.restart_camera()
            except Exception as e:
                self.logger.error(f"Error in camera process: {e}", exc_info=True)
                self.result_queue.put(None)

    def _initialize_camera(self):
        self.picam2 = Picamera2()
        video_config = self.picam2.create_video_configuration(
            main={"size": self.record_size, "format": "RGB888"},
            lores={"size": self.detect_size, "format": "YUV420"},
            controls={"FrameRate": self.framerate},
        )
        self.picam2.configure(video_config)
        self.picam2.set_controls({"FrameRate": self.framerate})

    def start_camera(self):
        if not self.status_dict["is_camera_running"]:
            self.picam2.start()
            self.status_dict["is_camera_running"] = True

    def stop_camera(self):
        if (
            self.status_dict["is_camera_running"]
            and not self.status_dict["is_recording"]
        ):
            self.picam2.stop()
            self.status_dict["is_camera_running"] = False

    def restart_camera(self):
        self.stop_camera()
        self.picam2.close()
        self._initialize_camera()
        self.start_camera()

    def start_recording(self):
        if not self.status_dict["is_recording"]:
            raw_path, pts_path = self.file_manager.save_raw_file()
            self.picam2.start_encoder(
                H264Encoder(bitrate=self.encoder_bitrate, framerate=self.framerate),
                FileOutput(str(raw_path)),
            )
            self.status_dict["is_recording"] = True
            self.result_queue.put((raw_path, pts_path))

    def stop_recording(self):
        if self.status_dict["is_recording"]:
            self.picam2.stop_encoder()
            self.status_dict["is_recording"] = False
            raw_path, pts_path = self.result_queue.get()
            final_path = self.video_processor.process_and_save(raw_path, pts_path)
            self.result_queue.put(final_path)
