import logging
from .video_transcoder import VideoTranscoder

logger = logging.getLogger(__name__)


class NullTranscoder(VideoTranscoder):
    def convert(self, raw_path, pts_file=None):
        return self.file_manager.move_to_output(raw_path, raw_path.name)
