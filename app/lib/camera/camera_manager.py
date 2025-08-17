import time
import numpy as np
import threading
import logging
from picamera2 import Picamera2, Transform
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


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
        orientation=0,
    ):
        self.logger = logging.getLogger(__name__)
        self.framerate = framerate
        self.camera_lock = threading.Lock()
        self.client_lock = threading.Lock()
        self.is_camera_running = False
        self.is_recording = False
        self.is_restarting = False
        self.restart_condition = threading.Condition()
        self.record_size = record_size
        self.logger.debug(f"Initialized with record_size: {self.record_size}")
        self.detect_size = detect_size
        self.logger.debug(f"Initialized with detect_size: {self.detect_size}")
        self.file_manager = file_manager
        self.video_processor = video_processor
        self.client_count = 0
        self.encoder = H264Encoder(
            bitrate=encoder_bitrate, framerate=framerate, enable_sps_framerate=True
        )
        self.tuning_file = tuning_file
        self.orientation = orientation
        self.logger.debug(f"Initialized with orientation: {self.orientation} degrees")
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
        except FileNotFoundError:
            self.logger.error(
                f"Tuning file '{tuning_file}' not found. Using default settings."
            )
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

    def _initialize_camera(self, tuning_file=None):
        """Initializes the Picamera2 instance with optional tuning."""
        tuning = self._load_tuning(tuning_file)
        self.picam2 = Picamera2(tuning=tuning)

        transform = Transform()
        if self.orientation == 90:
            transform = transform @ Transform(vflip=True) @ Transform(hflip=False) @ Transform(rotation=90)
        elif self.orientation == 180:
            transform = transform @ Transform(vflip=True) @ Transform(hflip=True) @ Transform(rotation=180)
        elif self.orientation == 270:
            transform = transform @ Transform(vflip=False) @ Transform(hflip=True) @ Transform(rotation=270)
        else:
            transform = Transform()

        video_config = self.picam2.create_video_configuration(
            main={"size": self.record_size, "format": "RGB888"},
            lores={"size": self.detect_size, "format": "YUV420"},
            transform=transform,
            controls={
                "FrameRate": self.framerate,
                "AeEnable": True,      # Auto Exposure ON
                "AwbEnable": True,     # Auto White Balance ON
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
            w = config["size"][0]  # Width
            h = config["size"][1]  # Height
            self.logger.debug(f"Stream {stream} configuration: size={w}x{h}, format={config['format']}")
            
            if config["format"] == "RGB888":
                expected_size = w * h * 3  # 3 bytes per pixel for RGB
                if len(buf) != expected_size:
                    self.logger.warning(f"Buffer size {len(buf)} does not match expected {expected_size} for RGB888")
                # Reshape to (height, width, 3) and return as RGB
                image = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3)
                self.logger.debug(f"RGB image shape: {image.shape}")
                return image
            else:  # Assume YUV420 for lores or other formats, return grayscale Y plane
                yuv_height = int(h * 1.5)  # Full YUV420 height
                if len(buf) % yuv_height != 0:
                    self.logger.error(f"Buffer size {len(buf)} not divisible by YUV height {yuv_height}")
                    return None
                stride = len(buf) // yuv_height
                self.logger.debug(f"Computed stride: {stride}")
                image = np.frombuffer(buf, dtype=np.uint8).reshape(yuv_height, stride)
                y_plane = image[:h, :w]  # Extract Y plane as grayscale
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