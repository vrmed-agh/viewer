from abc import ABC, abstractmethod
from typing import Iterator

import pygame

from src.input.commands import ViewerCommand


class SteeringHandler(ABC):
    @abstractmethod
    def steer(self, events: list[pygame.event.Event]) -> Iterator[ViewerCommand]:
        ...