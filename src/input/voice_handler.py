import queue
import threading
from typing import Iterator

import pygame

from src.input.base import SteeringHandler
from src.input.commands import ViewerCommand


class VoiceSteeringHandler(SteeringHandler):
    def __init__(self) -> None:
        self._queue: queue.Queue[ViewerCommand] = queue.Queue()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self) -> None:
        # Wątek działa w tle i nasłuchuje mikrofonu.
        # Rozpoznane słowo kluczowe trafia do kolejki self._queue — steer() odbiera je co klatkę.
        #
        # TODO(Piotrek i Sonia): zaimplementujcie tutaj sterowanie głosowe
        pass

    def steer(self, events: list[pygame.event.Event]) -> Iterator[ViewerCommand]:
        while not self._queue.empty():
            yield self._queue.get_nowait()
