import logging
from .notifier import Notifier

class LoggingNotifier(Notifier):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def notify(self, action: str, data: dict) -> None:
        self.logger.debug(f"Notifying: {action}")