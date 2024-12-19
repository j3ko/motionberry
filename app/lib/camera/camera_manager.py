import io
import time
import threading
from PIL import Image
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

class CameraManager:
    def __init__(self, video_dir, encoder_bitrate=5000000, main_size=(1280, 720), lores_size=(320, 240)):
        self.video_dir = Path(video_dir)
        self.video_dir.mkdir(exist_ok=True)
        self.picam2 = Picamera2()
        self.encoder = H264Encoder(encoder_bitrate)
        self.camera_lock = threading.Lock()
        self.is_camera_running = False
        self.is_encoding = False
        self.is_streaming = False
        self.main_size = main_size
        self.lores_size = lores_size

        # Configure the camera
        video_config = self.picam2.create_video_configuration(
            main={"size": main_size, "format": "RGB888"},
            lores={"size": lores_size, "format": "YUV420"}
        )
        self.picam2.configure(video_config)

    def start_camera(self):
        """Starts the camera."""
        with self.camera_lock:
            if not self.is_camera_running:
                self.picam2.start()
                self.is_camera_running = True
                print("Camera started.")

    def stop_camera(self):
        """Stops the camera."""
        with self.camera_lock:
            if self.is_camera_running and not self.is_streaming and not self.is_encoding:
                self.picam2.stop()
                self.is_camera_running = False
                print("Camera stopped.")

    def capture_frame(self, stream="lores"):
        """Captures a frame buffer for analysis."""
        with self.camera_lock:
            if not self.is_camera_running:
                self.start_camera()
            frame = self.picam2.capture_buffer(stream)
        return frame

    def start_recording(self):
        """Starts encoding video."""
        with self.camera_lock:
            if not self.is_encoding:
                filename = self.video_dir / f"motion_{time.strftime('%Y-%m-%d_%H-%M-%S')}.h264"
                self.encoder.output = FileOutput(str(filename))
                self.picam2.start_encoder(self.encoder)
                self.is_encoding = True
                print(f"Recording started: {filename}")
                return filename

    def stop_recording(self):
        """Stops video encoding."""
        with self.camera_lock:
            if self.is_encoding:
                self.picam2.stop_encoder()
                self.is_encoding = False
                print("Recording stopped.")

    def take_snapshot(self):
        """Takes a snapshot."""
        if not self.is_camera_running:
            self.start_camera()
        filename = f"snapshot_{time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        request = self.picam2.capture_request()
        request.save("main", str(self.video_dir / filename))
        request.release()
        print(f"Snapshot taken: {filename}")
        return filename

    # Streaming function
    def generate_frames(self):
        self.is_streaming = True
        if not self.is_camera_running:
            self.start_camera()
        try:
            while True:
                frame = self.picam2.capture_array()
                stream = io.BytesIO()
                image = Image.fromarray(frame)
                image.save(stream, format="JPEG")
                stream.seek(0)
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + stream.getvalue() + b'\r\n')
                time.sleep(0.1)
        finally:
            self.is_streaming = False
            self.stop_camera()