from .nodes import CinematicLookComposer

NODE_CLASS_MAPPINGS = {
    "SFT_CinematicLookComposer": CinematicLookComposer,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SFT_CinematicLookComposer": "Cinematic Look Mixer",
}
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
