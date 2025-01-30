import logging

from app.lib.transcode.mkv_transcoder import MKVTranscoder
from app.lib.transcode.mp4_transcoder import MP4Transcoder
from app.lib.transcode.null_transcoder import NullTranscoder

class VideoProcessor:
    def __init__(self, file_manager, framerate=30, video_format="mp4"):
        self.logger = logging.getLogger(__name__)
        self.file_manager = file_manager
        self.framerate = framerate
        self.video_format = video_format.lower()
        self.transcoder = self._get_transcoder()
        self.logger.info(f"VideoProcessor initialized with format: {self.video_format}")

    def _get_transcoder(self):
        """Returns the appropriate transcoder based on the video format."""
        if self.video_format == "mp4":
            return MP4Transcoder(self.file_manager, self.framerate)
        elif self.video_format == "mkv":
            return MKVTranscoder(self.file_manager, self.framerate)
        else:
            return NullTranscoder(self.file_manager, self.framerate)

    def process_and_save(self, raw_path, pts_file=None):
        """Processes the raw file and moves it to the final output directory."""
        return self.transcoder.convert(raw_path, pts_file)
