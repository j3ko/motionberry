import io
import time
import threading
import logging
from PIL import Image
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from .video_processor import VideoProcessor
from .file_manager import FileManager


class CameraManager:
    def __init__(self, file_manager, video_processor, encoder_bitrate=5000000, main_size=(1280, 720), lores_size=(320, 240)):
        self.logger = logging.getLogger(__name__)
        self.picam2 = Picamera2()
        self.encoder = H264Encoder(encoder_bitrate)
        self.camera_lock = threading.Lock()
        self.client_lock = threading.Lock()
        self.is_camera_running = False
        self.is_encoding = False
        self.main_size = main_size
        self.lores_size = lores_size
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.client_count = 0

        video_config = self.picam2.create_video_configuration(
            main={"size": main_size, "format": "RGB888"},
            lores={"size": lores_size, "format": "YUV420"}
        )
        self.picam2.configure(video_config)
        self.logger.debug("CameraManager initialized.")

    def start_camera(self):
        """Starts the camera or increments the client count."""
        with self.client_lock:
            self.client_count += 1
            self.logger.debug(f"Client added. Total clients: {self.client_count}")
            if self.client_count == 1:
                with self.camera_lock:
                    if not self.is_camera_running:
                        self.picam2.start()
                        self.is_camera_running = True
                        self.logger.info("Camera started.")

    def stop_camera(self):
        """Decrements the client count and stops the camera if no clients remain."""
        with self.client_lock:
            if self.client_count > 0:
                self.client_count -= 1
                self.logger.debug(f"Client removed. Total clients: {self.client_count}")
                if self.client_count == 0:
                    with self.camera_lock:
                        if self.is_camera_running and not self.is_encoding:
                            self.picam2.stop()
                            self.is_camera_running = False
                            self.logger.info("Camera stopped.")

    def capture_frame(self, stream="lores"):
        """Captures a frame buffer for analysis."""
        with self.camera_lock:
            if not self.is_camera_running:
                self.start_camera()
            return self.picam2.capture_buffer(stream)
    
    def capture_image_array(self):
        """Captures a frame as an image array."""
        with self.camera_lock:
            if not self.is_camera_running:
                self.start_camera()
            return self.picam2.capture_array()

    def start_recording(self):
        """Starts encoding video."""
        with self.camera_lock:
            if not self.is_encoding:
                self.current_raw_path = self.file_manager.save_raw_file()
                self.encoder.output = FileOutput(str(self.current_raw_path))
                self.picam2.start_encoder(self.encoder)
                self.is_encoding = True
                self.logger.info(f"Recording started: {self.current_raw_path}")

    def stop_recording(self):
        """Stops video encoding and processes the output."""
        with self.camera_lock:
            if self.is_encoding:
                try:
                    self.picam2.stop_encoder()
                    self.is_encoding = False
                    self.logger.info("Recording stopped.")
                    final_path = self.video_processor.process_and_save(self.current_raw_path)
                    self.logger.info(f"Video saved: {final_path}")
                finally:
                    self.file_manager.cleanup_tmp_dir(self.current_raw_path.parent)
                    self.file_manager.cleanup_output_directory()

    def take_snapshot(self):
        """Takes a snapshot."""
        if not self.is_camera_running:
            self.start_camera()
        filename = f"snapshot_{time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        request = self.picam2.capture_request()
        request.save("main", str(self.file_manager.output_dir / filename))
        request.release()
        self.logger.info(f"Snapshot taken: {filename}")
        return filename

