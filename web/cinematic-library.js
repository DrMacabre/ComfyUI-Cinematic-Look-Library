import { app } from "/scripts/app.js";

const NODE_NAME = "SFT_CinematicLookComposer";
const VISION_NODE_NAME = "SFT_CinematicVisionAnalyzer";
const STORAGE_KEY = "comfy:cinematic-look-library:presets:v1";
const KEYS = ["camera", "lens", "optical", "grade", "texture"];
const LABELS = {
  camera: "Camera", lens: "Lens", optical: "Optical Character",
  grade: "Color Grade", texture: "Film Texture",
};
const catalogURL = new URL("./catalog.json", import.meta.url);
let catalogRequest;

function getCatalog() {
  if (!catalogRequest) {
    catalogRequest = fetch(catalogURL).then((response) => {
      if (!response.ok) throw new Error("Cinematic catalog not available");
      return response.json();
    }).catch((error) => { catalogRequest = null; throw error; });
  }
  return catalogRequest;
}
function getPresets() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(data) ? data.filter((x) =>
      x && typeof x.id === "string" && typeof x.name === "string"
      && x.selection && typeof x.selection === "object"
    ) : [];
  } catch { return []; }
}
function storePresets(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}
function readWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}
function writeWidget(node, name, value) {
  const widget = readWidget(node, name);
  if (!widget) return;
  widget.value = value;
  widget.callback?.(value, node);
  node.setDirtyCanvas?.(true, true);
}
function findItem(catalog, key, idOrName) {
  return catalog.categories[key].find(
    (entry) => entry.id === idOrName || entry.name === idOrName
  );
}
function selected(node, catalog) {
  const result = {};
  for (const key of KEYS) {
    result[key] = findItem(catalog, key, readWidget(node, key)?.value)?.id || "";
  }
  return result;
}
function readVisionRecipe(node) {
  try {
    const raw = readWidget(node, "vision_preset")?.value;
    if (!raw || typeof raw !== "string") return null;
    const data = JSON.parse(raw);
    return data && typeof data === "object" && data.descriptions
      && typeof data.descriptions === "object" ? data : null;
  } catch { return null; }
}
function cleanDescriptions(descriptions) {
  const result = {};
  for (const key of KEYS) {
    const text = descriptions?.[key];
    result[key] = typeof text === "string" ? text.trim().slice(0, 550) : "";
  }
  return result;
}
function loadSelection(node, catalog, selection, descriptions = null) {
  for (const key of KEYS) {
    const item = findItem(catalog, key, selection[key]);
    writeWidget(node, key, item?.name || "None");
  }
  writeWidget(node, "preset", "Custom Mix");
  writeWidget(node, "enabled", true);
  const rich = descriptions && Object.values(cleanDescriptions(descriptions)).some(Boolean);
  const recipe = rich ? {schema_version:1, source:"vision",
    selection: Object.fromEntries(KEYS.map(k => [k, selection[k] || ""])),
    descriptions:cleanDescriptions(descriptions)} : null;
  writeWidget(node, "vision_preset", recipe ? JSON.stringify(recipe) : "");
}
function changeComponent(node, catalog, key, value) {
  const item = findItem(catalog, key, value);
  writeWidget(node, key, item?.name || "None");
  writeWidget(node, "preset", "Custom Mix");
  const recipe = readVisionRecipe(node);
  if (recipe) {
    recipe.selection = recipe.selection && typeof recipe.selection === "object"
      ? recipe.selection : {};
    recipe.selection[key] = item?.id || "";
    recipe.descriptions = cleanDescriptions(recipe.descriptions);
    recipe.descriptions[key] = "";
    writeWidget(node, "vision_preset", JSON.stringify(recipe));
  }
}
function snapshot(node, catalog) {
  const recipe = readVisionRecipe(node);
  return {selection:selected(node, catalog),
    ...(recipe ? {descriptions:cleanDescriptions(recipe.descriptions), source:"vision"} : {})};
}
function el(tag, klass, text) {
  const element = document.createElement(tag);
  if (klass) element.className = klass;
  if (text !== undefined) element.textContent = text;
  return element;
}
function makeButton(label, callback) {
  const button = el("button", "", label);
  button.type = "button";
  button.addEventListener("click", callback);
  return button;
}
function ensureStyles() {
  if (document.getElementById("sft-cinematic-library-css")) return;
  const stylesheet = document.createElement("link");
  stylesheet.id = "sft-cinematic-library-css";
  stylesheet.rel = "stylesheet";
  stylesheet.href = new URL("./library.css", import.meta.url).href;
  document.head.append(stylesheet);
}
function download(filename, value) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function showLibrary(node) {
  const catalog = await getCatalog();
  ensureStyles();
  const nativePreset = readWidget(node, "preset")?.value;
  const builtIn = catalog.system_presets.find((entry) => entry.name === nativePreset);
  if (builtIn) loadSelection(node, catalog, builtIn.selection);
  let presets = getPresets();
  let category = KEYS[0];
  let active = "";
  let search = "";
  const previousFocus = document.activeElement;

  const overlay = el("div", "sft-cine-overlay");
  const dialog = el("section", "sft-cine-dialog");
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-label", "Cinematic Look Library");
  overlay.append(dialog);
  document.body.append(overlay);
  const close = () => {
    overlay.remove();
    document.removeEventListener("keydown", onKey);
    previousFocus?.focus?.();
  };
  const onKey = (event) => {
    if (event.key === "Escape") { event.preventDefault(); close(); }
  };
  document.addEventListener("keydown", onKey);
  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) close();
  });

  const header = el("header");
  header.append(el("strong", "", "Cinematic Look Library"));
  header.append(makeButton("Done ×", close));
  dialog.append(header);

  const tabs = el("nav", "sft-cine-tabs");
  dialog.append(tabs);
  const body = el("div", "sft-cine-body");
  const gallery = el("main");
  const searchBox = el("input");
  searchBox.type = "search";
  searchBox.placeholder = "Search cinematic components";
  searchBox.setAttribute("aria-label", "Search cinematic components");
  searchBox.addEventListener("input", () => { search = searchBox.value; renderGallery(); });
  gallery.append(searchBox);
  const cards = el("div", "sft-cine-cards");
  gallery.append(cards);
  const sidebar = el("aside", "sft-cine-side");
  body.append(gallery, sidebar);
  dialog.append(body);

  function renderTabs() {
    tabs.replaceChildren();
    for (const key of KEYS) {
      const b = makeButton(LABELS[key], () => {
        category = key; search = ""; searchBox.value = ""; render();
      });
      b.setAttribute("aria-pressed", String(category === key));
      tabs.append(b);
    }
  }
  function renderGallery() {
    cards.replaceChildren();
    for (const item of catalog.categories[category]) {
      if (!(item.name + " " + item.render).toLowerCase().includes(search.toLowerCase())) continue;
      const button = makeButton("", () => {
        changeComponent(node, catalog, category, item.name);
        render();
      });
      button.className = "sft-cine-card";
      button.setAttribute("aria-pressed",
        String(readWidget(node, category)?.value === item.name));
      if (item.thumbnail) {
        const image = el("img");
        image.loading = "lazy";
        image.alt = "";
        image.src = new URL(item.thumbnail, catalogURL).href;
        button.append(image);
      } else {
        button.append(el("span", "sft-cine-placeholder", "Preview pending"));
      }
      button.append(el("strong", "", item.name), el("small", "", item.render));
      cards.append(button);
    }
  }
  function saveNew(defaultName = "My Cinematic Look") {
    const name = window.prompt("Preset name", defaultName)?.trim();
    if (!name) return;
    if (presets.some((p) => p.name.toLowerCase() === name.toLowerCase())) {
      window.alert("This preset name is already taken.");
      return;
    }
    const id = "user-" + Date.now() + "-" + Math.random().toString(36).slice(2, 7);
    presets.push({ id, name, ...snapshot(node, catalog) });
    storePresets(presets);
    active = id;
    render();
  }
  function currentPreset() { return presets.find((x) => x.id === active); }
  function update() {
    const entry = currentPreset(); if (!entry) return;
    Object.assign(entry, snapshot(node, catalog));
    if (!readVisionRecipe(node)) { delete entry.descriptions; delete entry.source; }
    storePresets(presets); render();
  }
  function rename() {
    const entry = currentPreset(); if (!entry) return;
    const name = window.prompt("Rename preset", entry.name)?.trim();
    if (!name) return;
    if (presets.some((p) => p !== entry && p.name.toLowerCase() === name.toLowerCase())) {
      window.alert("This preset name is already taken."); return;
    }
    entry.name = name;
    storePresets(presets); render();
  }
  function remove() {
    const entry = currentPreset();
    if (!entry || !window.confirm('Delete preset "' + entry.name + '"?')) return;
    presets = presets.filter((p) => p !== entry);
    active = "";
    storePresets(presets); render();
  }
  async function importFile(file) {
    try {
      const parsed = JSON.parse(await file.text());
      const incoming = Array.isArray(parsed) ? parsed : parsed?.presets;
      if (!Array.isArray(incoming)) throw new Error("Invalid presets file");
      let added = 0;
      for (const entry of incoming.slice(0, 500)) {
        if (!entry || typeof entry.name !== "string"
            || !entry.name.trim() || entry.name.length > 200
            || !entry.selection || typeof entry.selection !== "object") continue;
        const name = entry.name.trim();
        if (presets.some((p) => p.name.toLowerCase() === name.toLowerCase())) continue;
        const selection = {};
        for (const key of KEYS) {
          selection[key] = findItem(catalog, key, entry.selection[key])?.id || "";
        }
        const descriptions = cleanDescriptions(entry.descriptions);
        presets.push({ id: "import-" + Date.now() + "-" + presets.length,
          name, selection, ...(Object.values(descriptions).some(Boolean)
            ? {descriptions, source:"vision"} : {}) });
        added++;
      }
      storePresets(presets);
      render();
      window.alert(added + " preset(s) imported.");
    } catch (err) {
      window.alert("Import failed: " + (err.message || err));
    }
  }
  function listPresetGroup(title, items, system = false) {
    sidebar.append(el("strong", "sft-cine-title", title));
    const list = el("div", "sft-cine-preset-list");
    for (const item of items) {
      const button = makeButton(item.name, () => {
        loadSelection(node, catalog, item.selection, system ? null : item.descriptions);
        active = system ? "" : item.id;
        render();
      });
      button.setAttribute("aria-pressed", String(!system && active === item.id));
      list.append(button);
    }
    sidebar.append(list);
  }
  function renderSidebar() {
    sidebar.replaceChildren();
    sidebar.append(el("strong", "sft-cine-title", "Current mix"));
    for (const key of KEYS) {
      const label = el("label", "", LABELS[key]);
      const select = el("select");
      select.setAttribute("aria-label", LABELS[key]);
      for (const item of [{ id: "", name: "None" }, ...catalog.categories[key]]) {
        const opt = el("option", "", item.name);
        opt.value = item.name;
        select.append(opt);
      }
      select.value = readWidget(node, key)?.value || "None";
      select.addEventListener("change", () => {
        changeComponent(node, catalog, key, select.value);
        render();
      });
      label.append(select); sidebar.append(label);
    }
    const check = el("label", "sft-cine-checkbox");
    const input = el("input");
    input.type = "checkbox";
    input.checked = !!readWidget(node, "enabled")?.value;
    input.addEventListener("change", () => writeWidget(node, "enabled", input.checked));
    check.append(input, document.createTextNode(" Apply to image prompt"));
    sidebar.append(check);
    sidebar.append(makeButton("Reset selection", () => {
      loadSelection(node, catalog, {});
      writeWidget(node, "enabled", false);
      active = ""; render();
    }));
    listPresetGroup("System presets", catalog.system_presets, true);
    listPresetGroup("My presets (" + presets.length + ")", presets);
    const actions = el("div", "sft-cine-actions");
    const entry = currentPreset();
    actions.append(makeButton("Save Preset", () => saveNew()));
    actions.append(makeButton("Update", update));
    actions.append(makeButton("Duplicate", () => saveNew(entry ? entry.name + " Copy" : "Cinematic Copy")));
    actions.append(makeButton("Rename", rename));
    actions.append(makeButton("Delete", remove));
    actions.append(makeButton("Export", () => download("cinematic-presets.json", { version: 1, presets })));
    const fileInput = el("input");
    fileInput.type = "file"; fileInput.accept = "application/json,.json";
    fileInput.hidden = true;
    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0]; if (file) void importFile(file);
    });
    actions.append(makeButton("Import", () => fileInput.click()), fileInput);
    for (const button of actions.querySelectorAll("button")) {
      if (["Update", "Rename", "Delete"].includes(button.textContent)) button.disabled = !entry;
    }
    sidebar.append(actions);
  }
  function render() { renderTabs(); renderGallery(); renderSidebar(); }
  render();
}

