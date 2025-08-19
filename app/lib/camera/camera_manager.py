import time
import numpy as np
import threading
import logging
from libcamera import Transform
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from ...locks import config_lock

class CameraManager:
    def __init__(
        self,
        file_manager,
        video_processor,
        encoder_bitrate=1000000,
        framerate=30,
        record_size=(1280, 720),
        detect_size=(320, 240),
        tuning_file=None,
        orientation="normal",
    ):
        self.logger = logging.getLogger(__name__)
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.encoder_bitrate = encoder_bitrate
        self.framerate = framerate
        self.record_size = record_size
        self.detect_size = detect_size
        self.tuning_file = tuning_file
        self.orientation = orientation.lower()
        self.camera_lock = threading.Lock()
        self.client_lock = threading.Lock()
        self.is_camera_running = False
        self.is_recording = False
        self.is_restarting = False
        self.restart_condition = threading.Condition()
        self.client_count = 0
        self.encoder = None
        self.logger.debug(f"Initialized with record_size: {self.record_size}, detect_size: {self.detect_size}, orientation: {self.orientation}")
        self._initialize_camera(tuning_file)

    def _load_tuning(self, tuning_file=None):
        if tuning_file is None:
            self.logger.debug("No tuning file provided. Using default settings.")
            return None

        if not tuning_file.endswith(".json"):
            tuning_file += ".json"

        try:
            tuning = Picamera2.load_tuning_file(tuning_file)
            self.logger.info(f"Loading tuning file '{tuning_file}'")
            return tuning
        except FileNotFoundError:
            self.logger.error(f"Tuning file '{tuning_file}' not found. Using default settings.")
            return None

    def start(self):
        """Start or restart the camera with current configuration."""
        with self.camera_lock:
            if self.is_camera_running:
                self.logger.debug("Camera already running, ensuring correct configuration.")
                return
            self.start_camera()

    def stop(self):
        """Stop the camera and recording, preparing for reinitialization."""
        with self.camera_lock:
            if self.is_recording:
                self.logger.info("Stopping active recording before shutdown.")
                self.stop_recording()
            if self.is_camera_running:
                self.logger.info("Stopping camera before reinitialization.")
                self.picam2.stop()
                self.is_camera_running = False
            self.client_count = 0
            self.logger.debug("Camera stopped and client count reset.")

    def update_config(self, file_manager, video_processor, encoder_bitrate, framerate, record_size, detect_size, tuning_file, orientation):
        """Update configuration and reinitialize the camera."""
        with config_lock:
            with self.restart_condition:
                if self.is_restarting:
                    self.logger.warning("Restart already in progress. Waiting...")
                    self.restart_condition.wait()

                self.is_restarting = True
                try:
                    self.stop()
                    self.file_manager = file_manager
                    self.video_processor = video_processor
                    self.encoder_bitrate = encoder_bitrate
                    self.framerate = framerate
                    self.record_size = tuple(record_size)
                    self.detect_size = tuple(detect_size)
                    self.tuning_file = tuning_file
                    self.orientation = orientation.lower()
                    self.logger.debug(f"Updated config: record_size={self.record_size}, detect_size={self.detect_size}, orientation={self.orientation}")
                    self.encoder = H264Encoder(
                        bitrate=self.encoder_bitrate, framerate=self.framerate, enable_sps_framerate=True
                    )
                    self._initialize_camera(self.tuning_file)
                    if self.client_count > 0:
                        self.start_camera()
                        self.logger.info("Camera restarted with new configuration.")
                except Exception as e:
                    self.logger.error(f"Failed to update configuration: {e}", exc_info=True)
                    raise
                finally:
                    self.is_restarting = False
                    self.restart_condition.notify_all()

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

    def _initialize_camera(self, tuning_file=None):
        """Initializes the Picamera2 instance."""
        tuning = self._load_tuning(tuning_file)
        try:
            if hasattr(self, 'picam2') and self.picam2:
                self.picam2.close()
                self.logger.debug("Closed existing Picamera2 instance.")
        except Exception as e:
            self.logger.error(f"Error closing existing camera: {e}")

        self.picam2 = Picamera2(tuning=tuning)

        transform = Transform()
        if self.orientation == "flipped_horizontal":
            transform = Transform(hflip=1, vflip=0)
        elif self.orientation == "inverted":
            transform = Transform(hflip=1, vflip=1)
        elif self.orientation == "flipped_vertical":
            transform = Transform(hflip=0, vflip=1)
        elif self.orientation != "normal":
            self.logger.warning(f"Invalid orientation state '{self.orientation}'. Using 'normal'.")

        video_config = self.picam2.create_video_configuration(
            main={"size": self.record_size, "format": "RGB888"},
            lores={"size": self.detect_size, "format": "YUV420"},
            transform=transform,
            controls={
                "FrameRate": self.framerate,
                "AeEnable": True,
                "AwbEnable": True,
            },
        )
        self.logger.debug(f"Video config: {video_config}")
        self.picam2.configure(video_config)
        self.picam2.set_controls({
            "FrameRate": self.framerate
        })
        self.logger.debug(f"Video config after apply: {self.picam2.camera_config}")

    def restart_camera(self):
        """Restarts the camera safely, ensuring only one restart happens at a time."""
        with self.restart_condition:
            if self.is_restarting:
                self.logger.warning("Restart already in progress. Skipping redundant restart.")
                return
            self.is_restarting = True

        self.logger.warning("Restarting Picamera2 instance...")

        result = False
        with self.client_lock, self.camera_lock:
            try:
                self.is_camera_running = False
                self.picam2.close()
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Error closing camera: {e}")

            try:
                self._initialize_camera(self.tuning_file)
                self.picam2.start()
                self.is_camera_running = True
                self.logger.info("Camera successfully restarted.")
                result = True
            except Exception as e:
                self.logger.error(f"Failed to restart camera: {e}", exc_info=True)

        with self.restart_condition:
            self.is_restarting = False
            self.restart_condition.notify_all()

        return result

    def _capture_with_timeout(self, capture_function, *args, timeout=10):
        self.logger.debug("Entering _capture_with_timeout with function: %s, args: %s", capture_function.__name__, args)
        with self.restart_condition:
            while self.is_restarting:
                self.logger.debug("Waiting for camera restart...")
                self.restart_condition.wait()
        if not self.is_camera_running:
            self.logger.warning("Camera is not running. Attempting to start.")
            self.start_camera()
            if not self.is_camera_running:
                self.logger.error("Camera failed to start.")
                return None

        capture_result = [None]
        capture_complete = threading.Event()

        def capture():
            try:
                self.logger.debug("Executing capture function %s with args %s", capture_function.__name__, args)
                capture_result[0] = capture_function(*args)
                self.logger.debug("Capture function returned with result: %s", "None" if capture_result[0] is None else "valid")
            except Exception as e:
                self.logger.error(f"Error during capture: {e}", exc_info=True)
            finally:
                capture_complete.set()

        capture_thread = threading.Thread(target=capture, daemon=True)
        capture_thread.start()

        if not capture_complete.wait(timeout):
            self.logger.error("Capture timed out! Restarting camera...")
            self.restart_camera()
            return None

        self.logger.debug("Capture completed successfully, result: %s", "None" if capture_result[0] is None else "valid")
        return capture_result[0]

    def capture_image_array(self, stream="main"):
        """Captures an image array with timeout handling."""
        self.logger.debug(f"Attempting to capture image array from {stream} stream using capture_buffer")
        buf = self._capture_with_timeout(self.picam2.capture_buffer, stream)
        if buf is None:
            self.logger.warning(f"Captured buffer is None for {stream} stream. Camera restart?")
            return None
        self.logger.debug(f"Buffer size: {len(buf)}")
        try:
            config = self.picam2.stream_configuration(stream)
            w = config["size"][0]
            h = config["size"][1]
            self.logger.debug(f"Stream {stream} configuration: size={w}x{h}, format={config['format']}")
            
            if config["format"] == "RGB888":
                expected_size = w * h * 3
                if len(buf) != expected_size:
                    self.logger.warning(f"Buffer size {len(buf)} does not match expected {expected_size} for RGB888")
                image = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
                self.logger.debug(f"RGB image shape: {image.shape}")
                return image
            else:
                yuv_height = int(h * 1.5)
                if len(buf) % yuv_height != 0:
                    self.logger.error(f"Buffer size {len(buf)} not divisible by YUV height {yuv_height}")
                    return None
                stride = len(buf) // yuv_height
                self.logger.debug(f"Computed stride: {stride}")
                image = np.frombuffer(buf, dtype=np.uint8).reshape(yuv_height, stride)
                y_plane = image[:h, :w]
                self.logger.debug(f"Y plane shape: {y_plane.shape}, min: {y_plane.min()}, max: {y_plane.max()}")
                return y_plane
        except Exception as e:
            self.logger.error(f"Failed to process buffer for {stream} stream: {e}", exc_info=True)
            return None

    def take_snapshot(self):
        """Takes a snapshot and saves it as a JPEG file with timeout handling."""
        filename = f"snapshot_{time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        full_path = str(self.file_manager.output_dir / filename)

        request = self._capture_with_timeout(self.picam2.capture_request)
        if request is None:
            self.logger.error("Failed to capture snapshot.")
            return None

        try:
            request.save("main", full_path)
            self.logger.info(f"Snapshot taken: {full_path}")
        finally:
            request.release()

        return filename

    def start_recording(self):
        """Starts encoding video."""
        with self.camera_lock:
            if not self.is_recording:
                try:
                    self.current_raw_path, self.current_pts_path = (
                        self.file_manager.save_raw_file()
                    )
                    self.encoder.output = FileOutput(str(self.current_raw_path))
                    self.is_recording = True
                    self.picam2.start_encoder(
                        encoder=self.encoder,
                        output=str(self.current_raw_path),
                        pts=str(self.current_pts_path),
                    )
                    self.logger.info(f"Recording started: {self.current_raw_path}")
                except Exception as e:
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
                    final_path = self.video_processor.process_and_save(
                        self.current_raw_path, self.current_pts_path
                    )
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
                self.logger.warning(
                    "A recording is already in progress. Ignoring request."
                )
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