import pygame

from src.models.slice_data import SliceData
from src.utils.pixel_utils import apply_windowing, grayscale_to_rgb, to_pygame_surface_array


class PygameView:
    WINDOW_TITLE = "VRMed DICOM Viewer"
    INITIAL_WIDTH = 1024
    INITIAL_HEIGHT = 768
    INFO_FONT_SIZE = 18
    INFO_COLOR = (200, 200, 200)
    INFO_PADDING = 8

    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self._screen = pygame.display.set_mode(
            (self.INITIAL_WIDTH, self.INITIAL_HEIGHT),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption(self.WINDOW_TITLE)
        self._font = pygame.font.SysFont("monospace", self.INFO_FONT_SIZE)
        self._clock = pygame.time.Clock()
        self._cached_surface: pygame.Surface | None = None
        self._cached_slice_id: int | None = None

    def render(
        self,
        slice_data: SliceData,
        scan_name: str,
        scan_index: int,
        scan_count: int,
        slice_index: int,
        slice_count: int,
    ) -> None:
        self._screen.fill((0, 0, 0))

        surface = self._get_slice_surface(slice_data)
        self._screen.blit(surface, (0, 0))

        self._render_info(scan_name, scan_index, scan_count, slice_index, slice_count, surface.get_height())

        pygame.display.flip()

    def _get_slice_surface(self, slice_data: SliceData) -> pygame.Surface:
        if id(slice_data) == self._cached_slice_id and self._cached_surface is not None:
            return self._cached_surface

        gray = apply_windowing(
            slice_data.pixel_array,
            slice_data.rescale_slope,
            slice_data.rescale_intercept,
            slice_data.window_center,
            slice_data.window_width,
        )
        rgb = grayscale_to_rgb(gray)
        transposed = to_pygame_surface_array(rgb)
        surface = pygame.surfarray.make_surface(transposed)

        self._cached_surface = surface
        self._cached_slice_id = id(slice_data)
        return surface

    def _render_info(
        self,
        scan_name: str,
        scan_index: int,
        scan_count: int,
        slice_index: int,
        slice_count: int,
        image_height: int,
    ) -> None:
        lines = [
            f"Scan: {scan_name}  [{scan_index + 1}/{scan_count}]",
            f"Slice: {slice_index + 1}/{slice_count}",
            f"[<- ->] prev/next slice   [up/down] prev/next scan   [Q/ESC] quit",
        ]
        line_height = self.INFO_FONT_SIZE + 4
        y = image_height - len(lines) * line_height - self.INFO_PADDING
        for line in lines:
            text_surface = self._font.render(line, True, self.INFO_COLOR)
            self._screen.blit(text_surface, (self.INFO_PADDING, y))
            y += line_height

    def get_events(self) -> list[pygame.event.Event]:
        return pygame.event.get()

    def tick(self, fps: int = 60) -> None:
        self._clock.tick(fps)

    def shutdown(self) -> None:
        pygame.quit()