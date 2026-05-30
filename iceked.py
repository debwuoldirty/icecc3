#!/usr/bin/env python3
"""
IceWM Keys Editor (iceked)
Basado en iceked.cpp de Vadim A. Khohlov
"""

import sys
import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

# Rutas
ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"
DEFAULT_KEYS_FILE = ICEWM_PRIV_DIR / "keys"

def parse_keys_file(filepath):
    entries = []
    if not filepath.exists():
        return entries
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if not line.startswith("key "):
                continue
            rest = line[4:].strip()
            if '"' not in rest:
                continue
            first = rest.index('"')
            second = rest.index('"', first+1)
            combo = rest[first+1:second]
            command = rest[second+1:].strip()
            entries.append({"key": combo, "command": command})
    return entries

def save_keys_file(filepath, entries):
    with open(filepath, 'w') as f:
        for e in entries:
            f.write(f'key "{e["key"]}" {e["command"]}\n')
    try:
        subprocess.run(["pkill", "-1", "icewm"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

class KeysEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("IceWM Keys Editor")
        self.set_default_size(600, 400)

        self.current_file = DEFAULT_KEYS_FILE
        self.entries = parse_keys_file(self.current_file)

        # Contenedor principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        self.set_child(vbox)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(toolbar)
        btn_open = Gtk.Button.new_with_label("Abrir")
        btn_open.connect("clicked", self.on_open)
        toolbar.append(btn_open)
        btn_save = Gtk.Button.new_with_label("Guardar")
        btn_save.connect("clicked", self.on_save)
        toolbar.append(btn_save)

        # Panel horizontal
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(250)
        vbox.append(paned)

        # Lista de teclas
        self.list_store = Gtk.ListStore(str, str)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        renderer = Gtk.CellRendererText()
        col_key = Gtk.TreeViewColumn("Tecla", renderer, text=0)
        col_cmd = Gtk.TreeViewColumn("Comando", renderer, text=1)
        self.tree_view.append_column(col_key)
        self.tree_view.append_column(col_cmd)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.tree_view)
        paned.set_start_child(scrolled)

        self.tree_view.get_selection().connect("changed", self.on_selection_changed)

        # Panel editor
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        editor_box.set_margin_top(5)
        editor_box.set_margin_bottom(5)
        editor_box.set_margin_start(5)
        editor_box.set_margin_end(5)
        paned.set_end_child(editor_box)

        # Modificadores
        mod_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        editor_box.append(mod_box)
        self.chk_ctrl = Gtk.CheckButton(label="Ctrl")
        mod_box.append(self.chk_ctrl)
        self.chk_alt = Gtk.CheckButton(label="Alt")
        mod_box.append(self.chk_alt)
        self.chk_shift = Gtk.CheckButton(label="Shift")
        mod_box.append(self.chk_shift)

        # Tecla base
        editor_box.append(Gtk.Label(label="Tecla:"))
        self.entry_key = Gtk.Entry()
        editor_box.append(self.entry_key)

        # Comando
        editor_box.append(Gtk.Label(label="Comando:"))
        cmd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        editor_box.append(cmd_box)
        self.entry_command = Gtk.Entry()
        cmd_box.append(self.entry_command)
        btn_browse = Gtk.Button.new_with_label("...")
        btn_browse.connect("clicked", self.on_browse_command)
        cmd_box.append(btn_browse)

        # Botones
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        editor_box.append(btn_box)
        btn_set = Gtk.Button.new_with_label("Establecer")
        btn_set.connect("clicked", self.on_set)
        btn_box.append(btn_set)
        btn_add = Gtk.Button.new_with_label("Añadir")
        btn_add.connect("clicked", self.on_add)
        btn_box.append(btn_add)
        btn_del = Gtk.Button.new_with_label("Eliminar")
        btn_del.connect("clicked", self.on_delete)
        btn_box.append(btn_del)

        self.populate_list()

    def populate_list(self):
        self.list_store.clear()
        for e in self.entries:
            self.list_store.append([e["key"], e["command"]])

    def on_open(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Abrir archivo de teclas")
        dialog.open(self, None, self._on_open_finish)

    def _on_open_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.current_file = Path(file.get_path())
                self.entries = parse_keys_file(self.current_file)
                self.populate_list()
        except GLib.Error:
            pass

    def on_save(self, button):
        save_keys_file(self.current_file, self.entries)
        self.entries = parse_keys_file(self.current_file)
        self.populate_list()

    def on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        combo = model[treeiter][0]
        cmd = model[treeiter][1]
        self.chk_ctrl.set_active("Ctrl+" in combo)
        self.chk_alt.set_active("Alt+" in combo)
        self.chk_shift.set_active("Shift+" in combo)
        key = combo
        for mod in ("Ctrl+", "Alt+", "Shift+"):
            key = key.replace(mod, "")
        self.entry_key.set_text(key)
        self.entry_command.set_text(cmd)

    def build_combo(self):
        parts = []
        if self.chk_ctrl.get_active():
            parts.append("Ctrl")
        if self.chk_alt.get_active():
            parts.append("Alt")
        if self.chk_shift.get_active():
            parts.append("Shift")
        key = self.entry_key.get_text().strip()
        if key:
            parts.append(key)
        return "+".join(parts)

    def on_set(self, *args):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        new_combo = self.build_combo()
        new_cmd = self.entry_command.get_text()
        model[treeiter][0] = new_combo
        model[treeiter][1] = new_cmd
        idx = model.get_path(treeiter).get_indices()[0]
        if idx < len(self.entries):
            self.entries[idx]["key"] = new_combo
            self.entries[idx]["command"] = new_cmd

    def on_add(self, *args):
        combo = self.build_combo()
        cmd = self.entry_command.get_text()
        self.entries.append({"key": combo, "command": cmd})
        self.populate_list()

    def on_delete(self, *args):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        idx = model.get_path(treeiter).get_indices()[0]
        del self.entries[idx]
        self.populate_list()

    def on_browse_command(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Seleccionar programa")
        dialog.open(self, None, self._on_browse_finish)

    def _on_browse_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.entry_command.set_text(file.get_path())
        except GLib.Error:
            pass

class KeysEditorApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.iceked")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = KeysEditorWindow(application=app)
        win.present()

if __name__ == "__main__":
    app = KeysEditorApp()
    app.run(sys.argv)
