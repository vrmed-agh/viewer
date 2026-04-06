from dataclasses import dataclass

import numpy as np


@dataclass
class SliceData:
    pixel_array: np.ndarray
    instance_number: int
    slice_location: float
    rows: int
    cols: int
    rescale_slope: float = 1.0
    rescale_intercept: float = 0.0
    window_center: float = 50.0
    window_width: float = 500.0