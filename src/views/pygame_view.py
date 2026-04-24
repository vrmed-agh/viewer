import numpy as np
import pygame

from src.utils.pixel_utils import apply_windowing, grayscale_to_rgb, to_pygame_surface_array


class PygameView:
    WINDOW_TITLE = "VRMed DICOM Viewer"
    INITIAL_WIDTH = 1024
    INITIAL_HEIGHT = 768
    INFO_FONT_SIZE = 18
    INFO_COLOR = (200, 200, 200)
    INFO_PADDING = 8
    # Paleta kolorów dla kolejnych etykiet masek segmentacji (RGB).
    # Indeks 0 = tło / brak etykiety (pomijany przy rysowaniu), indeksy 1-8 =
    # różne klasy anatomiczne. Kolory dobrane tak, aby były wyraźnie różne
    # na tle obrazu w odcieniach szarości.
    MASK_COLORS = [(0,0,0),
                    (85, 255, 255),
                    (255, 170, 0),
                    (0, 170, 255),
                    (170, 0, 255),
                    (255, 0, 0),
                    (255, 255, 0),
                    (65, 58, 255),
                    (128, 174, 128),]
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
        # Dwa niezależne cache: jeden dla zrenderowanego przekroju DICOM
        # (po windowingu), drugi dla maski. Klucze cache to krotki
        # identyfikujące stan – gdy klucz się zmienia, regenerujemy
        # powierzchnię. Dzięki temu przesuwanie/zoom nie wymusza kosztownego
        # windowingu, a zmiana jasności automatycznie inwaliduje cache.
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
    ) -> None:
        self._screen.fill((0, 0, 0))

        # Klucz zawiera EFEKTYWNE wartości okna (bazowe + delta), a nie same
        # delty – dzięki temu zmiana scanu z innym presetem też unieważni
        # cache, nawet jeśli użytkownik nie ruszał jasności/kontrastu.
        slice_key = (scan_index, plane, slice_index, window_center + window_center_delta, window_width + window_width_delta)
        surface = self._get_slice_surface(image_slice, rescale_slope, rescale_intercept, window_center + window_center_delta, window_width + window_width_delta, slice_key)

        if masks_visible and mask_slice is not None:
            mask_key = (scan_index, plane, slice_index)
            mask_surface = self._get_mask_surface(mask_slice, surface.get_width(), surface.get_height(), mask_key)
            surface.blit(mask_surface, (0, 0))

        # smoothscale zamiast scale – interpolacja bikubiczna daje znacznie
        # lepszy obraz przy powiększeniach niż najbliższy sąsiad. max(1, ...)
        # chroni przed zerowym wymiarem przy bardzo małym zoomie (pygame
        # rzuciłby wtedy wyjątek).
        if zoom != 1.0:
            size = (max(1, int(surface.get_width() * zoom)), max(1, int(surface.get_height() * zoom)))
            surface = pygame.transform.smoothscale(surface, size)

        self._screen.blit(surface, (pan[0], pan[1]))

        self._render_info(
            scan_name, scan_index, scan_count, slice_index, slice_count,
            zoom, plane, masks_visible,
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

    # Budowanie półprzezroczystej powierzchni maski. Dla każdej etykiety
    # (1..N) tworzymy maskę bool i wpisujemy odpowiedni kolor RGB oraz
    # alphę do tablicy RGBA. Następnie musimy przenieść tablicę do pygame
    # przez surfarray – API rozdziela kanały kolorów (blit_array dla RGB)
    # od kanału alpha (pixels_alpha zwraca mutowalny widok z lockiem).
    # Skalowanie do rozmiaru obrazu DICOM robimy na końcu, żeby kolorowe
    # bloki nie były interpolowane z tłem.
    def _get_mask_surface(
        self,
        mask_slice: np.ndarray,
        width: int,
        height: int,
        cache_key: tuple,
    ) -> pygame.Surface:
        if self._cached_mask_key == cache_key and self._cached_mask_surface is not None:
            return self._cached_mask_surface

        rgba = np.zeros((mask_slice.shape[0], mask_slice.shape[1], 4), dtype=np.uint8)
        for label in range(1, len(self.MASK_COLORS)):
            mask = (mask_slice == label)
            rgba[mask, 0] = self.MASK_COLORS[label][0]
            rgba[mask, 1] = self.MASK_COLORS[label][1]
            rgba[mask, 2] = self.MASK_COLORS[label][2]
            rgba[mask, 3] = self.MASK_ALPHA

        # blit_array wspiera tylko RGB – alphę ustawiamy osobno przez
        # pixels_alpha. `del alpha_array` zwalnia surface lock przed
        # dalszym użyciem powierzchni (blit, scale).
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

    # Dolny panel informacyjny. Rysujemy go jako osobną powierzchnię z
    # kanałem alpha (SRCALPHA) wypełnioną czernią z alpha 180 – daje to
    # efekt półprzezroczystego paska pod tekstem, dzięki czemu napisy są
    # czytelne nawet na jasnym obrazie DICOM.
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
    ) -> None:
        lines = [
            f"Scan: {scan_name}  [{scan_index + 1}/{scan_count}]",
            f"Slice: {slice_index + 1}/{slice_count}   Plane: {plane}   Zoom: {zoom:.1f}x   Masks: {'on' if masks_visible else 'off'}",
            f"[<- ->] slice   [up/down] scan   [+/-] zoom   [WASD] pan   [1/2/3] plane   [M/N] masks   [Q/ESC] quit",
        ]
        line_height = self.INFO_FONT_SIZE + 4
        panel_height = len(lines) * line_height + self.INFO_PADDING * 2
        screen_height = self._screen.get_height()
        screen_width = self._screen.get_width()
        panel_y = screen_height - panel_height
        panel_surface = pygame.Surface((screen_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 180))
        self._screen.blit(panel_surface, (0, panel_y))
        color = self.INFO_COLOR
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
