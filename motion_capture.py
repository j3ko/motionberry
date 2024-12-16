#!/usr/bin/python3
import time
import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import logging


class MotionCapture:
    """A motion detection and capture application using the Raspberry Pi Camera."""

    def __init__(self, resolution_main=(1280, 720), resolution_lores=(320, 240), encoder_bitrate=1000000, motion_threshold=7, timeout=2.0):
        """
        Initialize the motion capture system.
        Args:
            resolution_main (tuple): Resolution of the main camera feed.
            resolution_lores (tuple): Resolution for motion detection.
            encoder_bitrate (int): Bitrate for H.264 encoding.
            motion_threshold (float): Threshold for motion detection based on mean square error (MSE).
            timeout (float): Time in seconds to stop recording after motion ceases.
        """
        self.resolution_main = resolution_main
        self.resolution_lores = resolution_lores
        self.encoder_bitrate = encoder_bitrate
        self.motion_threshold = motion_threshold
        self.timeout = timeout
        self.picam2 = Picamera2()
        self.encoder = H264Encoder(self.encoder_bitrate)
        self.prev_frame = None
        self.encoding = False
        self.last_motion_time = 0

        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Configure camera
        self._configure_camera()

    def _configure_camera(self):
        """Configures the Picamera2 instance for video and low-resolution streams."""
        video_config = self.picam2.create_video_configuration(
            main={"size": self.resolution_main, "format": "RGB888"},
            lores={"size": self.resolution_lores, "format": "YUV420"}
        )
        self.picam2.configure(video_config)
        self.logger.info("Camera configured with resolutions: main=%s, lores=%s", self.resolution_main, self.resolution_lores)

    def start(self):
        """Starts the motion detection and video recording system."""
        self.picam2.start()
        self.logger.info("Camera started. Waiting for motion...")
        self._motion_detection_loop()

    def _motion_detection_loop(self):
        """Main loop for detecting motion and handling video recording."""
        w, h = self.resolution_lores
        while True:
            cur_frame = self.picam2.capture_buffer("lores")[:w * h].reshape(h, w)
            if self.prev_frame is not None:
                mse = self._calculate_mse(self.prev_frame, cur_frame)
                if mse > self.motion_threshold:
                    self._handle_motion_detected(mse)
                else:
                    self._handle_no_motion()
            self.prev_frame = cur_frame

    def _calculate_mse(self, frame1, frame2):
        """Calculate the Mean Square Error (MSE) between two frames."""
        return np.square(np.subtract(frame1, frame2)).mean()

    def _handle_motion_detected(self, mse):
        """Handles the event when motion is detected."""
        if not self.encoding:
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            output_path = f"/home/pi/motion_videos/motion_{timestamp}.h264"
            self.encoder.output = FileOutput(output_path)
            self.picam2.start_encoder(self.encoder)
            self.encoding = True
            self.logger.info("Motion detected (MSE=%.2f). Recording started: %s", mse, output_path)
        self.last_motion_time = time.time()

    def _handle_no_motion(self):
        """Handles the case when no motion is detected."""
        if self.encoding and (time.time() - self.last_motion_time > self.timeout):
            self.picam2.stop_encoder()
            self.encoding = False
            self.logger.info("No motion detected. Recording stopped.")

    def stop(self):
        """Stops the motion detection and recording system."""
        if self.encoding:
            self.picam2.stop_encoder()
        self.picam2.stop()
        self.logger.info("Camera stopped.")


if __name__ == "__main__":
    try:
        motion_capture = MotionCapture()
        motion_capture.start()
    except KeyboardInterrupt:
        motion_capture.stop()
        print("Motion capture stopped.")
