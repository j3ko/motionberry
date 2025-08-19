import os
import logging
import time
from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from . import load_config, configure_logging, initialize_components
from .utils import config_lock

class ConfigFileHandler(FileSystemEventHandler):
    """Handles file system events for config file changes."""
    def __init__(self, app, config_file):
        self.app = app
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        self.debounce_timer = None
        self.last_event_time = 0
        self.debounce_interval = 1.0  # Seconds

    def on_modified(self, event):
        if event.src_path != self.config_file or event.is_directory:
            return
        current_time = time.time()
        if current_time - self.last_event_time < self.debounce_interval:
            return
        self.last_event_time = current_time
        if self.debounce_timer:
            self.debounce_timer.cancel()
        self.debounce_timer = Timer(self.debounce_interval, self.reload_config)
        self.debounce_timer.start()

    def reload_config(self):
        self.logger.info(f"Detected change in config file: {self.config_file}")
        try:
            config = load_config(self.config_file)
            with config_lock:
                self.app.config.update(config)
                configure_logging(self.app, config)
                initialize_components(self.app, config)
                self.logger.info("Configuration reloaded and components reinitialized.")
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")

def start_config_watcher(app, config_file):
    """Starts a file watcher for the config file."""
    if not os.path.exists(config_file):
        logging.getLogger(__name__).warning(f"Config file {config_file} does not exist. Watcher not started.")
        return

    event_handler = ConfigFileHandler(app, config_file)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(config_file), recursive=False)
    observer.start()
    logging.getLogger(__name__).info(f"Started config file watcher for {config_file}")