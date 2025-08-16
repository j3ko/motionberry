

import io
import logging
import threading
import time
from PIL import Image
from app.lib.camera.camera_manager import CameraManager


class StreamManager:
    def __init__(self, camera_manager: CameraManager):
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        self.streaming_clients = 0
        self.client_lock = threading.Lock()

    def generate_frames(self, stream="main"):
        """Generates frames for streaming."""
        with self.client_lock:
            self.streaming_clients += 1
            self.logger.debug(f"New streaming client connected. Total clients: {self.streaming_clients}")
            if self.streaming_clients == 1:
                self.camera_manager.start_camera()

        try:
            while True:
                self.logger.info(f"Capturing frame from camera...{stream}")
                frame = self.camera_manager.capture_image_array(stream)

                if frame is None:
                    self.logger.warning("Captured frame is None. Skipping this frame.")
                    time.sleep(0.25)
                    continue

                try:
                    stream_bytes = io.BytesIO()
                    image = Image.fromarray(frame)
                    image.save(stream_bytes, format="JPEG")
                    stream_bytes.seek(0)

                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + stream_bytes.getvalue() + b'\r\n')
                except Exception as e:
                    self.logger.error("Error processing frame: %s", e, exc_info=True)
                
                time.sleep(0.1)
        except Exception as e:
            self.logger.error("Error during streaming: %s", e, exc_info=True)
        finally:
            with self.client_lock:
                self.streaming_clients -= 1
                self.logger.debug(f"Streaming client disconnected. Remaining clients: {self.streaming_clients}")
                if self.streaming_clients == 0:
                    self.camera_manager.stop_camera()
                    self.logger.debug("All streaming clients disconnected.")
