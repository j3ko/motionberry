from abc import ABC, abstractmethod
import logging

class VideoTranscoder(ABC):
    def __init__(self, file_manager, framerate, video_format):
        self.file_manager = file_manager
        self.framerate = framerate
        self.video_format = video_format.lower()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def convert(self, raw_path, pts_file=None):
        pass
