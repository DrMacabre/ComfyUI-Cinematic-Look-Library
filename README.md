# ComfyUI Cinematic Look Library

A portable **cinematic look mixer** for regular ComfyUI image workflows, adapted from the SFT Film Studio cinematic look library.

Mix five independently selectable categories: **Camera**, **Lens**, **Optical Character**, **Color Grade**, and **Film Texture**. Save, recall, rename, duplicate, delete, import, and export personal presets. Comes with 46 original component profiles and five system presets.

**No Ollama, Qwen, SFT, checkpoint, or extra Python dependencies are required.** This node creates descriptive prompt text; your existing image model renders it. Named cameras and lenses are *visual prompts*, not an actual camera/optical simulation, so results depend on the image model.

## Install

1. Download or clone this repository into ComfyUI/custom_nodes/ComfyUI-Cinematic-Look-Library/.
2. Restart ComfyUI and refresh the browser.
3. Add **Cinematic Looks → Cinematic Look Mixer** to any image workflow.

There are no additional Python requirements.

## Use

1. Enter a base_prompt, or connect a STRING output to it (convert the text widget to an input where supported).
2. Choose Custom Mix and pick components, or select a bundled preset.
3. Click **Open Cinematic Library** to browse the component gallery and manage personal presets.
4. Connect the prompt output to a text encoder's prompt input (often CLIP Text Encode after converting its text widget to an input).
5. The optional look_only output contains just the cinematic rendering instructions for pipelines that merge text elsewhere.

The node only composes text; it does not generate images or rewrite prompts with a language model. You can connect your own LLM or wildcard processor before or after this node.

enabled = false passes the original base_prompt through untouched. replace_sft_look = true replaces the known original SFT cinematic rendering paragraph when present; for any other prompt, the selected look is appended without rewriting subject descriptions.

### Preset storage

- **System presets** are included in web/catalog.json.
- **Personal presets** are saved to the current browser's local storage and can be transferred with Export / Import JSON.
- Applied combinations are also stored in normal workflow node widget values, so a saved ComfyUI workflow carries its chosen settings even to another machine.
- Presets exported from the SFT Cinematic Look Library use compatible category IDs and can be imported here.
- These are **fixed, user-selectable settings**, not random wildcards.

### Previews

The gallery supports an optional thumbnail field in the catalog. Preview images are intentionally **not included yet**. Placeholder cards remain until representative images are generated from a common source image for each profile.

## Categories

| Category | Entries |
| --- | ---: |
| Camera | 9 |
| Lens | 9 |
| Optical Character | 10 |
| Color Grade | 10 |
| Film Texture | 8 |

System presets: Classic Cooke Warm, 70s Gritty Anamorphic, Prestige Natural Alexa, Dreamy Period Film, Clean Premium Digital.

## Compatibility

This is a classic NODE_CLASS_MAPPINGS ComfyUI custom node with a standard frontend extension registered through app.registerExtension. No proprietary SFT routes or project structure are used. It outputs ordinary STRING data, compatible with other custom nodes that accept string prompts. Tested with isolated Python unit tests and JavaScript static checks; integration with every version of ComfyUI and every model has not been verified.

## Tests

From the repository root: python -m unittest discover -s tests -v

## Credits

Original concept and look library: DrMacabre / SFT Film Studio.

Camera and lens names are used descriptively. This project is independent of the named equipment manufacturers.
