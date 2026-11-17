import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import numpy as np
except ImportError:  # isolated sandbox may lack system BLAS
    np = None

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cinematic_vision", ROOT / "vision.py")
vision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vision)
spec2 = importlib.util.spec_from_file_location("cinematic_nodes", ROOT / "nodes.py")
nodes = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(nodes)


def analyzed():
    return {
        "name": "Soft Cool Print",
        "descriptions": {
            "camera": "Natural highlight shoulder and deep midtones",
            "lens": "Soft falloff and oval background blur",
            "optical": "Fine glow around practical lights",
            "grade": "Desaturated cool blues with warm skin tones",
            "texture": "Subtle uneven visible grain",
        },
        "selection": {
            "camera": "alexa35", "lens": "panac",
            "optical": "glow", "grade": "cyan", "texture": "fine",
        },
        "confidence": "low",
        "notes": "Camera identity not verifiable",
    }


class VisionTests(unittest.TestCase):
    def test_json_normalization(self):
        preset = vision.normalize_analysis(json.dumps(analyzed()))
        self.assertEqual(preset["source"], "vision")
        self.assertEqual(preset["selection"]["lens"], "panac")
        self.assertIn("oval background blur", preset["descriptions"]["lens"])
        self.assertIn("Color grade", vision.describe_look(preset))

    def test_unlisted_equipment_does_not_block_descriptions(self):
        data = analyzed()
        data["selection"] = {key: "unsupported-camera-or-lens" for key in vision.KEYS}
        data["descriptions"]["lens"] = "Highly unusual off-axis coma with faceted bokeh"
        result = vision.normalize_analysis(data)
        self.assertEqual(result["selection"]["lens"], "")
        self.assertIn("faceted bokeh", result["descriptions"]["lens"])
        prompt, look = nodes.CinematicLookComposer().compose(
            "A studio portrait", vision_preset=json.dumps(result))
        self.assertIn("faceted bokeh", prompt)
        self.assertIn("faceted bokeh", look)

    def test_mixer_accepts_rich_vision_preset(self):
        preset = vision.normalize_analysis(analyzed())
        prompt, look = nodes.CinematicLookComposer().compose(
            "A person sitting", camera="Sony VENICE 2",
            vision_preset=json.dumps(preset))
        self.assertIn("Natural highlight shoulder", prompt)
        self.assertIn("Soft falloff and oval", look)
        self.assertIn("nearest catalog analogy: ARRI ALEXA 35", look)
        self.assertNotIn("Sony VENICE 2", look)

    def test_disable_does_not_parse_vision_json(self):
        prompt, look = nodes.CinematicLookComposer().compose(
            "Unchanged", enabled=False, vision_preset="broken JSON")
        self.assertEqual((prompt, look), ("Unchanged", ""))

    def test_system_preset_not_overridden_by_vision(self):
        preset = vision.normalize_analysis(analyzed())
        prompt, look = nodes.CinematicLookComposer().compose(
            "Scene", preset="Clean Premium Digital",
            vision_preset=json.dumps(preset))
        self.assertIn("Sony VENICE 2", look)
        self.assertNotIn("Soft falloff and oval", look)

    def test_empty_analysis_rejected(self):
        with self.assertRaises(ValueError):
            vision.normalize_analysis({"selection": {}, "descriptions": {}})

    def test_invalid_json_rejected(self):
        with self.assertRaises(ValueError):
            vision.normalize_analysis("not JSON")

    def test_endpoint_guard(self):
        self.assertEqual(
            vision.endpoint_url("http://127.0.0.1:11434"),
            "http://127.0.0.1:11434/api/chat")
        with self.assertRaises(ValueError):
            vision.endpoint_url("http://192.168.1.1:11434")
        with self.assertRaises(ValueError):
            vision.endpoint_url("http://localhost:11434/custom")
        self.assertEqual(vision.endpoint_url("http://192.168.1.1:11434", True),
                         "http://192.168.1.1:11434/api/chat")

    @unittest.skipIf(np is None, 'sandbox NumPy unavailable; ComfyUI installs NumPy')
    def test_comfy_image_encoding(self):
        img = np.zeros((1, 24, 32, 3), dtype=np.float32)
        encoded = vision.encode_reference(img)
        import base64
        from PIL import Image
        import io
        picture = Image.open(io.BytesIO(base64.b64decode(encoded)))
        self.assertEqual(picture.size, (32, 24))
        self.assertEqual(picture.mode, "RGB")

    def test_node_ui_preset_roundtrip(self):
        original = vision.ollama_analyze
        try:
            vision.ollama_analyze = lambda *args, **kwargs: json.dumps(analyzed())
            with patch.object(vision, "encode_reference", return_value="fixture-base64"):
                result = vision.CinematicVisionAnalyzer().analyze(object())
            self.assertIn("cinematic_preset", result["ui"])
            exported, rendered, report = result["result"]
            self.assertEqual(result["ui"]["cinematic_preset"][0], exported)
            composed, look = nodes.CinematicLookComposer().compose(
                "Test photograph", vision_preset=exported)
            self.assertIn("Fine glow around practical lights", composed)
            self.assertIn("Fine glow around practical lights", look)
            self.assertIn("cannot be identified", report)
        finally:
            vision.ollama_analyze = original

    def test_ollama_request_contract(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, amount):
                return json.dumps({"message":{"content":json.dumps(analyzed())}}).encode()
        with patch.object(vision, "urlopen", return_value=FakeResponse()) as remote:
            text = vision.ollama_analyze("abcd", "vision-test", "http://127.0.0.1:11434", 40)
            self.assertEqual(json.loads(text)["name"], "Soft Cool Print")
            req = remote.call_args.args[0]
            payload = json.loads(req.data)
            self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(payload["messages"][1]["images"], ["abcd"])
            self.assertEqual(payload["format"], "json")
            self.assertEqual(payload["stream"], False)

    def test_descriptions_preserve_nonreference_camera_style(self):
        data = analyzed()
        data["selection"]["camera"] = ""
        data["descriptions"]["camera"] = "Liquid silver-patina tone mapping with compressed highlights"
        preset = vision.normalize_analysis(data)
        output, _ = nodes.CinematicLookComposer().compose(
            "Some subjects", vision_preset=json.dumps(preset))
        self.assertIn("Liquid silver-patina", output)
        self.assertNotIn("ARRI ALEXA 35", output)


if __name__ == "__main__":
    unittest.main()
