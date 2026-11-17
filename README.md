# ComfyUI Cinematic Look Library

A portable **cinematic look mixer** for regular ComfyUI image workflows, adapted from the SFT Film Studio cinematic look library.

Mix five independently selectable categories: **Camera**, **Lens**, **Optical Character**, **Color Grade**, and **Film Texture**. Save, recall, rename, duplicate, delete, import, and export personal presets. Comes with 46 original component profiles and five system presets.

**The original mixer requires no Ollama, Qwen, SFT, checkpoint, or extra Python dependencies.** The optional Vision Analyzer needs a running Ollama vision model, but no additional Python packages beyond regular ComfyUI. Both nodes produce prompt text; your image model performs the rendering. Named cameras and lenses are *visual prompts*, not an actual camera/optical simulation, so results depend on the image model.

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

The mixer only composes text. The separate optional Vision Analyzer calls your chosen Ollama VLM to describe reference-image rendering; neither node generates images. You may still connect your own LLM or wildcard processor.

enabled = false passes the original base_prompt through untouched. replace_sft_look = true replaces the known original SFT cinematic rendering paragraph when present; for any other prompt, the selected look is appended without rewriting subject descriptions.

### Preset storage

- **System presets** are included in web/catalog.json.
- **Personal presets** are saved to the current browser's local storage and can be transferred with Export / Import JSON.
- Applied combinations are also stored in normal workflow node widget values, so a saved ComfyUI workflow carries its chosen settings even to another machine.
- Presets exported from the SFT Cinematic Look Library use compatible category IDs and can be imported here.
- These are **fixed, user-selectable settings**, not random wildcards.

### Previews

The gallery supports an optional thumbnail field in the catalog. Preview images are intentionally **not included yet**. Placeholder cards remain until representative images are generated from a common source image for each profile.

## Reference-image vision analyzer (optional)

Add **Cinematic Looks > Cinematic Vision Analyzer** and connect **Load Image > IMAGE**.
The analyzer sends a reduced in-memory JPEG (first frame, maximum 1024 px on the long edge)
to a locally installed **Ollama vision model**. Install Ollama separately only if you
want to use this optional analysis feature; **the original Cinematic Look Mixer needs
no LLM**.

1. Run Ollama with a vision-capable model (for example gemma3:latest, if installed).
2. Set ollama_model to that exact model name. The default endpoint is
   http://127.0.0.1:11434.
3. For an Ollama server on another trusted computer, set ollama_url and explicitly
   enable allow_remote_server. The image is sent to that endpoint, **not** to
   GitHub or an external API by default. Do not enable remote servers you do not trust.
4. Run the ComfyUI queue. The analyzer outputs preset_json, look_only,
   and analysis_report.
5. To apply immediately, connect preset_json to the Mixer's optional
   vision_preset STRING input. When a connection is present it overrides the
   Mixer's custom selections; disconnect it to return to manual mixing.
6. To save the analysis, click **Save Vision Preset** on the analyzer node
   *after it has executed*. Open the Mixer's **Cinematic Look Library** and find
   the new entry under **My presets**. It may then be mixed with the existing
   camera, lens, optical, color, and texture options.
7. Use Export to transfer saved presets between browsers or machines.

The analyzed preset stores five **independent freeform technical descriptions** in
addition to approximate matches in the existing catalog. Even if the source image
looks unlike all 46 built-in components, the analysis is preserved rather than
being forcibly assigned a known camera. When replacing one category in the picker,
only that category's analyzed description is removed; the other four remain.

**Important:** Visual analysis cannot prove the physical camera, lens or film stock
that captured an image. The returned names are approximate aesthetic references,
not hardware identification. Results depend strongly on the vision model. The
analyzer does not automatically render or compare a reconstructed reference;
review generated images before treating a preset as validated.

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

This is a classic NODE_CLASS_MAPPINGS ComfyUI custom node with a standard frontend extension registered through app.registerExtension. No proprietary SFT routes or project structure are used. It outputs ordinary STRING data, compatible with other custom nodes that accept string prompts. Tested with isolated Python unit tests and JavaScript static checks; the Ollama request/response path is mocked in tests. Actual model inference and frontend compatibility with every ComfyUI version have not been verified.

## Tests

From the repository root: python -m unittest discover -s tests -v

## Credits

Original concept and look library: DrMacabre / SFT Film Studio.

Camera and lens names are used descriptively. This project is independent of the named equipment manufacturers.
