from dataclasses import dataclass

import numpy as np


@dataclass
class NrrdMask:
    volume: np.ndarray
    series_number: int