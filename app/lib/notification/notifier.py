from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def notify(self, action: str, data: dict) -> None:
        pass