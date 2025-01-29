import logging
import subprocess
import time
from pathlib import Path
from .file_manager import FileManager

class VideoProcessor:
    def __init__(self, file_manager, framerate=30, video_format="mp4"):
        self.logger = logging.getLogger(__name__)
        self.file_manager = file_manager
        self.framerate = framerate
        self.video_format = video_format.lower()
        self.logger.info(f"VideoProcessor initialized with format: {self.video_format}")

    def process_and_save(self, raw_path, pts_file=None):
        """Processes the raw file and moves it to the final output directory."""
        if self.video_format == "mp4":
            result_path = self.convert_to_mp4(raw_path)
        elif self.video_format == "mkv":
            result_path = self.convert_to_mkv(raw_path, pts_file)
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
                    "-fps", str(self.framerate),
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
                self.logger.error(f"mkvmerge error output:\n{process.stderr}")
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
        return output_path

    def normalize_pts_file(self, pts_file):
        """Ensures the PTS file has the correct format and starts at 0."""
        if not Path(pts_file).exists():
            return

        with open(pts_file, "r+") as f:
            lines = f.readlines()
            
            # Check and add header if missing
            if not lines[0].startswith("# timestamp format v2"):
                header = "# timestamp format v2\n"
                self.logger.info(f"Adding missing PTS header to: {pts_file}")
            else:
                header = lines.pop(0)  # Remove existing header
            
            # Convert timestamps to start at 0
            try:
                timestamps = [float(line.strip()) for line in lines if line.strip()]
                min_timestamp = timestamps[0] if timestamps else 0.0
                normalized_timestamps = [f"{ts - min_timestamp:.6f}\n" for ts in timestamps]

                f.seek(0)
                f.write(header + "".join(normalized_timestamps))
                f.truncate()
            except ValueError:
                self.logger.error(f"Invalid PTS file format: {pts_file}")

    def convert_to_mkv(self, h264_path, pts_file=None):
        """Converts an H.264 file to MKV using mkvmerge and an optional PTS file."""
        mkv_filename = h264_path.with_suffix('.mkv').name
        output_path = (self.file_manager.output_dir / mkv_filename).resolve()

        try:
            start_time = time.time()
            self.logger.info(f"Starting MKV conversion for file: {h264_path}")

            if pts_file:
                self.normalize_pts_file(pts_file)

            command = ["mkvmerge", "-o", str(output_path)]

            if pts_file and Path(pts_file).exists():
                command.extend(["--timecodes", f"0:{pts_file}"])

            command.append(str(h264_path))

            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.logger.debug(f"mkvmerge stdout:\n{process.stdout}")
            self.logger.error(f"mkvmerge stderr:\n{process.stderr}")

            if process.returncode != 0:
                self.logger.error(f"mkvmerge process failed with return code {process.returncode}")
                self.logger.error(f"mkvmerge error output:\n{process.stderr}")
                raise subprocess.CalledProcessError(
                    process.returncode, process.args, process.stdout, process.stderr
                )

            elapsed_time = time.time() - start_time
            self.logger.info(f"MKV conversion successful: {output_path} (Time: {elapsed_time:.2f}s)")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Error during MKV conversion for file {h264_path}: {e}", exc_info=True
            )
            raise

        return output_path