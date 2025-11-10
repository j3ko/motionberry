import subprocess
import time
import logging
from pathlib import Path
from .video_transcoder import VideoTranscoder

logger = logging.getLogger(__name__)


class FFmpegTranscoder(VideoTranscoder):
    """Unified MP4/MKV transcoder using ffmpeg."""

    def normalize_pts_file(self, pts_file):
        p = Path(pts_file)
        if not p.exists():
            return

        lines = [x.strip() for x in p.read_text().splitlines() if x.strip()]

        # Remove mkvmerge header if present
        if lines and lines[0].startswith("# timestamp format"):
            lines = lines[1:]

        try:
            timestamps = [float(x) for x in lines]
        except ValueError:
            logger.error(f"Invalid PTS file: {pts_file}")
            return

        if timestamps:
            base = timestamps[0]
            normalized = [f"{ts - base:.6f}\n" for ts in timestamps]
        else:
            normalized = []

        p.write_text("".join(normalized))

    def convert(self, raw_path, pts_file=None):
        raw_path = Path(raw_path)

        video_format = self.video_format.lower()
        if video_format not in {"mp4", "mkv"}:
            raise ValueError(f"Unsupported video_format: {video_format}")

        output_ext = f".{video_format}"
        output_path = (self.file_manager.output_dir /
                       raw_path.with_suffix(output_ext).name).resolve()

        try:
            start = time.time()
            logger.info(f"Starting transcoding: {raw_path} -> {output_path}")

            args = ["ffmpeg", "-y", "-loglevel", "error"]

            # Raw Annex-B inputs require explicit input framerate
            args.extend(["-framerate", str(self.framerate)])

            # Apply timecodes only if MKV + pts_file present
            # if video_format == "mkv" and pts_file and Path(pts_file).exists():
            #     self.normalize_pts_file(pts_file)
            #     args.extend(["-timecodes", f"0:{pts_file}"])

            args.extend([
                "-i", str(raw_path),
                "-c", "copy",
                "-r", str(self.framerate),
                str(output_path),
            ])

            proc = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if proc.returncode != 0:
                logger.error(f"ffmpeg failed ({video_format}) rc={proc.returncode}")
                logger.error(proc.stderr)
                raise subprocess.CalledProcessError(
                    proc.returncode, proc.args, proc.stdout, proc.stderr
                )

            elapsed = time.time() - start
            logger.info(f"Transcoding successful: {output_path} ({elapsed:.2f}s)")

        except subprocess.CalledProcessError:
            raise

        return output_path
