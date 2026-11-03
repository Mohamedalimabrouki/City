"""Static checks of the Godot 4 starter (prompt 72): Godot is not installed where the tests run."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GODOT = ROOT / "engine" / "godot"
SOURCES = [*GODOT.rglob("*.gd"), *GODOT.rglob("*.tscn"), GODOT / "project.godot"]
GODOT_BUILTIN = {"KHR_texture_transform", "KHR_materials_emissive_strength", "KHR_materials_unlit",
                 "KHR_lights_punctual", "KHR_materials_pbrSpecularGlossiness"}   # gltf_document.cpp, 4.3


def test_godot_project_files_exist_and_link():
    assert (GODOT / "project.godot").is_file() and (GODOT / "README.md").is_file()
    for path in SOURCES:
        text = path.read_text(encoding="utf-8")
        assert chr(0x2014) not in text, path
        for ref in re.findall(r'res://([\w/.-]+\.(?:gd|tscn))', text):
            assert (GODOT / ref).is_file(), f"{path.name} links missing res://{ref}"


def test_gdscript_indents_with_tabs_only():
    # GDScript refuses a file that mixes tabs and spaces in its indentation
    for path in GODOT.rglob("*.gd"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.match(r"^ +\S", line) and not re.match(r"^\t* +\t", line), f"{path.name}:{n}"


def test_extension_covers_every_glb_extension_the_writer_uses():
    supported = set(GODOT_BUILTIN)
    text = (GODOT / "scripts" / "citygen_gltf.gd").read_text(encoding="utf-8")
    for name in re.findall(r'const \w+ := "((?:KHR|EXT)_\w+)"', text):
        supported.add(name)
    writer = (ROOT / "citygen" / "mesh" / "gltf.py").read_text(encoding="utf-8")
    used = set(re.findall(r'"((?:KHR|EXT)_[a-z_]+)"', writer))
    assert {"KHR_mesh_quantization", "EXT_mesh_gpu_instancing", "KHR_texture_transform"} <= used
    assert used <= supported, used - supported
