#!/usr/bin/env python3

import time
import threading
import numpy as np
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

class MotionDetector:
    def __init__(self, video_dir="recordings", lores_size=(320, 240), main_size=(1280, 720)):
        self.video_dir = Path(video_dir)
        self.video_dir.mkdir(exist_ok=True)
        self.picam2 = Picamera2()
        self.is_running = False
        self.encoding = False
        self.last_motion_time = 0
        self.lores_size = lores_size

        # Configure the camera
        video_config = self.picam2.create_video_configuration(
            main={"size": main_size, "format": "RGB888"},
            lores={"size": lores_size, "format": "YUV420"}
        )
        self.picam2.configure(video_config)
        self.encoder = H264Encoder(1000000)

    def _motion_detection_loop(self):
        w, h = self.lores_size
        prev_frame = None

        self.picam2.start()
        while self.is_running:
            cur_frame = self.picam2.capture_buffer("lores")
            cur_frame = cur_frame[:w * h].reshape(h, w)

            if prev_frame is not None:
                mse = np.square(np.subtract(cur_frame, prev_frame)).mean()
                if mse > 7:  # Motion detected
                    if not self.encoding:
                        filename = self.video_dir / f"motion_{time.strftime('%Y-%m-%d_%H-%M-%S')}.h264"
                        self.encoder.output = FileOutput(str(filename))
                        self.picam2.start_encoder(self.encoder)
                        self.encoding = True
                        print(f"Motion detected! Recording started: {filename}")
                    self.last_motion_time = time.time()
                elif self.encoding and time.time() - self.last_motion_time > 2.0:
                    self.picam2.stop_encoder()
                    self.encoding = False
                    print("Recording stopped.")

            prev_frame = cur_frame
            time.sleep(0.1)

        self.picam2.stop()

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._motion_detection_loop, daemon=True)
            self.thread.start()
            print("Motion detection started.")

    def stop(self):
        self.is_running = False
        if self.thread.is_alive():
            self.thread.join()
            print("Motion detection stopped.")
