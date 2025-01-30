import logging
from .event_notifier import EventNotifier

class LoggingNotifier(EventNotifier):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def notify(self, action: str, data: dict) -> None:
        self.logger.debug(f"Notifying: {action}")