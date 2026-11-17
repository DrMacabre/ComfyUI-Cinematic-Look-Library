import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cinematic_nodes", ROOT / "nodes.py")
nodes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nodes)


class CinematicLookTests(unittest.TestCase):
    def test_catalog_counts(self):
        self.assertEqual(
            [len(nodes.CATALOG["categories"][key]) for key in nodes.CATEGORIES],
            [9, 9, 10, 10, 8],
        )
        self.assertEqual(len(nodes.CATALOG["system_presets"]), 5)

    def test_node_contract(self):
        cls = nodes.CinematicLookComposer
        self.assertEqual(cls.RETURN_TYPES, ("STRING", "STRING"))
        fields = cls.INPUT_TYPES()["required"]
        for key in ("base_prompt", "preset", *nodes.CATEGORIES, "enabled"):
            self.assertIn(key, fields)

    def test_mix_and_look_only(self):
        node = nodes.CinematicLookComposer()
        prompt, look = node.compose(
            "One adult in a cafe", camera="ARRI ALEXA 35", lens="Cooke Panchro Classic",
            grade="Warm Faded", texture="Fine 35mm Grain",
        )
        self.assertTrue(prompt.startswith("One adult in a cafe"))
        self.assertIn("ARRI ALEXA 35", prompt)
        self.assertIn("Cooke Panchro Classic", prompt)
        self.assertIn("Warm Faded", prompt)
        self.assertIn("Fine 35mm Grain", look)

    def test_disabled_is_exact_noop(self):
        base = "preserve  camera + lens\n"
        prompt, look = nodes.CinematicLookComposer().compose(
            base, enabled=False, camera="ARRI ALEXA 35",
        )
        self.assertEqual((prompt, look), (base, ""))

    def test_none_is_exact_noop(self):
        self.assertEqual(nodes.CinematicLookComposer().compose("Original"), ("Original", ""))

    def test_system_preset_overrides_manual_selections(self):
        prompt, look = nodes.CinematicLookComposer().compose(
            "Scene", preset="Classic Cooke Warm", camera="Sony VENICE 2",
        )
        self.assertIn("ARRI ALEXA 35", prompt)
        self.assertNotIn("Sony VENICE 2", prompt)
        self.assertIn("Cooke Panchro Classic", look)

    def test_sft_fixed_look_replaced(self):
        base = ("Preserve all identity details.\n\n" + nodes.SFT_LOOK_START
                + " Existing warm soft look.\n\n"
                + "Write ONE detailed English image-edit instruction "
                + nodes.SFT_TAIL_STYLE + ".")
        prompt, _ = nodes.CinematicLookComposer().compose(
            base, camera="Sony VENICE 2",
        )
        self.assertIn("Preserve all identity details", prompt)
        self.assertNotIn("Existing warm soft look", prompt)
        self.assertNotIn(nodes.SFT_TAIL_STYLE, prompt)
        self.assertIn("Sony VENICE 2", prompt)
        self.assertIn("with the selected cinematic rendering profile", prompt)

    def test_generic_base_not_rewritten(self):
        base = "A subject in full-body profile under indoor light."
        prompt, _ = nodes.CinematicLookComposer().compose(
            base, optical="Creamy Shallow Focus",
        )
        self.assertTrue(prompt.startswith(base))
        self.assertIn("Creamy Shallow Focus", prompt)

    def test_all_preset_references_exist(self):
        for preset in nodes.CATALOG["system_presets"]:
            for key in nodes.CATEGORIES:
                self.assertIsNotNone(
                    nodes.get_entry(key, preset["selection"][key]),
                    (preset["name"], key),
                )


if __name__ == "__main__":
    unittest.main()
