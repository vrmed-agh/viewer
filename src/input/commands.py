from dataclasses import dataclass
from enum import Enum, auto


class ViewerCommand(Enum):
    NEXT_SLICE = auto()
    PREV_SLICE = auto()
    NEXT_SCAN = auto()
    PREV_SCAN = auto()
    QUIT = auto()
    ZOOM_IN = auto()
    ZOOM_OUT = auto()
    PAN_LEFT = auto()
    PAN_RIGHT = auto()
    PAN_UP = auto()
    PAN_DOWN = auto()
    PLANE_CORONAL = auto()
    PLANE_SAGITTAL = auto()
    PLANE_AXIAL = auto()
    REPEAT = auto()
    UNDO = auto()
    INCREASE_CONTRAST = auto()
    DECREASE_CONTRAST = auto()
    INCREASE_BRIGHTNESS = auto()
    DECREASE_BRIGHTNESS = auto()
    SHOW_MASKS = auto()
    HIDE_MASKS = auto()
    GO_TO_SLICE = auto()


@dataclass
class ViewerAction:
    command: ViewerCommand
    value: int | None = None