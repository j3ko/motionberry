import logging
import subprocess
import time
from .file_manager import FileManager

class VideoProcessor:
    def __init__(self, file_manager, framerate=30, video_format="mp4"):
        self.logger = logging.getLogger(__name__)
        self.file_manager = file_manager
        self.framerate = framerate
        self.video_format = video_format.lower()
        self.logger.info(f"VideoProcessor initialized with format: {self.video_format}")

    def process_and_save(self, raw_path):
        """Processes the raw file and moves it to the final output directory."""
        if self.video_format == "mp4":
            result_path = self.convert_to_mp4(raw_path)
        else:
            result_path = self.file_manager.move_to_output(raw_path, raw_path.name)
        return result_path

    def convert_to_mp4(self, h264_path):
        """Converts an H.264 file to MP4 using MP4Box and moves it to the output directory."""
        mp4_filename = h264_path.with_suffix('.mp4').name
        output_path = (self.file_manager.output_dir / mp4_filename).resolve()
        try:
            start_time = time.time()
            self.logger.info(f"Starting MP4 conversion for file: {h264_path}")

            process = subprocess.run(
                [
                    "MP4Box",
                    "-add", str(h264_path),
                    # "-fps", str(self.framerate),
                    str(output_path)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.logger.debug(f"MP4Box stdout:\n{process.stdout}")
            self.logger.error(f"MP4Box stderr:\n{process.stderr}")

            if process.returncode != 0:
                self.logger.error(f"MP4Box process failed with return code {process.returncode}")
                raise subprocess.CalledProcessError(
                    process.returncode, process.args, process.stdout, process.stderr
                )

            elapsed_time = time.time() - start_time
            self.logger.info(f"MP4 conversion successful: {output_path} (Time: {elapsed_time:.2f}s)")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Error during MP4 conversion for file {h264_path}: {e}", exc_info=True
            )
            raise
        finally:
            self.file_manager.delete_file(h264_path)
        return output_path
