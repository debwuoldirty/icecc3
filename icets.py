#!/usr/bin/env python3
"""
IceWM Theme Switcher (icets)
Basado en icets.cpp de Vadim A. Khohlov
"""

import sys
import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

# ------------------------------------------------------------
# Directorios de temas
# ------------------------------------------------------------
HOME = Path.home()
ICEWM_PRIV_DIR = HOME / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = HOME / ".config" / "icewm"

GLOBAL_THEMES_DIR = Path("/usr/share/icewm/themes")
LOCAL_THEMES_DIR = ICEWM_PRIV_DIR / "themes"
THEME_CONFIG_FILE = ICEWM_PRIV_DIR / "theme"

# ------------------------------------------------------------
# Funciones auxiliares
# ------------------------------------------------------------
def get_subthemes(theme_dir: Path):
    if not theme_dir.is_dir():
        return []
    return sorted([f.stem for f in theme_dir.iterdir()
                   if f.suffix == ".theme" and f.stem != "default"])

def find_preview_image(theme_dir: Path, subtheme_name=None):
    if subtheme_name:
        path = theme_dir / f"{subtheme_name}.jpg"
        if path.exists():
            return path
        return None
    for name in ("default.jpg", "preview.jpg"):
        path = theme_dir / name
        if path.exists():
            return path
    return None

