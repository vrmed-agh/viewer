import numpy as np
import pygame

from src.utils.pixel_utils import apply_windowing, grayscale_to_rgb, to_pygame_surface_array


class PygameView:
    WINDOW_TITLE = "VRMed DICOM Viewer"
    INITIAL_WIDTH = 1024
    INITIAL_HEIGHT = 768
    INFO_FONT_SIZE = 18
    INFO_COLOR = (200, 200, 200)
    DISABLED_COLOR = (120, 60, 60)
    INFO_PADDING = 8
    MASK_COLOR = (255, 80, 0)
    MASK_ALPHA = 140

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
        self._cached_slice_key: tuple | None = None
        self._cached_mask_surface: pygame.Surface | None = None
        self._cached_mask_key: tuple | None = None

    def render(
        self,
        image_slice: np.ndarray,
        rescale_slope: float,
        rescale_intercept: float,
        window_center: float,
        window_width: float,
        scan_name: str,
        scan_index: int,
        scan_count: int,
        slice_index: int,
        slice_count: int,
        zoom: float = 1.0,
        pan: tuple[int, int] = (0, 0),
        plane: str = "axial",
        window_center_delta: float = 0.0,
        window_width_delta: float = 0.0,
        masks_visible: bool = False,
        mask_slice: np.ndarray | None = None,
        enabled: bool = True,
    ) -> None:
        self._screen.fill((0, 0, 0))

        slice_key = (scan_index, plane, slice_index, window_center + window_center_delta, window_width + window_width_delta)
        surface = self._get_slice_surface(image_slice, rescale_slope, rescale_intercept, window_center + window_center_delta, window_width + window_width_delta, slice_key)

        if masks_visible and mask_slice is not None:
            mask_key = (scan_index, plane, slice_index)
            mask_surface = self._get_mask_surface(mask_slice, surface.get_width(), surface.get_height(), mask_key)
            surface.blit(mask_surface, (0, 0))

        if zoom != 1.0:
            size = (max(1, int(surface.get_width() * zoom)), max(1, int(surface.get_height() * zoom)))
            surface = pygame.transform.smoothscale(surface, size)

        self._screen.blit(surface, (pan[0], pan[1]))

        self._render_info(
            scan_name, scan_index, scan_count, slice_index, slice_count,
            zoom, plane, masks_visible, enabled,
        )

        pygame.display.flip()

    def _get_slice_surface(
        self,
        image_slice: np.ndarray,
        rescale_slope: float,
        rescale_intercept: float,
        window_center: float,
        window_width: float,
        cache_key: tuple,
    ) -> pygame.Surface:
        if self._cached_slice_key == cache_key and self._cached_surface is not None:
            return self._cached_surface

        gray = apply_windowing(
            image_slice,
            rescale_slope,
            rescale_intercept,
            window_center,
            max(1.0, window_width),
        )
        rgb = grayscale_to_rgb(gray)
        transposed = to_pygame_surface_array(rgb)
        surface = pygame.surfarray.make_surface(transposed)

        self._cached_surface = surface
        self._cached_slice_key = cache_key
        return surface

    def _get_mask_surface(
        self,
        mask_slice: np.ndarray,
        width: int,
        height: int,
        cache_key: tuple,
    ) -> pygame.Surface:
        if self._cached_mask_key == cache_key and self._cached_mask_surface is not None:
            return self._cached_mask_surface

        mask_bool = (mask_slice > 0).astype(np.uint8)

        rgba = np.zeros((mask_bool.shape[0], mask_bool.shape[1], 4), dtype=np.uint8)
        rgba[..., 0] = self.MASK_COLOR[0] * mask_bool
        rgba[..., 1] = self.MASK_COLOR[1] * mask_bool
        rgba[..., 2] = self.MASK_COLOR[2] * mask_bool
        rgba[..., 3] = self.MASK_ALPHA * mask_bool

        transposed = rgba
        surface = pygame.Surface((transposed.shape[0], transposed.shape[1]), pygame.SRCALPHA)
        pygame.surfarray.blit_array(surface, transposed[:, :, :3])
        alpha_array = pygame.surfarray.pixels_alpha(surface)
        alpha_array[:] = transposed[:, :, 3]
        del alpha_array

        if surface.get_width() != width or surface.get_height() != height:
            surface = pygame.transform.scale(surface, (width, height))

        self._cached_mask_surface = surface
        self._cached_mask_key = cache_key
        return surface

    def _render_info(
        self,
        scan_name: str,
        scan_index: int,
        scan_count: int,
        slice_index: int,
        slice_count: int,
        zoom: float,
        plane: str,
        masks_visible: bool,
        enabled: bool,
    ) -> None:
        lines = [
            f"Scan: {scan_name}  [{scan_index + 1}/{scan_count}]",
            f"Slice: {slice_index + 1}/{slice_count}   Plane: {plane}   Zoom: {zoom:.1f}x   Masks: {'on' if masks_visible else 'off'}",
            f"[<- ->] slice   [up/down] scan   [+/-] zoom   [WASD] pan   [1/2/3] plane   [M/N] masks   [T] toggle   [Q/ESC] quit",
        ]
        if not enabled:
            lines.insert(0, "-- VOICE CONTROL DISABLED --")
        line_height = self.INFO_FONT_SIZE + 4
        panel_height = len(lines) * line_height + self.INFO_PADDING * 2
        screen_height = self._screen.get_height()
        screen_width = self._screen.get_width()
        panel_y = screen_height - panel_height
        panel_surface = pygame.Surface((screen_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 180))
        self._screen.blit(panel_surface, (0, panel_y))
        color = self.DISABLED_COLOR if not enabled else self.INFO_COLOR
        y = panel_y + self.INFO_PADDING
        for line in lines:
            text_surface = self._font.render(line, True, color)
            self._screen.blit(text_surface, (self.INFO_PADDING, y))
            y += line_height

    def get_events(self) -> list[pygame.event.Event]:
        return pygame.event.get()

    def tick(self, fps: int = 60) -> None:
        self._clock.tick(fps)

    def shutdown(self) -> None:
        pygame.quit()
