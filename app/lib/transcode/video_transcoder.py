from abc import ABC, abstractmethod
import logging

class VideoTranscoder(ABC):
    def __init__(self, file_manager, framerate):
        self.file_manager = file_manager
        self.framerate = framerate
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def convert(self, raw_path, pts_file=None):
        pass