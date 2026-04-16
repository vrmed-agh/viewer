from typing import Iterator

import pygame

from src.input.base import SteeringHandler
from src.input.commands import ViewerAction, ViewerCommand


class KeyboardSteeringHandler(SteeringHandler):
    BINDINGS: dict[int, ViewerCommand] = {
        pygame.K_RIGHT: ViewerCommand.NEXT_SLICE,
        pygame.K_LEFT: ViewerCommand.PREV_SLICE,
        pygame.K_UP: ViewerCommand.PREV_SCAN,
        pygame.K_DOWN: ViewerCommand.NEXT_SCAN,
        pygame.K_ESCAPE: ViewerCommand.QUIT,
        pygame.K_q: ViewerCommand.QUIT,
        pygame.K_EQUALS: ViewerCommand.ZOOM_IN,
        pygame.K_MINUS: ViewerCommand.ZOOM_OUT,
        pygame.K_a: ViewerCommand.PAN_LEFT,
        pygame.K_d: ViewerCommand.PAN_RIGHT,
        pygame.K_w: ViewerCommand.PAN_UP,
        pygame.K_s: ViewerCommand.PAN_DOWN,
        pygame.K_1: ViewerCommand.PLANE_AXIAL,
        pygame.K_2: ViewerCommand.PLANE_CORONAL,
        pygame.K_3: ViewerCommand.PLANE_SAGITTAL,
        pygame.K_r: ViewerCommand.REPEAT,
        pygame.K_u: ViewerCommand.UNDO,
        pygame.K_RIGHTBRACKET: ViewerCommand.INCREASE_CONTRAST,
        pygame.K_LEFTBRACKET: ViewerCommand.DECREASE_CONTRAST,
        pygame.K_PERIOD: ViewerCommand.INCREASE_BRIGHTNESS,
        pygame.K_COMMA: ViewerCommand.DECREASE_BRIGHTNESS,
        pygame.K_m: ViewerCommand.SHOW_MASKS,
        pygame.K_n: ViewerCommand.HIDE_MASKS,
        pygame.K_t: ViewerCommand.TOGGLE,
    }

    def steer(self, events: list[pygame.event.Event]) -> Iterator[ViewerAction]:
        for event in events:
            if event.type == pygame.QUIT:
                yield ViewerAction(ViewerCommand.QUIT)
            elif event.type == pygame.KEYDOWN:
                command = self.BINDINGS.get(event.key)
                if command is not None:
                    yield ViewerAction(command)