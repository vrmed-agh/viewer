from src.input.base import SteeringHandler
from src.input.commands import ViewerAction, ViewerCommand
from src.models.dataset import Dataset
from src.views.pygame_view import PygameView


class ViewerController:
    ZOOM_STEP = 0.2
    PAN_STEP = 40
    CONTRAST_STEP = 50
    BRIGHTNESS_STEP = 25

    def __init__(
        self,
        dataset: Dataset,
        view: PygameView,
        steering_handlers: list[SteeringHandler],
    ) -> None:
        self._dataset = dataset
        self._view = view
        self._steering_handlers = steering_handlers
        self._scan_index: int = 0
        self._slice_index: int = 0
        self._enabled: bool = True
        self._zoom: float = 1.0
        self._pan_x: int = 0
        self._pan_y: int = 0
        self._plane: str = "axial"
        self._window_width_delta: float = 0.0
        self._window_center_delta: float = 0.0
        self._masks_visible: bool = False
        self._last_action: ViewerAction | None = None
        self._history: list[tuple] = []

    def run(self) -> None:
        running = True
        while running:
            events = self._view.get_events()

            for action in [a for handler in self._steering_handlers for a in handler.steer(events)]:
                if action.command == ViewerCommand.QUIT:
                    running = False
                else:
                    self._handle(action)

            self._render()
            self._view.tick(fps=60)

        self._view.shutdown()

    def _handle(self, action: ViewerAction) -> None:
        command = action.command

        if command == ViewerCommand.TOGGLE:
            self._enabled = not self._enabled
            return

        if not self._enabled and command != ViewerCommand.TOGGLE:
            return

        if command == ViewerCommand.REPEAT:
            if self._last_action is not None:
                self._handle(self._last_action)
            return

        if command == ViewerCommand.UNDO:
            self._undo()
            return

        self._push_history()

        if command == ViewerCommand.NEXT_SLICE:
            self._switch_slice(+1)
        elif command == ViewerCommand.PREV_SLICE:
            self._switch_slice(-1)
        elif command == ViewerCommand.NEXT_SCAN:
            self._switch_scan(+1)
        elif command == ViewerCommand.PREV_SCAN:
            self._switch_scan(-1)
        elif command == ViewerCommand.ZOOM_IN:
            self._zoom = min(8.0, self._zoom + self.ZOOM_STEP)
        elif command == ViewerCommand.ZOOM_OUT:
            self._zoom = max(0.2, self._zoom - self.ZOOM_STEP)
        elif command == ViewerCommand.PAN_LEFT:
            self._pan_x -= self.PAN_STEP
        elif command == ViewerCommand.PAN_RIGHT:
            self._pan_x += self.PAN_STEP
        elif command == ViewerCommand.PAN_UP:
            self._pan_y -= self.PAN_STEP
        elif command == ViewerCommand.PAN_DOWN:
            self._pan_y += self.PAN_STEP
        elif command == ViewerCommand.PLANE_AXIAL:
            self._plane = "axial"
        elif command == ViewerCommand.PLANE_CORONAL:
            self._plane = "coronal"
        elif command == ViewerCommand.PLANE_SAGITTAL:
            self._plane = "sagittal"
        elif command == ViewerCommand.INCREASE_CONTRAST:
            self._window_width_delta -= self.CONTRAST_STEP
        elif command == ViewerCommand.DECREASE_CONTRAST:
            self._window_width_delta += self.CONTRAST_STEP
        elif command == ViewerCommand.INCREASE_BRIGHTNESS:
            self._window_center_delta -= self.BRIGHTNESS_STEP
        elif command == ViewerCommand.DECREASE_BRIGHTNESS:
            self._window_center_delta += self.BRIGHTNESS_STEP
        elif command == ViewerCommand.SHOW_MASKS:
            self._masks_visible = True
        elif command == ViewerCommand.HIDE_MASKS:
            self._masks_visible = False
        elif command == ViewerCommand.GO_TO_SLICE:
            self._go_to_slice(action.value)

        self._last_action = action

    def _snapshot(self) -> tuple:
        return (
            self._scan_index,
            self._slice_index,
            self._zoom,
            self._pan_x,
            self._pan_y,
            self._plane,
            self._window_width_delta,
            self._window_center_delta,
            self._masks_visible,
        )

    def _push_history(self) -> None:
        self._history.append(self._snapshot())
        if len(self._history) > 100:
            self._history.pop(0)

    def _undo(self) -> None:
        if not self._history:
            return
        state = self._history.pop()
        (
            self._scan_index,
            self._slice_index,
            self._zoom,
            self._pan_x,
            self._pan_y,
            self._plane,
            self._window_width_delta,
            self._window_center_delta,
            self._masks_visible,
        ) = state

    def _switch_slice(self, delta: int) -> None:
        current_scan = self._dataset.scans[self._scan_index]
        self._slice_index = max(0, min(self._slice_index + delta, current_scan.slice_count - 1))

    def _switch_scan(self, delta: int) -> None:
        self._scan_index = max(0, min(self._scan_index + delta, self._dataset.scan_count - 1))
        self._slice_index = 0

    def _go_to_slice(self, number: int | None) -> None:
        if number is None:
            return
        current_scan = self._dataset.scans[self._scan_index]
        index = max(0, min(number - 1, current_scan.slice_count - 1))
        self._slice_index = index

    def _render(self) -> None:
        current_scan = self._dataset.scans[self._scan_index]
        current_slice = current_scan.slices[self._slice_index]

        mask_slice = None
        if current_scan.nrrd_mask is not None:
            volume = current_scan.nrrd_mask.volume
            if 0 <= self._slice_index < volume.shape[0]:
                mask_slice = volume[self._slice_index]

        self._view.render(
            slice_data=current_slice,
            scan_name=current_scan.name,
            scan_index=self._scan_index,
            scan_count=self._dataset.scan_count,
            slice_index=self._slice_index,
            slice_count=current_scan.slice_count,
            zoom=self._zoom,
            pan=(self._pan_x, self._pan_y),
            plane=self._plane,
            window_center_delta=self._window_center_delta,
            window_width_delta=self._window_width_delta,
            masks_visible=self._masks_visible,
            mask_slice=mask_slice,
            enabled=self._enabled,
        )