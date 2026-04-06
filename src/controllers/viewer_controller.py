from src.input.base import SteeringHandler
from src.input.commands import ViewerCommand
from src.models.dataset import Dataset
from src.views.pygame_view import PygameView


class ViewerController:
    def __init__(
        self,
        dataset: Dataset,
        view: PygameView,
        steering_handler: SteeringHandler,
    ) -> None:
        self._dataset = dataset
        self._view = view
        self._steering_handler = steering_handler
        self._scan_index: int = 0
        self._slice_index: int = 0

    def run(self) -> None:
        running = True
        while running:
            events = self._view.get_events()

            for command in self._steering_handler.steer(events):
                if command == ViewerCommand.QUIT:
                    running = False
                elif command == ViewerCommand.NEXT_SLICE:
                    self._switch_slice(+1)
                elif command == ViewerCommand.PREV_SLICE:
                    self._switch_slice(-1)
                elif command == ViewerCommand.NEXT_SCAN:
                    self._switch_scan(+1)
                elif command == ViewerCommand.PREV_SCAN:
                    self._switch_scan(-1)

            self._render()
            self._view.tick(fps=60)

        self._view.shutdown()

    def _switch_slice(self, delta: int) -> None:
        current_scan = self._dataset.scans[self._scan_index]
        self._slice_index = max(0, min(self._slice_index + delta, current_scan.slice_count - 1))

    def _switch_scan(self, delta: int) -> None:
        self._scan_index = max(0, min(self._scan_index + delta, self._dataset.scan_count - 1))
        self._slice_index = 0

    def _render(self) -> None:
        current_scan = self._dataset.scans[self._scan_index]
        current_slice = current_scan.slices[self._slice_index]

        self._view.render(
            slice_data=current_slice,
            scan_name=current_scan.name,
            scan_index=self._scan_index,
            scan_count=self._dataset.scan_count,
            slice_index=self._slice_index,
            slice_count=current_scan.slice_count,
        )