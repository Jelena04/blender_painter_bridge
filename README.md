# Blender Painter Bridge

A Blender add-on that automates the export-and-bake workflow between Blender and Adobe Substance 3D Painter. Set up your suffixes, hit a button, and your FBX files are exported and a bake task is queued for Painter with a mesh state system to help you gauge the risk of rebaking into an existing `.spp` project.

---

## Features

- **One-click export & bake** — exports low and high poly FBX meshes based on configurable name suffixes and creates a task file for Substance Painter to pick up
- **Auto-launch Painter** — optionally launches Substance Painter automatically when starting a new project
- **Mesh states** — snapshot your mesh at any point; save, load, and remove states from within Blender
- **Rebake risk assessment** — compares your current mesh against a saved state across three categories (bounding box, materials, UV islands) and shows a risk indicator
- **Configurable thresholds** — control how sensitive the change detection is via `check_config.json`

---

## Requirements

- Blender 4.4.3+
- Adobe Substance 3D Painter (any recent version)
- Windows (the add-on uses `tasklist` to detect running processes and hardcoded Windows paths)

---

## Installation

1. Download or clone this repository.
2. Open Blender and go to **Edit > Preferences > Add-ons > Install**.
3. Select `bp_bridge_blender.py` and click **Install Add-on**.
4. Enable the add-on in the list.

Before using, you **must** update two constants at the top of `bp_bridge_blender.py`:

```python
# Path to your Substance Painter executable
PAINTER_PATH = r"C:\Program Files\Adobe\Adobe Substance 3D Painter\Adobe Substance 3D Painter.exe"

# Path to check_config.json (included in this repo)
CONFIG_PATH = r"C:\path\to\your\blender_painter_bridge\check_config.json"
```

Update `CONFIG_PATH` to wherever you cloned/saved this repo. If your Substance Painter is installed in the default location, `PAINTER_PATH` likely won't need changing.

---

## Usage

The panel lives in **View3D > Tool > Blender Painter Bridge**.

**Setup**
- Choose scope: *Selected* (only selected meshes) or *All* (every mesh in the scene)
- Set the suffixes that identify your low and high poly meshes (defaults: `_low` / `_high`)
- Set a working directory — this is where all output files will be saved

**Mesh States**
- Enter a name and click **Save** to snapshot the current mesh (exports an FBX + JSON with bbox, material, and UV island data)
- Select a state from the list and click **Load** to reimport it, or **Remove** to delete it from disk
- Click **Check Changes** to compare the current mesh against the selected state — the panel will show one of three results:

| Indicator | Meaning |
|---|---|
| 🟢 Safe to reload | Unlikely to affect Painter layer assignments |
| 🟡 Reload with caution | Rebaking may break layer assignments |
| 🔴 Risky to reload | Consider baking into a new `.spp` file |

- Click **Config** to reload `check_config.json` if you've changed the thresholds

**Baking**
- Toggle which mesh maps to bake (Normal, AO, Curvature)
- Choose *Use Open* to bake into your already-open Painter project, or *Use New* to have Painter launched automatically with a fresh project
- Click **Export and Bake**

---

## Configuration

`check_config.json` controls the thresholds used by the change detection system:

```json
{
  "bbox_threshold": 10,
  "uv_islands_threshold": 2
}
```

- `bbox_threshold` — maximum allowed percentage change in any bounding box dimension before it's flagged
- `uv_islands_threshold` — maximum number of UV islands the count is allowed to differ by before it's flagged

Edit this file and click **Config** in the panel to reload it without restarting Blender.

---

## Output Structure

All files are written inside a `bp_bridge_output/` folder within your chosen working directory:

```
bp_bridge_output/
├── meshes/          # Exported low and high poly FBX files
├── mesh_states/     # Saved mesh state FBX and JSON snapshots  
└── tasks/           # Task JSON files for Substance Painter to process
```

---

*By Jelena Rombouts — [ArtStation](https://www.artstation.com/jelenarombouts2)*
