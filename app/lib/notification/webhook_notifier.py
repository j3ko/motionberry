import logging
import threading
import requests
from .notifier import Notifier

class WebhookNotifier(Notifier):
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config

    def notify(self, action: str, data: dict) -> None:
        if not self.config:
            return

        if action in self.config and "webhook_url" in self.config[action]:
            thread = threading.Thread(
                target=self._post, 
                args=(self.config[action]["webhook_url"], data),
                daemon=True,
            )
            thread.start()

    def _post(self, url, data: dict) -> None:
        try:
            response = requests.post(url, json=data, timeout=10)
        except Exception as e:
            self.logger.error(f"Unable to connect to {url}: {e}")