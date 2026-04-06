import numpy as np


# Skaner CT mierzy jak bardzo każdy punkt w ciele pochłania promieniowanie rentgenowskie
# i zapisuje to jako liczby zwane jednostkami Hounsfielda (HU):
#   powietrze  ≈ -1000 HU
#   woda       ≈     0 HU
#   kość       ≈ +1000 HU i więcej
#
# Monitor wyświetla kolory jako liczby 0–255, więc pełny zakres HU trzeba zmieścić na ekranie.
# Naiwne rozciągnięcie całego zakresu (-1000…+1000) na 0–255 daje fatalny kontrast —
# kości i tkanki miękkie wyglądają prawie tak samo.
#
# Okienkowanie rozwiązuje ten problem: zamiast pokazywać wszystko, wybierany jest tylko
# fragment zakresu i rozciągany na pełne 0–255. Analogia: zoom na aparacie —
# nie powiększa się całego zdjęcia, tylko wybrany wycinek.
# Przykład dla tkanek miękkich: zakres [-150, 250] HU — wszystko poniżej jest czarne,
# powyżej białe, a środek ma pełny kontrast.
def apply_windowing(
    pixel_array: np.ndarray,
    rescale_slope: float,
    rescale_intercept: float,
    window_center: float,
    window_width: float,
) -> np.ndarray:
    hu = pixel_array.astype(np.float32) * rescale_slope + rescale_intercept
    low = window_center - window_width / 2.0
    high = window_center + window_width / 2.0
    hu_clipped = np.clip(hu, low, high)
    normalized = (hu_clipped - low) / (high - low) * 255.0
    return normalized.astype(np.uint8)


def grayscale_to_rgb(gray: np.ndarray) -> np.ndarray:
    return np.stack([gray, gray, gray], axis=-1)


def to_pygame_surface_array(rgb: np.ndarray) -> np.ndarray:
    return np.transpose(rgb, (1, 0, 2))