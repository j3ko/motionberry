from .base_algorithm import BaseAlgorithm
from .frame_diff_algorithm import FrameDiffAlgorithm
from .background_subtraction_algorithm import BackgroundSubtractionAlgorithm


def get_motion_algorithm(name, threshold) -> BaseAlgorithm:
    name = name.lower()
    if name == "frame_diff":
        return FrameDiffAlgorithm(threshold)
    elif name == "background":
        return BackgroundSubtractionAlgorithm(threshold)
    else:
        raise ValueError(f"Unknown motion detection algorithm: {name}")
