from typing import Iterator

import pygame

from src.input.base import SteeringHandler
from src.input.commands import ViewerCommand


class KeyboardSteeringHandler(SteeringHandler):
    BINDINGS: dict[int, ViewerCommand] = {
        pygame.K_RIGHT: ViewerCommand.NEXT_SLICE,
        pygame.K_LEFT: ViewerCommand.PREV_SLICE,
        pygame.K_UP: ViewerCommand.PREV_SCAN,
        pygame.K_DOWN: ViewerCommand.NEXT_SCAN,
        pygame.K_ESCAPE: ViewerCommand.QUIT,
        pygame.K_q: ViewerCommand.QUIT,
    }

    def process_events(self, events: list[pygame.event.Event]) -> Iterator[ViewerCommand]:
        for event in events:
            if event.type == pygame.QUIT:
                yield ViewerCommand.QUIT
            elif event.type == pygame.KEYDOWN:
                command = self.BINDINGS.get(event.key)
                if command is not None:
                    yield command
