from .notifier import Notifier

class LoggingNotifier(Notifier):
    def notify(self, action: str, data: dict) -> None:
        print(f"Notifying: {action}")