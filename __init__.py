from .nodes import CinematicLookComposer
from .vision import CinematicVisionAnalyzer

NODE_CLASS_MAPPINGS = {
    "SFT_CinematicLookComposer": CinematicLookComposer,
    "SFT_CinematicVisionAnalyzer": CinematicVisionAnalyzer,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SFT_CinematicLookComposer": "Cinematic Look Mixer",
    "SFT_CinematicVisionAnalyzer": "Cinematic Vision Analyzer",
}
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
