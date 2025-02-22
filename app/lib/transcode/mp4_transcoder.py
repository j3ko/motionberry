import subprocess
import time
from pathlib import Path
import logging
from .video_transcoder import VideoTranscoder

logger = logging.getLogger(__name__)


class MP4Transcoder(VideoTranscoder):
    def convert(self, raw_path, pts_file=None):
        mp4_filename = raw_path.with_suffix(".mp4").name
        output_path = (self.file_manager.output_dir / mp4_filename).resolve()

        try:
            start_time = time.time()
            logger.info(f"Starting MP4 transcoding for file: {raw_path}")

            process = subprocess.run(
                [
                    "MP4Box",
                    "-add",
                    str(raw_path),
                    "-fps",
                    str(self.framerate),
                    str(output_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.debug(f"MP4Box stdout:\n{process.stdout}")

            if process.returncode != 0:
                logger.error(
                    f"MP4Box process failed with return code {process.returncode}"
                )
                logger.error(f"MP4Box error output:\n{process.stderr}")
                raise subprocess.CalledProcessError(
                    process.returncode, process.args, process.stdout, process.stderr
                )

            elapsed_time = time.time() - start_time
            logger.info(
                f"MP4 transcoding successful: {output_path} (Time: {elapsed_time:.2f}s)"
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Error during MP4 transcoding for file {raw_path}: {e}", exc_info=True
            )
            raise

        return output_path
