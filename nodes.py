"""Portable cinematic rendering prompt composer for ComfyUI.

No inference/model dependencies. All entries mirror the original SFT look catalog.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).resolve().parent / "web" / "catalog.json"
CATEGORIES = ("camera", "lens", "optical", "grade", "texture")
CATEGORY_LABELS = {
    "camera": "Camera",
    "lens": "Lens",
    "optical": "Optical Character",
    "grade": "Color Grade",
    "texture": "Film Texture",
}
CUSTOM = "Custom Mix"
NONE = "None"
SFT_LOOK_START = "Render the final image as a cinematic film still with a soft, gentle optical character."
SFT_LOOK_END = "\n\nWrite ONE detailed English image-edit instruction"
SFT_TAIL_STYLE = "with its soft, muted, filmic rendering"


def read_catalog() -> dict[str, Any]:
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    for category in CATEGORIES:
        if category not in data.get("categories", {}):
            raise ValueError(f"Missing catalog category: {category}")
    return data


CATALOG = read_catalog()


def get_entry(category: str, value: str) -> dict[str, str] | None:
    if value == NONE or not value:
        return None
    return next(
        (item for item in CATALOG["categories"][category]
         if item["name"] == value or item["id"] == value),
        None,
    )


def get_system_preset(name: str) -> dict[str, Any] | None:
    return next(
        (item for item in CATALOG["system_presets"] if item["name"] == name),
        None,
    )


def look_text(selection: dict[str, str]) -> str:
    lines = []
    for category in CATEGORIES:
        entry = get_entry(category, selection.get(category, NONE))
        if entry is not None:
            lines.append(
                f'{CATEGORY_LABELS[category]}: {entry["name"]} — {entry["render"]}.'
            )
    return "\n".join(lines)


def compose_cinematic_prompt(
    base_prompt: str,
    selection: dict[str, str],
    enabled: bool = True,
    replace_sft_look: bool = True,
) -> tuple[str, str]:
    """Return (complete prompt, look-only block). Non-selected mode is a no-op."""
    base_prompt = str(base_prompt or "")
    rendered = look_text(selection)
    if not enabled or not rendered:
        return (base_prompt, "")

    look = (
        "Selected cinematic rendering profile "
        "(camera / lens / optical treatment / color grade / film texture):\n"
        + rendered
    )

    if replace_sft_look:
        start = base_prompt.find(SFT_LOOK_START)
        end = base_prompt.find(SFT_LOOK_END, start) if start >= 0 else -1
        if start >= 0 and end > start:
            suffix = base_prompt[end:].replace(
                SFT_TAIL_STYLE, "with the selected cinematic rendering profile", 1
            )
            return (base_prompt[:start] + look + suffix, look)

    # Generic ComfyUI prompts are not rewritten: the chosen look is appended.
    separator = "\n\n" if base_prompt else ""
    result = (
        base_prompt + separator + look
        + "\nApply this selected profile to the photographic rendering "
        "without altering the requested subjects, composition or setting."
    )
    return (result, look)


class CinematicLookComposer:
    """Mix five independent choices or recall a bundled system preset."""

    CATEGORY = "Cinematic Looks"
    FUNCTION = "compose"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "look_only")
    DESCRIPTION = (
        "Select camera, lens, optical character, color grade and film texture. "
        "Outputs a full prompt and a look-only block. No LLM required."
    )

    @classmethod
    def INPUT_TYPES(cls):
        categories = CATALOG["categories"]
        presets = [CUSTOM] + [
            item["name"] for item in CATALOG["system_presets"]
        ]
        return {
            "required": {
                "base_prompt": ("STRING", {"default": "", "multiline": True}),
                "preset": (presets, {"default": CUSTOM}),
                "camera": ([NONE] + [x["name"] for x in categories["camera"]],),
                "lens": ([NONE] + [x["name"] for x in categories["lens"]],),
                "optical": ([NONE] + [x["name"] for x in categories["optical"]],),
                "grade": ([NONE] + [x["name"] for x in categories["grade"]],),
                "texture": ([NONE] + [x["name"] for x in categories["texture"]],),
                "enabled": ("BOOLEAN", {"default": True}),
                "replace_sft_look": ("BOOLEAN", {"default": True}),
            },
        }

    def compose(
        self,
        base_prompt: str,
        preset: str = CUSTOM,
        camera: str = NONE,
        lens: str = NONE,
        optical: str = NONE,
        grade: str = NONE,
        texture: str = NONE,
        enabled: bool = True,
        replace_sft_look: bool = True,
    ):
        selection = {
            "camera": camera,
            "lens": lens,
            "optical": optical,
            "grade": grade,
            "texture": texture,
        }
        system_preset = get_system_preset(preset)
        if system_preset:
            selection = system_preset["selection"]
        return compose_cinematic_prompt(
            base_prompt,
            selection,
            enabled=enabled,
            replace_sft_look=replace_sft_look,
        )
