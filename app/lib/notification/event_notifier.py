from abc import ABC, abstractmethod

class EventNotifier(ABC):
    @abstractmethod
    def notify(self, action: str, data: dict) -> None:
        pass