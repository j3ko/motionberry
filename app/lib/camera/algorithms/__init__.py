import logging
from .base_algorithm import BaseAlgorithm
from .frame_diff_algorithm import FrameDiffAlgorithm
from .background_subtraction_algorithm import BackgroundSubtractionAlgorithm

def get_motion_algorithm(name, motion_threshold, blur_strength, detection_frames) -> BaseAlgorithm:
    """Instantiate a motion detection algorithm based on the given name.

    Args:
        name (str): Name of the algorithm ('frame_diff' or 'background').
        **kwargs: Algorithm-specific parameters (motion_threshold, blur_strength, detection_frames).

    Returns:
        BaseAlgorithm: Instance of the specified motion detection algorithm.

    Raises:
        ValueError: If the algorithm name is unknown.
    """
    logger = logging.getLogger(__name__)
    name = name.lower()

    if name == "frame_diff":
        return FrameDiffAlgorithm(
            motion_threshold,
            blur_strength,
            detection_frames
        )
    elif name == "background":
        return BackgroundSubtractionAlgorithm(
            motion_threshold,
            blur_strength,
            detection_frames
        )
    else:
        logger.error(f"Unknown motion detection algorithm: {name}")
        raise ValueError(f"Unknown motion detection algorithm: {name}")