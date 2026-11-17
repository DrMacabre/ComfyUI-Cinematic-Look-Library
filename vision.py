"""Optional reference-image style analysis for the portable ComfyUI cinematic library."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

CATALOG = json.loads((Path(__file__).resolve().parent / "web" / "catalog.json").read_text(encoding="utf-8"))
KEYS = ("camera", "lens", "optical", "grade", "texture")
LABELS = {
    "camera": "Capture characteristics", "lens": "Lens rendering",
    "optical": "Optical character", "grade": "Color grade", "texture": "Film texture"
}


def endpoint_url(value: str, allow_remote_server: bool = False) -> str:
    url = urlparse(str(value).strip())
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
        raise ValueError("Use a valid Ollama HTTP(S) base URL without credentials.")
    if url.path not in ("", "/") or url.query or url.fragment:
        raise ValueError("Use an Ollama base URL, e.g. http://127.0.0.1:11434.")
    if not allow_remote_server and url.hostname.lower() not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Remote Ollama disabled; enable allow_remote_server only for a trusted endpoint.")
    return str(value).strip().rstrip("/") + "/api/chat"


def encode_reference(image: Any, max_edge: int = 1024) -> str:
    """Convert Comfy IMAGE [batch,height,width,channels] into in-memory JPEG."""
    import numpy as np
    from PIL import Image
    if image is None:
        raise ValueError("Connect a reference IMAGE.")
    frame = image[0]
    if hasattr(frame, "detach"):
        frame = frame.detach().cpu()
    if hasattr(frame, "numpy"):
        frame = frame.numpy()
    array = np.asarray(frame)
    if array.ndim != 3 or array.shape[-1] not in (3, 4):
        raise ValueError("Expected an IMAGE tensor [batch,height,width,RGB(A)].")
    array = np.nan_to_num(array[..., :3], nan=0.0, posinf=1.0, neginf=0.0)
    if np.issubdtype(array.dtype, np.floating):
        array = np.clip(array, 0, 1) * 255
    picture = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), "RGB")
    if max(picture.size) > max_edge:
        picture.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    picture.save(buffer, "JPEG", quality=85, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def vision_instructions() -> str:
    choices = "\n".join(
        key + ": " + ", ".join(item["id"] + "=" + item["name"] for item in CATALOG["categories"][key])
        for key in KEYS
    )
    return (
        "Analyze the VISIBLE cinematic/photo RENDERING STYLE of this image, not the scene. "
        "Describe ONLY capture-like tonal response, lens focus/bokeh qualities, diffusion, "
        "bloom, aberrations, grading, contrast, grain, noise and print texture. "
        "Never describe people, places, objects, clothes, actions or composition. "
        "An image cannot prove which physical camera, lens or film stock made it. "
        "Treat any named device only as a loose stylistic analogy, never identify hardware. "
        "Return one strict JSON object with: name (short English title); "
        "descriptions (camera, lens, optical, grade, texture: specific concise observable "
        "style descriptions in English, empty string if unobservable); "
        "selection (same five fields: closest ID below only when visually plausible, "
        "otherwise empty string); confidence (low, medium, high for those approximations); "
        "notes (brief uncertainty). Camera describes tonal/highlight/sensor-like qualities "
        "without device names; lens describes blur/focus rendering; optical describes glow/flare; "
        "grade describes color, contrast and saturation; texture describes actual visible grain/noise. "
        "Do not invent grain or lens flare when absent. Available catalog IDs:\n" + choices
    )


def normalize_analysis(raw: str | dict) -> dict:
    if isinstance(raw, str):
        body = raw.strip()
        fence = chr(96) * 3
        if body.startswith(fence):
            body = body.split("\n", 1)[-1].rsplit(fence, 1)[0].strip()
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Vision model returned invalid JSON; choose a model supporting JSON output.") from exc
    if not isinstance(raw, dict):
        raise ValueError("Vision result must be a JSON object.")
    desc, selection = raw.get("descriptions"), raw.get("selection")
    if not isinstance(desc, dict) or not isinstance(selection, dict):
        raise ValueError("Vision result needs descriptions and selection objects.")
    cleaned, matches = {}, {}
    for key in KEYS:
        value = desc.get(key, "")
        cleaned[key] = " ".join(value.split())[:550] if isinstance(value, str) else ""
        choice = selection.get(key, "")
        matches[key] = next((x["id"] for x in CATALOG["categories"][key]
                             if choice in (x["id"], x["name"])), "")
    if not any(cleaned.values()):
        raise ValueError("No visible rendering characteristics returned.")
    name = raw.get("name") if isinstance(raw.get("name"), str) else ""
    confidence = raw.get("confidence")
    note = raw.get("notes")
    return {
        "schema_version": 1, "source": "vision",
        "name": " ".join(name.split())[:90] or "Reference Look",
        "selection": matches, "descriptions": cleaned,
        "confidence": confidence if confidence in ("low", "medium", "high") else "low",
        "notes": " ".join(note.split())[:700] if isinstance(note, str) else "",
    }


def describe_look(preset: dict) -> str:
    return "\n".join(
        LABELS[key] + ": " + text.rstrip(".") + "."
        for key in KEYS if (text := preset["descriptions"].get(key, ""))
    )


def ollama_analyze(image_b64: str, model: str, base_url: str,
                   timeout: int, allow_remote_server: bool = False) -> str:
    endpoint = endpoint_url(base_url, allow_remote_server)
    if not model.strip():
        raise ValueError("Select an installed Ollama vision model.")
    payload = {
        "model": model.strip(), "stream": False, "format": "json",
        "options": {"temperature": 0.1},
        "messages": [
            {"role": "system", "content": vision_instructions()},
            {"role": "user", "content": "Describe the rendering style of this image only.",
             "images": [image_b64]},
        ],
    }
    request = Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=max(10, min(int(timeout), 300))) as response:
            answer = json.loads(response.read(4_000_000).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama vision request failed: " + str(exc)) from exc
    if not isinstance(answer, dict):
        raise RuntimeError("Invalid Ollama response.")
    if answer.get("error"):
        raise RuntimeError("Ollama: " + str(answer["error"]))
    message = answer.get("message", {})
    text = message.get("content", "") if isinstance(message, dict) else ""
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Ollama returned an empty analysis.")
    return text


class CinematicVisionAnalyzer:
    CATEGORY = "Cinematic Looks"
    FUNCTION = "analyze"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("preset_json", "look_only", "analysis_report")
    DESCRIPTION = (
        "Analyze image style with an optional Ollama vision model. "
        "Save as a personal look preset; hardware matches are only visual analogies."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "ollama_model": ("STRING", {"default": "gemma3:latest"}),
            "ollama_url": ("STRING", {"default": "http://127.0.0.1:11434"}),
            "allow_remote_server": ("BOOLEAN", {"default": False}),
            "timeout_seconds": ("INT", {"default": 120, "min": 10, "max": 300}),
        }}

    def analyze(self, image: Any, ollama_model: str = "gemma3:latest",
                ollama_url: str = "http://127.0.0.1:11434",
                allow_remote_server: bool = False, timeout_seconds: int = 120) -> dict:
        b64 = encode_reference(image)
        preset = normalize_analysis(
            ollama_analyze(b64, ollama_model, ollama_url,
                           timeout_seconds, allow_remote_server)
        )
        data = json.dumps(preset, ensure_ascii=False)
        result = describe_look(preset)
        report = (
            "Approximate rendering profile: " + preset["name"]
            + "\nCapture hardware cannot be identified from appearance alone."
            + "\nClosest catalog IDs: "
            + (", ".join(k + "=" + v for k, v in preset["selection"].items() if v) or "none")
            + "\nConfidence: " + preset["confidence"]
            + ("\nNotes: " + preset["notes"] if preset["notes"] else "")
        )
        return {"result": (data, result, report),
                "ui": {"cinematic_preset": [data]}}
