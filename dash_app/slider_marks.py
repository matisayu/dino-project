""" Mark-dict builders for dcc.RangeSlider. """

import math

def geo_age_marks(boundaries: list) -> dict:
    """Generate marks for the Geological Age RangeSlider, keyed by index position.

    Called when building slider div in app.py

    Args:
        boundaries (list[str]): Ma boundary strings, oldest to youngest,
            e.g. ['251.9 Ma', '247.2 Ma', ..., '66.0 Ma'].
            Ingested from 'assets/transforms.js'  

    Returns:
        dict[int, str]: {index: label}, one entry per boundary to pass
        to dcc.RangeSlider's `marks` prop.
    """
    return {i: boundary for i, boundary in enumerate(boundaries)}  # index -> label text


def year_marks(year_min: int, year_max: int, step: int = 25) -> dict:
    """Generate marks for the Discovery Year RangeSlider.

    Places a mark at every multiple of `step` within (year_min, year_max),
    year_min and year_max are always included.

    Args:
        year_min (int): minimum selectable year.
        year_max (int): maximum selectable year.
        step (int, optional): year spacing between marks

    Returns:
        dict[int, str]: {year: label}, ready to pass  to 
        dcc.RangeSlider's `marks` prop.
    """
    
    min_gap = step * 0.4  # minimum allowed spacing between two marks in years

    # first multiple of step at or after year_min, ex: math.ceil(1758 / 25) * 25 = 1775
    first_interior = math.ceil(year_min / step) * step
    interior = list(range(first_interior, year_max, step))  # every step-th year, up to year_max

    # Check if first and last marks meet min_gap
    if interior and interior[0] - year_min < min_gap:
        interior.pop(0)
    if interior and year_max - interior[-1] < min_gap:
        interior.pop()  

    marks = [year_min] + interior + [year_max]
    return {m: str(m) for m in marks}  # dcc.RangeSlider ingests {value: label}
