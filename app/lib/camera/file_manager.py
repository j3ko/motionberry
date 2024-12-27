import logging
import time
import tempfile
import shutil
from pathlib import Path



class FileManager:
    def __init__(self, output_dir, max_size_mb=2048, max_age_days=7):
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.tmp_dir_base = Path(tempfile.gettempdir()) / "motionberry"
        self.tmp_dir_base.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_age_seconds = max_age_days * 24 * 60 * 60
        self.logger.info(f"FileManager initialized with output directory: {self.output_dir}")
        self.logger.info(f"Max size: {self.max_size_bytes} bytes ({max_size_mb} MB), Max age: {self.max_age_seconds} seconds")

    def cleanup_output_directory(self):
        """Cleans up the output directory by size and age constraints."""
        files = sorted(self.output_dir.iterdir(), key=lambda f: f.stat().st_mtime)
        total_size = sum(f.stat().st_size for f in files)

        # Delete oldest files until size is within limits
        for file in files:
            if total_size <= self.max_size_bytes:
                break
            self.logger.info(f"Deleting file to enforce size limit: {file}")
            total_size -= file.stat().st_size
            file.unlink()

        # Delete files older than max age
        current_time = time.time()
        for file in files:
            if current_time - file.stat().st_mtime > self.max_age_seconds:
                self.logger.info(f"Deleting file to enforce age limit: {file}")
                file.unlink()

    def move_to_output(self, src, dest_name):
        """Moves a file to the managed output directory."""
        dest_path = self.output_dir / dest_name
        shutil.move(str(src), str(dest_path))
        self.logger.info(f"File moved to: {dest_path}")
        return dest_path

    def cleanup_tmp_dir(self, tmp_dir):
        """Cleans up a specific temporary directory."""
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            self.logger.debug(f"Temporary directory deleted: {tmp_dir}")

    def delete_file(self, file_path):
        """Deletes a single file."""
        if file_path.exists():
            file_path.unlink()
            self.logger.info(f"Deleted file: {file_path}")

    def _create_tmp_dir(self):
        """Creates a unique temporary directory for a session."""
        tmp_dir = Path(tempfile.mkdtemp(prefix="motion-", dir=self.tmp_dir_base))
        self.logger.debug(f"Temporary directory created: {tmp_dir}")
        return tmp_dir

    def _generate_tmp_filename(self, tmp_dir, extension):
        """Generates a filename with a timestamp and the given extension in the temporary directory."""
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        tmp_filename = tmp_dir / f"motion_{timestamp}.{extension}"
        self.logger.debug(f"Generated temporary filename: {tmp_filename}")
        return tmp_filename

    def save_raw_file(self):
        """Creates a temporary directory and returns the path for saving raw video files."""
        tmp_dir = self._create_tmp_dir()
        raw_file_path = self._generate_tmp_filename(tmp_dir, "h264")
        self.logger.debug(f"Raw file path generated: {raw_file_path}")
        return raw_file_path