def read_theme_info(theme_dir: Path, subtheme_name=None):
    theme_file = theme_dir / (f"{subtheme_name}.theme" if subtheme_name else "default.theme")
    author = "Desconocido"
    description = ""
    if theme_file.exists():
        try:
            with open(theme_file, 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("ThemeAuthor"):
                        author = stripped.split("=", 1)[1].strip().strip('"')
                    elif stripped.startswith("ThemeDescription"):
                        description = stripped.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return author, description

def apply_theme(theme_item):
    """
    Escribe la línea Theme en ~/.icewm/theme y preferences,
    luego reinicia IceWM con killall -HUP.
    """
    is_global, theme_name, sub = theme_item
    theme_rel = f"{theme_name}/{sub}.theme" if sub else f"{theme_name}/default.theme"

    # Escribir en ambos archivos
    for config_file in (THEME_CONFIG_FILE, ICEWM_PRIV_DIR / "preferences"):
        ICEWM_PRIV_DIR.mkdir(parents=True, exist_ok=True)
        lines = []
        if config_file.exists():
            with open(config_file, 'r') as f:
                lines = f.readlines()
        with open(config_file, 'w') as f:
            found = False
            for line in lines:
                if line.strip().startswith("Theme"):
                    f.write(f'Theme = "{theme_rel}"\n')
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f'\nTheme = "{theme_rel}"\n')

    print(f"[DEBUG] Tema aplicado: {theme_rel}")

    # Reinicio fiable: killall -HUP icewm (si no existe, pkill -1)
    try:
        subprocess.run(["killall", "-HUP", "icewm"], stderr=subprocess.DEVNULL)
        print("[DEBUG] Reinicio con killall -HUP icewm")
    except FileNotFoundError:
        try:
            subprocess.run(["pkill", "-1", "icewm"], stderr=subprocess.DEVNULL)
            print("[DEBUG] Reinicio con pkill -1 icewm")
        except FileNotFoundError:
            print("[ERROR] No se pudo reiniciar IceWM")

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class ThemeSwitcherWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("IceWM Theme Switcher")
        self.set_default_size(600, 450)

        self.themes_store = self.load_themes()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(10); hbox.set_margin_bottom(10)
        hbox.set_margin_start(10); hbox.set_margin_end(10)
        self.set_child(hbox)

        # Árbol de temas
        tree_frame = Gtk.Frame(label="Temas")
        hbox.append(tree_frame)

        self.tree_model = Gtk.TreeStore(str, str, str)
        self.tree_view = Gtk.TreeView(model=self.tree_model)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Tema", renderer, text=1)
        self.tree_view.append_column(column)
        self.tree_view.set_headers_visible(False)

        scroll_tree = Gtk.ScrolledWindow()
        scroll_tree.set_child(self.tree_view)
        scroll_tree.set_min_content_width(180)
        tree_frame.set_child(scroll_tree)

        # Panel derecho
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right_box.set_hexpand(True)
        hbox.append(right_box)

        self.preview = Gtk.Picture()
        self.preview.set_size_request(320, 200)
        self.preview.set_hexpand(True)
        right_box.append(self.preview)

        self.author_label = Gtk.Label(label="Autor: ")
        self.author_label.set_halign(Gtk.Align.START)
        right_box.append(self.author_label)

        self.desc_label = Gtk.Label(label="Descripción: ")
        self.desc_label.set_halign(Gtk.Align.START)
        self.desc_label.set_wrap(True)
        right_box.append(self.desc_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        right_box.append(btn_box)

        btn_apply = Gtk.Button(label="Aplicar")
        btn_apply.set_hexpand(True)
        btn_apply.connect("clicked", self.on_apply)
        btn_box.append(btn_apply)

        btn_ok = Gtk.Button(label="Ok")
        btn_ok.set_hexpand(True)
        btn_ok.connect("clicked", self.on_ok)
        btn_box.append(btn_ok)

        btn_close = Gtk.Button(label="Cerrar")
        btn_close.set_hexpand(True)
        btn_close.connect("clicked", lambda *args: self.close())
        btn_box.append(btn_close)

        self.populate_tree()
        self.tree_view.get_selection().connect("changed", self.on_selection_changed)
        self.tree_view.expand_all()
        first = self.tree_model.get_iter_first()
        if first:
            self.tree_view.get_selection().select_iter(first)

    def load_themes(self):
        themes = {"global": {}, "local": {}}
        if GLOBAL_THEMES_DIR.is_dir():
            for d in GLOBAL_THEMES_DIR.iterdir():
                if d.is_dir():
                    subthemes = get_subthemes(d)
                    themes["global"][d.name] = subthemes
        if LOCAL_THEMES_DIR.is_dir():
            for d in LOCAL_THEMES_DIR.iterdir():
                if d.is_dir():
                    subthemes = get_subthemes(d)
                    themes["local"][d.name] = subthemes
        return themes

    def populate_tree(self):
        self.tree_model.clear()
        global_iter = self.tree_model.append(None, ["", "Global", "root"])
        for theme_name, subthemes in self.themes_store["global"].items():
            parent = self.tree_model.append(global_iter, ["", theme_name, "global"])
            for sub in subthemes:
                self.tree_model.append(parent, ["", sub, "sub"])
        if self.themes_store["local"]:
            local_iter = self.tree_model.append(None, ["", "Local", "root"])
            for theme_name, subthemes in self.themes_store["local"].items():
                parent = self.tree_model.append(local_iter, ["", theme_name, "local"])
                for sub in subthemes:
                    self.tree_model.append(parent, ["", sub, "sub"])

    def on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return
        tipo = model[treeiter][2]
        name = model[treeiter][1]
        if tipo == "root":
            self.preview.set_filename(None)
            self.author_label.set_text("Autor: ")
            self.desc_label.set_text("")
            return

        if tipo == "global":
            theme_dir = GLOBAL_THEMES_DIR / name
            sub = None
        elif tipo == "local":
            theme_dir = LOCAL_THEMES_DIR / name
            sub = None
        elif tipo == "sub":
            parent_iter = model.iter_parent(treeiter)
            parent_name = model[parent_iter][1]
            parent_tipo = model[parent_iter][2]
            if parent_tipo == "global":
                theme_dir = GLOBAL_THEMES_DIR / parent_name
            else:
                theme_dir = LOCAL_THEMES_DIR / parent_name
            sub = name
        else:
            return

        preview_path = find_preview_image(theme_dir, sub)
        self.preview.set_filename(str(preview_path) if preview_path else None)

        author, desc = read_theme_info(theme_dir, sub)
        self.author_label.set_text(f"Autor: {author}")
        self.desc_label.set_text(f"Descripción: {desc}")

    def get_selected_theme(self):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return None
        tipo = model[treeiter][2]
        name = model[treeiter][1]
        if tipo == "root":
            return None
        if tipo in ("global", "local"):
            return (tipo == "global", name, None)
        parent_iter = model.iter_parent(treeiter)
        parent_name = model[parent_iter][1]
        parent_tipo = model[parent_iter][2]
        return (parent_tipo == "global", parent_name, name)

    def on_apply(self, button=None):   # <-- Aquí el cambio: button es opcional
        sel = self.get_selected_theme()
        if sel:
            apply_theme(sel)

    def on_ok(self, button=None):      # <-- También aquí, para consistencia
        self.on_apply()                 # Ahora ya no falta el argumento
        self.close()

# ------------------------------------------------------------
# App
# ------------------------------------------------------------
class ThemeSwitcherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.icets")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = ThemeSwitcherWindow(application=app)
        win.present()

if __name__ == "__main__":
    app = ThemeSwitcherApp()
    app.run(sys.argv)