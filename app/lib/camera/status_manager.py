

import logging
import json
import time
from app.lib.camera.camera_manager import CameraManager
from app.lib.camera.motion_detector import MotionDetector


class StatusManager:
    def __init__(self, camera_manager: CameraManager, motion_detector: MotionDetector):
        self.logger = logging.getLogger(__name__)
        self.camera_manager = camera_manager
        self.motion_detector = motion_detector

    def generate_status(self):
        """Generates status for streaming."""
        try:
            while True:
                data = { 
                    "is_camera_running": self.camera_manager.is_camera_running,
                    "is_recording": self.camera_manager.is_recording,
                    "is_motion_detecting": self.motion_detector.is_running.value
                }
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(1)
        except Exception as e:
            self.logger.error("Error during generate_status: %s", e, exc_info=True)
