import io
import time
import threading
import logging
from PIL import Image
from collections import deque
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
from .file_manager import FileManager


class CameraManager:
    def __init__(self, file_manager, video_format="mp4", encoder_bitrate=1000000, framerate=30, record_size=(1280, 720), detect_size=(320, 240), tuning_file=None):
        self.logger = logging.getLogger(__name__)
        tuning = self._load_tuning(tuning_file)
        self.picam2 = Picamera2(tuning=tuning)
        self.encoder = H264Encoder(encoder_bitrate)
        self.framerate = framerate
        self.frame_buffer = deque(maxlen=int(framerate * 3))  # 3 seconds of buffer
        self.buffer_framerate = framerate
        self.buffer_active = False
        self.camera_lock = threading.Lock()
        self.client_lock = threading.Lock()
        self.is_camera_running = False
        self.is_recording = False
        self.record_size = record_size
        self.detect_size = detect_size
        self.file_manager = file_manager
        self.video_format = video_format.lower()
        self.client_count = 0

        video_config = self.picam2.create_video_configuration(
            main={"size": record_size, "format": "RGB888"},
            lores={"size": detect_size, "format": "YUV420"},
            controls={"FrameRate": framerate}
        )
        self.picam2.configure(video_config)
        self.logger.debug("CameraManager initialized.")

    def _load_tuning(self, tuning_file=None):
        if tuning_file is None:
            self.logger.debug("No tuning file provided. Using default settings.")
            return None
        
        if not tuning_file.endswith(".json"):
            tuning_file += ".json"
        
        try:
            tuning = Picamera2.load_tuning_file(tuning_file)
            self.logger.info(f"Loading tuning file '{tuning_file}'")
        except FileNotFoundError:
            self.logger.error(f"Tuning file '{tuning_file}' not found. Using default settings.")
            tuning = None
        return tuning

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
                        if self.is_camera_running and not self.is_recording:
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
        """Captures a high-resolution frame and stores it in the rolling buffer."""
        with self.camera_lock:
            if not self.is_camera_running:
                self.start_camera()
            frame = self.picam2.capture_array("main")
            if self.buffer_active:
                self.frame_buffer.append(frame)
            return frame

    def start_recording(self):
        """Starts encoding video, including buffered high-resolution frames."""
        with self.camera_lock:
            if not self.is_recording:
                try:
                    # Create a file path for the recording
                    self.current_raw_path = self.file_manager.save_raw_file(self.video_format)
                    
                    # Configure the encoder output based on the video format
                    if self.video_format == "h264":
                        self.encoder.output = FileOutput(str(self.current_raw_path))
                    else:
                        self.encoder.output = FfmpegOutput(str(self.current_raw_path))
                    
                    # Start the recording process
                    self.is_recording = True
                    self.picam2.start_encoder(self.encoder)
                    self.logger.info(f"Recording started: {self.current_raw_path}")

                    # Add buffered high-res frames to the recording
                    if hasattr(self, "frame_buffer") and self.frame_buffer:
                        self.logger.info("Adding buffered high-resolution frames to the recording.")
                        for frame in self.frame_buffer:
                            self.encoder.encode(frame)
                        self.logger.debug(f"{len(self.frame_buffer)} buffered frames added to the recording.")

                    # Clear the buffer after adding frames
                    if hasattr(self, "frame_buffer"):
                        self.frame_buffer.clear()
                        self.logger.info("Buffer cleared after adding frames to the recording.")

                except Exception as e:
                    # Handle exceptions during recording
                    self.logger.error(f"Failed to start recording: {e}", exc_info=True)
                    self.is_recording = False
                    raise

    def stop_recording(self):
        """Stops video encoding and processes the output."""
        with self.camera_lock:
            if self.is_recording:
                try:
                    self.picam2.stop_encoder()
                    self.logger.info("Recording stopped.")
                    final_path = self.file_manager.move_to_output(self.current_raw_path, self.current_raw_path.name)
                    self.logger.info(f"Video saved: {final_path}")
                    return final_path
                finally:
                    self.is_recording = False
                    self.file_manager.cleanup_tmp_dir(self.current_raw_path.parent)
                    self.file_manager.cleanup_output_directory()


    def record_for_duration(self, duration, result_queue=None):
        """Records a video for a specified duration in seconds."""
        if duration <= 0:
            self.logger.error("Duration must be greater than 0 seconds.")
            if result_queue:
                result_queue.put(None)
            return

        with self.camera_lock:
            if self.is_recording:
                self.logger.warning("A recording is already in progress. Ignoring request.")
                if result_queue:
                    result_queue.put(None)
                return

        if not self.is_camera_running:
            self.start_camera()

        def record():
            try:
                self.logger.info(f"Starting recording for {duration} seconds.")
                self.start_recording()
                time.sleep(duration)
                final_path = self.stop_recording()
                self.logger.info(f"Recording completed and saved to: {final_path}")
                if result_queue:
                    result_queue.put(final_path)
            except Exception as e:
                self.logger.error(f"Error during recording: {e}")
                if result_queue:
                    result_queue.put(None)

        record_thread = threading.Thread(target=record, daemon=True)
        record_thread.start()


    def take_snapshot(self):
        """Takes a snapshot."""
        if not self.is_camera_running:
            self.start_camera()
        filename = f"snapshot_{time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        full_path = str(self.file_manager.output_dir / filename)
        request = self.picam2.capture_request()
        request.save("main", full_path)
        request.release()
        self.logger.info(f"Snapshot taken: {full_path}")
        return filename

