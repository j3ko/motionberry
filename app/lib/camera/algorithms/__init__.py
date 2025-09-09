import logging
from .base_algorithm import BaseAlgorithm
from .frame_diff_algorithm import FrameDiffAlgorithm
from .background_subtraction_algorithm import BackgroundSubtractionAlgorithm

def get_motion_algorithm(name, **kwargs) -> BaseAlgorithm:
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

    logger.debug(f"Creating algorithm '{name}' with kwargs: {kwargs}")

    if name == "frame_diff":
        return FrameDiffAlgorithm(
            motion_threshold=kwargs.get("motion_threshold", 5),
            blur_strength=kwargs.get("blur_strength", 0),
            detection_frames=kwargs.get("detection_frames", 3)
        )
    elif name == "background":
        return BackgroundSubtractionAlgorithm(
            motion_threshold=kwargs.get("motion_threshold", 5),
            blur_strength=kwargs.get("blur_strength", 0),
            detection_frames=kwargs.get("detection_frames", 3)
        )
    else:
        logger.error(f"Unknown motion detection algorithm: {name}")
        raise ValueError(f"Unknown motion detection algorithm: {name}")