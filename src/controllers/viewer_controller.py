from src.input.base import SteeringHandler
from src.input.commands import ViewerAction, ViewerCommand
from src.models.dataset import Dataset
from src.models.scan import Scan
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
        self._zoom: float = 1.0
        self._pan_x: int = 0
        self._pan_y: int = 0
        self._plane: str = self._current_scan().plane if self._dataset.scans else "unknown"
        self._window_width_delta: float = 0.0
        self._window_center_delta: float = 0.0
        self._masks_visible: bool = False
        self._last_action: ViewerAction | None = None
        self._history: list[tuple] = []
        self._preferred_series_by_plane = self._build_preferred_series_map()
        self._log_preferred_series_map()

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
            self._switch_to_plane("axial")
        elif command == ViewerCommand.PLANE_CORONAL:
            self._switch_to_plane("coronal")
        elif command == ViewerCommand.PLANE_SAGITTAL:
            self._switch_to_plane("sagittal")
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

    def _current_scan(self) -> Scan:
        return self._dataset.scans[self._scan_index]

    def _sync_plane_from_current_scan(self) -> None:
        self._plane = self._current_scan().plane

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
        self._sync_plane_from_current_scan()

    def _switch_slice(self, delta: int) -> None:
        current_scan = self._current_scan()
        self._slice_index = max(0, min(self._slice_index + delta, current_scan.slice_count - 1))

    def _switch_scan(self, delta: int) -> None:
        self._scan_index = max(0, min(self._scan_index + delta, self._dataset.scan_count - 1))
        self._slice_index = 0
        self._sync_plane_from_current_scan()

    def _build_preferred_series_map(self) -> dict[str, int]:
        preferred: dict[str, int] = {}
        planes = ("axial", "coronal", "sagittal")
        for plane in planes:
            candidates = [
                (index, scan)
                for index, scan in enumerate(self._dataset.scans)
                if scan.plane == plane and scan.is_volume
            ]
            if not candidates:
                candidates = [
                    (index, scan)
                    for index, scan in enumerate(self._dataset.scans)
                    if scan.plane == plane and scan.slice_count > 1
                ]
            if not candidates:
                continue
            best_index, _ = min(candidates, key=lambda item: (item[1].series_number, item[0]))
            preferred[plane] = best_index
        return preferred

    def _log_preferred_series_map(self) -> None:
        for plane in ("coronal", "sagittal", "axial"):
            index = self._preferred_series_by_plane.get(plane)
            if index is None:
                print(f"[VIEWER] Preferred {plane}: none")
                continue
            scan = self._dataset.scans[index]
            description = scan.series_description or "brak opisu"
            print(
                f"[VIEWER] Preferred {plane}: series #{scan.series_number} "
                f"({scan.plane_display_name}, {scan.slice_count} slices) - {description}"
            )

    def _switch_to_plane(self, plane: str) -> None:
        target_index = self._preferred_series_by_plane.get(plane)
        if target_index is None:
            print(f"[VIEWER] Plane '{plane}' -> no eligible multi-slice series")
            return

        self._scan_index = target_index
        self._slice_index = 0
        self._sync_plane_from_current_scan()
        target_scan = self._current_scan()
        print(
            f"[VIEWER] Plane '{plane}' -> series #{target_scan.series_number} "
            f"({target_scan.plane_display_name}, {target_scan.slice_count} slices)"
        )

    def _go_to_slice(self, number: int | None) -> None:
        if number is None:
            return
        current_scan = self._current_scan()
        index = max(0, min(number - 1, current_scan.slice_count - 1))
        self._slice_index = index

    def _render(self) -> None:
        current_scan = self._current_scan()
        current_slice = current_scan.slices[self._slice_index]

        mask_slice = None
        if current_scan.nrrd_mask is not None:
            volume = current_scan.nrrd_mask.volume
            if 0 <= self._slice_index < volume.shape[0]:
                mask_slice = volume[self._slice_index]

        self._view.render(
            image_slice=current_slice.pixel_array,
            rescale_slope=current_slice.rescale_slope,
            rescale_intercept=current_slice.rescale_intercept,
            window_center=current_slice.window_center,
            window_width=current_slice.window_width,
            scan_name=current_scan.name,
            scan_index=self._scan_index,
            scan_count=self._dataset.scan_count,
            slice_index=self._slice_index,
            slice_count=current_scan.slice_count,
            zoom=self._zoom,
            pan=(self._pan_x, self._pan_y),
            plane=current_scan.plane_display_name,
            window_center_delta=self._window_center_delta,
            window_width_delta=self._window_width_delta,
            masks_visible=self._masks_visible,
            mask_slice=mask_slice,
        )
