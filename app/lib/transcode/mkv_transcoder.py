import subprocess
import time
from pathlib import Path
import logging
from .video_transcoder import VideoTranscoder

logger = logging.getLogger(__name__)


class MKVTranscoder(VideoTranscoder):
    def normalize_pts_file(self, pts_file):
        """Ensures the PTS file has the correct format and starts at 0."""
        if not Path(pts_file).exists():
            return

        with open(pts_file, "r+") as f:
            lines = f.readlines()

            # Check and add header if missing
            if not lines[0].startswith("# timestamp format v2"):
                header = "# timestamp format v2\n"
                logger.info(f"Adding missing PTS header to: {pts_file}")
            else:
                header = lines.pop(0)

            # Convert timestamps to start at 0
            try:
                timestamps = [float(line.strip()) for line in lines if line.strip()]
                min_timestamp = timestamps[0] if timestamps else 0.0
                normalized_timestamps = [
                    f"{ts - min_timestamp:.6f}\n" for ts in timestamps
                ]

                f.seek(0)
                f.write(header + "".join(normalized_timestamps))
                f.truncate()
            except ValueError:
                logger.error(f"Invalid PTS file format: {pts_file}")

    def convert(self, raw_path, pts_file=None):
        mkv_filename = raw_path.with_suffix(".mkv").name
        output_path = (self.file_manager.output_dir / mkv_filename).resolve()

        try:
            start_time = time.time()
            logger.info(f"Starting MKV transcoding for file: {raw_path}")

            if pts_file:
                self.normalize_pts_file(pts_file)

            command = ["mkvmerge", "-o", str(output_path)]

            if pts_file and Path(pts_file).exists():
                command.extend(["--timecodes", f"0:{pts_file}"])

            command.append(str(raw_path))

            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.debug(f"mkvmerge stdout:\n{process.stdout}")
            logger.error(f"mkvmerge stderr:\n{process.stderr}")

            if process.returncode != 0:
                logger.error(
                    f"mkvmerge process failed with return code {process.returncode}"
                )
                logger.error(f"mkvmerge error output:\n{process.stderr}")
                raise subprocess.CalledProcessError(
                    process.returncode, process.args, process.stdout, process.stderr
                )

            elapsed_time = time.time() - start_time
            logger.info(
                f"MKV transcoding successful: {output_path} (Time: {elapsed_time:.2f}s)"
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Error during MKV transcoding for file {raw_path}: {e}", exc_info=True
            )
            raise

        return output_path
