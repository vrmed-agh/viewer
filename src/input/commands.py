from enum import Enum, auto


class ViewerCommand(Enum):
    NEXT_SLICE = auto()
    PREV_SLICE = auto()
    NEXT_SCAN = auto()
    PREV_SCAN = auto()
    QUIT = auto()