app.registerExtension({
  name: "sft.cinematicLookLibrary",
  nodeCreated(node) {
    if (node.comfyClass === VISION_NODE_NAME) {
      if (node.__cinematicVisionAdded) return;
      node.__cinematicVisionAdded = true;
      const original = node.onExecuted;
      node.onExecuted = function(message) {
        original?.apply(this, arguments);
        const raw = message?.cinematic_preset?.[0];
        if (typeof raw === "string") this.__latestCinematicVision = raw;
      };
      node.addWidget("button", "Save Vision Preset", null, async () => {
        try {
          const raw = node.__latestCinematicVision;
          if (!raw) { window.alert("Run the Vision Analyzer first."); return; }
          const catalog = await getCatalog();
          const result = JSON.parse(raw);
          const selection = {};
          for (const key of KEYS) {
            selection[key] = findItem(catalog, key, result.selection?.[key])?.id || "";
          }
          const descriptions = cleanDescriptions(result.descriptions);
          if (!Object.values(descriptions).some(Boolean)) throw new Error("No usable style properties.");
          const name = window.prompt("Preset name", result.name || "Vision Look")?.trim();
          if (!name) return;
          const presets = getPresets();
          if (presets.some(p => p.name.toLowerCase() === name.toLowerCase())) {
            window.alert("Preset name already used."); return;
          }
          presets.push({id:"vision-" + Date.now() + "-"
            + Math.random().toString(36).slice(2,7),
            name, selection, descriptions, source:"vision"});
          storePresets(presets);
          window.alert("Vision preset saved. Open Cinematic Look Mixer to load it.");
        } catch (error) {
          window.alert("Cannot save vision preset: " + (error.message || error));
        }
      }, {serialize:false});
      return;
    }
    if (node.comfyClass !== NODE_NAME || node.__cinematicLibraryAdded) return;
    node.__cinematicLibraryAdded = true;
    node.addWidget("button", "Open Cinematic Library", null, () => {
      void showLibrary(node).catch((error) => window.alert(
        "Cinematic library unavailable: " + (error.message || error)
      ));
    }, { serialize: false });
  },
});
