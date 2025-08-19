import logging
import os
import shutil
import json
import yaml
from threading import Lock
from flask.logging import default_handler
from .lib.camera.file_manager import FileManager
from .lib.camera.video_processor import VideoProcessor
from .lib.camera.camera_manager import CameraManager
from .lib.camera.stream_manager import StreamManager
from .lib.camera.motion_detector import MotionDetector
from .lib.camera.status_manager import StatusManager
from .lib.notification.webhook_notifier import WebhookNotifier, get_webhook_specs
from .lib.notification.logging_notifier import LoggingNotifier

config_lock = Lock()

def load_config(config_file=None):
    """Loads configuration from config/config.yml."""
    default_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.default.yml")
    existing_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config/config.yml")

    if not config_file:
        config_file = existing_config_file

    logger = logging.getLogger(__name__)

    if not os.path.exists(config_file):
        if os.path.exists(default_config_file):
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            shutil.copy(default_config_file, config_file)
            logger.info(f"Copied '{default_config_file}' to '{config_file}'")
        else:
            logger.error(f"Default configuration file '{default_config_file}' not found.")
            raise RuntimeError(f"Default configuration file '{default_config_file}' not found.")

    try:
        with open(config_file, 'r') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            if data is None:
                logger.warning(f"Configuration file '{config_file}' is empty. No updates applied.")
                data = {}
            logger.info(f"Configuration loaded:\n{json.dumps(data, indent=4)}")
    except FileNotFoundError:
        logger.error(f"Configuration file '{config_file}' not found.")
        raise RuntimeError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        raise RuntimeError(f"Error parsing YAML file: {e}")

    return data

def configure_logging(app, config):
    """Configures logging based on application settings."""
    with config_lock:
        if default_handler in app.logger.handlers:
            app.logger.removeHandler(default_handler)

        log_level = config.get("logging", {}).get("level", "info").upper()
        numeric_level = getattr(logging, log_level, logging.INFO)

        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        app.logger.setLevel(numeric_level)
        app.logger.info(f"Logging configured to {log_level} level.")

def initialize_components(app, config):
    """Initialize application components."""
    with config_lock:
        logging_notifier = LoggingNotifier()
        webhook_notifier = WebhookNotifier(config.get("notification", {}))
        app.config["file_manager"] = FileManager(
            output_dir=str(config.get("capture", {}).get("directory", "captures")),
            max_size_mb=int(config.get("capture", {}).get("max_size_mb", 0)),
            max_age_days=int(config.get("capture", {}).get("max_age_days", 0)),
        )

        app.config["video_processor"] = VideoProcessor(
            file_manager=app.config["file_manager"],
            framerate=int(config.get("capture", {}).get("framerate", 30)),
            video_format=config.get("capture", {}).get("video_format", "mkv"),
        )

        # Update or initialize camera_manager
        if "camera_manager" in app.config:
            app.config["camera_manager"].update_config(
                file_manager=app.config["file_manager"],
                video_processor=app.config["video_processor"],
                encoder_bitrate=int(config.get("capture", {}).get("bitrate", 5000000)),
                framerate=int(config.get("capture", {}).get("framerate", 30)),
                record_size=tuple(config.get("capture", {}).get("record_size", [1024, 720])),
                detect_size=tuple(config.get("capture", {}).get("detect_size", [320, 240])),
                tuning_file=config.get("capture", {}).get("tuning", None),
                orientation=config.get("capture", {}).get("orientation", "normal"),
            )
        else:
            app.config["camera_manager"] = CameraManager(
                file_manager=app.config["file_manager"],
                video_processor=app.config["video_processor"],
                encoder_bitrate=int(config.get("capture", {}).get("bitrate", 5000000)),
                framerate=int(config.get("capture", {}).get("framerate", 30)),
                record_size=tuple(config.get("capture", {}).get("record_size", [1024, 720])),
                detect_size=tuple(config.get("capture", {}).get("detect_size", [320, 240])),
                tuning_file=config.get("capture", {}).get("tuning", None),
                orientation=config.get("capture", {}).get("orientation", "normal"),
            )

        app.config["stream_manager"] = StreamManager(
            camera_manager=app.config["camera_manager"]
        )

        # Update or initialize motion_detector
        if "motion_detector" in app.config:
            app.config["motion_detector"].update_config(
                camera_manager=app.config["camera_manager"],
                motion_threshold=float(config.get("motion", {}).get("motion_threshold", 5)),
                blur_strength=float(config.get("motion", {}).get("blur_strength", 0)),
                motion_gap=int(config.get("motion", {}).get("motion_gap", 5)),
                min_clip_length=(config.get("motion", {}).get("min_clip_length", None)),
                max_clip_length=(config.get("motion", {}).get("max_clip_length", None)),
                notifiers=[logging_notifier, webhook_notifier],
                algorithm=config.get("motion", {}).get("algorithm", "frame_diff"),
                buffer_duration=float(config.get("motion", {}).get("buffer_duration", 2)),
                enabled=config.get("motion", {}).get("enabled", False),
            )
        else:
            app.config["motion_detector"] = MotionDetector(
                camera_manager=app.config["camera_manager"],
                motion_threshold=float(config.get("motion", {}).get("motion_threshold", 5)),
                blur_strength=float(config.get("motion", {}).get("blur_strength", 0)),
                motion_gap=int(config.get("motion", {}).get("motion_gap", 5)),
                min_clip_length=(config.get("motion", {}).get("min_clip_length", None)),
                max_clip_length=(config.get("motion", {}).get("max_clip_length", None)),
                notifiers=[logging_notifier, webhook_notifier],
                algorithm=config.get("motion", {}).get("algorithm", "frame_diff"),
                buffer_duration=float(config.get("motion", {}).get("buffer_duration", 2)),
                enabled=config.get("motion", {}).get("enabled", False),
            )

        app.config["status_manager"] = StatusManager(
            camera_manager=app.config["camera_manager"],
            motion_detector=app.config["motion_detector"]
        )