import numpy as np


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