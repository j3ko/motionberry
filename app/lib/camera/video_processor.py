import tempfile
import subprocess
import shutil
from pathlib import Path
import os
import time
import logging

class VideoProcessor:
    def __init__(self, video_dir, video_format="mp4"):
        self.logger = logging.getLogger(__name__)
        self.video_dir = Path(video_dir)
        self.video_dir.mkdir(exist_ok=True)
        self.video_format = video_format.lower()
        self.logger.info(f"VideoProcessor initialized with output directory: {self.video_dir}")

    def _create_tmp_dir(self):
        """Creates a unique temporary directory for the current processing session."""
        tmp_dir = Path(tempfile.mkdtemp(prefix="pimotion2-"))
        self.logger.debug(f"Temporary directory created: {tmp_dir}")
        return tmp_dir

    def _cleanup_tmp_dir(self, tmp_dir):
        """Cleans up the temporary directory."""
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            self.logger.debug(f"Temporary directory deleted: {tmp_dir}")

    def generate_tmp_filename(self, tmp_dir, extension):
        """Generates a filename with a timestamp and the given extension in the temporary directory."""
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        tmp_filename = tmp_dir / f"motion_{timestamp}.{extension}"
        self.logger.debug(f"Generated temporary filename: {tmp_filename}")
        return tmp_filename

    def save_raw_file(self):
        """Creates a temporary directory and returns the path for saving raw video files."""
        tmp_dir = self._create_tmp_dir()
        raw_file_path = self.generate_tmp_filename(tmp_dir, "h264")
        self.logger.debug(f"Raw file path generated: {raw_file_path}")
        return raw_file_path

    def process_and_save(self, raw_path):
        """Processes the raw file and moves it to the final output directory."""
        tmp_dir = raw_path.parent
        self.logger.info(f"Processing raw file: {raw_path}")
        try:
            if self.video_format == "mp4":
                result_path = self.convert_to_mp4(raw_path)
            else:
                result_path = self.move_to_output(raw_path)
        finally:
            self._cleanup_tmp_dir(tmp_dir)
        return result_path

    def convert_to_mp4(self, h264_path):
        """Converts an H.264 file to MP4 using FFmpeg and moves it to the output directory."""
        mp4_filename = self.video_dir / h264_path.with_suffix('.mp4').name
        try:
            start_time = time.time()
            self.logger.info(f"Starting MP4 conversion for file: {h264_path}")

            process = subprocess.run(
                [
                    "ffmpeg",
                    "-y",  # Overwrite output files without asking
                    "-i", str(h264_path),  # Input H.264 file
                    "-c:v", "copy",  # Copy the video stream without re-encoding
                    str(mp4_filename)  # Output MP4 file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.logger.debug(f"FFmpeg output:\n{process.stdout}")

            if process.returncode != 0:
                self.logger.error(f"FFmpeg process failed with return code {process.returncode}")
                self.logger.error(f"FFmpeg error output:\n{process.stderr}")
                raise subprocess.CalledProcessError(
                    process.returncode, process.args, process.stdout, process.stderr
                )

            elapsed_time = time.time() - start_time
            self.logger.info(f"MP4 conversion successful: {mp4_filename} (Time: {elapsed_time:.2f}s)")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Error during MP4 conversion for file {h264_path}: {e}", exc_info=True
            )
            raise
        finally:
            if h264_path.exists():
                os.remove(h264_path)
                self.logger.debug(f"Temporary raw file deleted: {h264_path}")
        return mp4_filename

    def move_to_output(self, raw_path):
        """Moves the raw file to the output directory."""
        output_path = self.video_dir / raw_path.name
        self.logger.info(f"Moving raw file to output directory: {output_path}")
        shutil.move(str(raw_path), str(output_path))
        self.logger.debug(f"Raw file successfully moved: {output_path}")
        return output_path
