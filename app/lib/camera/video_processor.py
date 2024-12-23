import tempfile
import subprocess
import shutil
from pathlib import Path
import os
import time


class VideoProcessor:
    def __init__(self, video_dir, video_format="mp4", tmp_dir=None):
        self.video_dir = Path(video_dir)
        self.video_dir.mkdir(exist_ok=True)
        self.tmp_dir = Path(tmp_dir or tempfile.mkdtemp())
        self.video_format = video_format.lower()
        print(f"Temporary directory created at: {self.tmp_dir}")

    def generate_tmp_filename(self, extension):
        """Generates a filename with a timestamp and the given extension in the temporary directory."""
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        return self.tmp_dir / f"motion_{timestamp}.{extension}"

    def save_raw_file(self):
        """Returns the path for saving raw video files."""
        return self.generate_tmp_filename("h264")

    def process_and_save(self, raw_path):
        """Processes the raw file and moves it to the final output directory."""
        if self.video_format == "mp4":
            return self.convert_to_mp4(raw_path)
        else:
            return self.move_to_output(raw_path)

    def convert_to_mp4(self, h264_path):
        """Converts an H.264 file to MP4 using FFmpeg and moves it to the output directory."""
        mp4_filename = self.video_dir / h264_path.with_suffix('.mp4').name
        try:
            start_time = time.time()
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",  # Overwrite output files without asking
                    "-i", str(h264_path),  # Input H.264 file
                    "-c:v", "copy",  # Copy the video stream without re-encoding
                    str(mp4_filename)  # Output MP4 file
                ],
                check=True
            )
            print(f"MP4 conversion successful: {mp4_filename}")
        except subprocess.CalledProcessError as e:
            print(f"Error during MP4 conversion: {e}")
        finally:
            os.remove(h264_path)
            print(f"Processing time: {time.time() - start_time:.2f}s for file {h264_path}")
        return mp4_filename

    def move_to_output(self, raw_path):
        """Moves the raw file to the output directory."""
        output_path = self.video_dir / raw_path.name
        shutil.move(str(raw_path), str(output_path))
        print(f"Raw file moved to output directory: {output_path}")
        return output_path

    def cleanup(self):
        """Cleans up temporary files and directories."""
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)
            print(f"Temporary directory {self.tmp_dir} deleted.")
