#!/usr/bin/env python3
"""
IceWM Menu/Toolbar Editor (icemc)
Uso: ./icemc.py [archivo_menu_o_toolbar]
"""

import sys
import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

# ------------------------------------------------------------
# Rutas
# ------------------------------------------------------------
ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"

DEFAULT_MENU_FILE = ICEWM_PRIV_DIR / "menu"

ITEM_TYPES = ["prog", "menu", "menufile", "menuprog", "restart",
              "separator", "include", "menuprogreload", "runonce"]

# ------------------------------------------------------------
# Parser y escritor del archivo menu/toolbar
# ------------------------------------------------------------
def parse_menu_file(filepath):
    def parse_stream(lines):
        items = []
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            idx += 1
            if not line or line.startswith('#'):
                continue
            tokens = []
            current = ""
            in_quotes = False
            escaped = False
            for ch in line:
                if escaped:
                    current += ch
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == '"':
                    in_quotes = not in_quotes
                elif ch in ' \t' and not in_quotes:
                    if current:
                        tokens.append(current)
                        current = ""
                else:
                    current += ch
            if current:
                tokens.append(current)

            if not tokens:
                continue

            kw = tokens[0]
            if kw == "}":
                break
            elif kw == "separator":
                items.append({"type": "separator"})
            elif kw == "menu":
                name = tokens[1] if len(tokens) > 1 else "Submenu"
                icon = tokens[2] if len(tokens) > 2 and tokens[2] != "{" else ""
                if "{" in tokens:
                    sub_items, idx = parse_stream(lines[idx:])
                    idx += idx
                else:
                    sub_items = []
                items.append({"type": "menu", "name": name, "icon": icon, "children": sub_items})
            elif kw in ("include", "menufile"):
                filename = tokens[1] if len(tokens) > 1 else ""
                items.append({"type": kw, "name": filename})
            elif kw in ("prog", "menuprog", "menuprogreload", "restart", "runonce"):
                name = tokens[1] if len(tokens) > 1 else "Programa"
                icon = tokens[2] if len(tokens) > 2 else ""
                command = " ".join(tokens[3:]) if len(tokens) > 3 else ""
                is_icerrun = False
                timeout = ""
                if kw == "menuprogreload":
                    if len(tokens) > 4:
                        timeout = tokens[3]
                        command = " ".join(tokens[4:])
                elif command.startswith("icerrun.py"):
                    is_icerrun = True
                    command = command[len("icerrun.py"):].strip()
                items.append({
                    "type": kw, "name": name, "icon": icon,
                    "command": command, "is_icerrun": is_icerrun,
                    "timeout": timeout
                })
            else:
                print(f"Token desconocido: {kw}")
        return items, idx

    with open(filepath, 'r') as f:
        all_lines = f.readlines()
    menu_tree, _ = parse_stream(all_lines)
    return menu_tree

def menu_to_lines(items, indent=0):
    lines = []
    prefix = "\t" * indent
    for item in items:
        t = item["type"]
        if t == "separator":
            lines.append(f"{prefix}separator")
        elif t == "menu":
            name = item.get("name", "Submenu")
            icon = item.get("icon", "")
            icon_str = f'"{icon}"' if icon else ""
            lines.append(f'{prefix}menu "{name}" {icon_str} {{')
            lines.extend(menu_to_lines(item.get("children", []), indent+1))
            lines.append(f'{prefix}}}')
        elif t in ("include", "menufile"):
            lines.append(f'{prefix}{t} "{item["name"]}"')
        elif t in ("prog", "menuprog", "menuprogreload", "restart", "runonce"):
            cmd = item.get("command", "")
            if item.get("is_icerrun"):
                cmd = "icerrun.py " + cmd
            if t == "menuprogreload" and item.get("timeout"):
                lines.append(f'{prefix}{t} "{item["name"]}" "{item["icon"]}" {item["timeout"]} {cmd}')
            else:
                lines.append(f'{prefix}{t} "{item["name"]}" "{item["icon"]}" {cmd}')
    return lines

def save_menu_file(filepath, items):
    with open(filepath, 'w') as f:
        for line in menu_to_lines(items):
            f.write(line + "\n")
    try:
        subprocess.run(["pkill", "-1", "icewm"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class MenuEditorWindow(Gtk.Window):
    def __init__(self, filepath=None):
        super().__init__(title="IceWM Menu Editor")
        self.current_file = Path(filepath) if filepath else DEFAULT_MENU_FILE
        if self.current_file.name == "toolbar":
            self.set_title("IceWM Toolbar Editor")
        else:
            self.set_title("IceWM Menu Editor")
        self.set_default_size(700, 500)

        self.menu_items = []
        if self.current_file.exists():
            self.menu_items = parse_menu_file(self.current_file)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5); vbox.set_margin_bottom(5)
        vbox.set_margin_start(5); vbox.set_margin_end(5)
        self.set_child(vbox)

        # Toolbar principal
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(toolbar)

        btn_open = Gtk.Button.new_with_label("Abrir")
        btn_open.connect("clicked", self.on_open)
        toolbar.append(btn_open)

        btn_save = Gtk.Button.new_with_label("Guardar")
        btn_save.connect("clicked", self.on_save)
        toolbar.append(btn_save)

        # Nuevos botones para reordenar
        btn_up = Gtk.Button.new_with_label("Subir ↑")
        btn_up.connect("clicked", self.on_move_up)
        toolbar.append(btn_up)

        btn_down = Gtk.Button.new_with_label("Bajar ↓")
        btn_down.connect("clicked", self.on_move_down)
        toolbar.append(btn_down)

        btn_add = Gtk.Button.new_with_label("Añadir")
        btn_add.connect("clicked", self.on_add_item)
        toolbar.append(btn_add)

        btn_del = Gtk.Button.new_with_label("Eliminar")
        btn_del.connect("clicked", self.on_delete_item)
        toolbar.append(btn_del)

        hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        hpaned.set_position(250)
        vbox.append(hpaned)

        self.tree_store = Gtk.TreeStore(str, object)
        self.tree_view = Gtk.TreeView(model=self.tree_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Elemento", renderer, text=0)
        self.tree_view.append_column(column)

        scroll_tree = Gtk.ScrolledWindow()
        scroll_tree.set_child(self.tree_view)
        hpaned.set_start_child(scroll_tree)

        self.tree_view.get_selection().connect("changed", self.on_item_selected)

        # Panel de propiedades
        prop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        prop_box.set_margin_top(5); prop_box.set_margin_bottom(5)
        prop_box.set_margin_start(5); prop_box.set_margin_end(5)
        hpaned.set_end_child(prop_box)

        prop_box.append(Gtk.Label(label="Tipo:"))
        self.combo_type = Gtk.ComboBoxText()
        for t in ITEM_TYPES:
            self.combo_type.append_text(t)
        self.combo_type.set_active(0)
        self.combo_type.connect("changed", self.on_type_changed)
        prop_box.append(self.combo_type)

        prop_box.append(Gtk.Label(label="Nombre:"))
        self.entry_name = Gtk.Entry()
        prop_box.append(self.entry_name)

        prop_box.append(Gtk.Label(label="Icono:"))
        box_icon = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        prop_box.append(box_icon)
        self.entry_icon = Gtk.Entry()
        box_icon.append(self.entry_icon)
        btn_browse_icon = Gtk.Button.new_with_label("...")
        btn_browse_icon.connect("clicked", self.on_browse_icon)
        box_icon.append(btn_browse_icon)

        prop_box.append(Gtk.Label(label="Comando:"))
        box_cmd = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        prop_box.append(box_cmd)
        self.entry_command = Gtk.Entry()
        box_cmd.append(self.entry_command)
        btn_browse_cmd = Gtk.Button.new_with_label("...")
        btn_browse_cmd.connect("clicked", self.on_browse_command)
        box_cmd.append(btn_browse_cmd)

        self.check_icerrun = Gtk.CheckButton(label="Ejecutar con icerrun")
        prop_box.append(self.check_icerrun)

        prop_box.append(Gtk.Label(label="Timeout (ms):"))
        self.entry_timeout = Gtk.Entry()
        prop_box.append(self.entry_timeout)

        btn_update = Gtk.Button.new_with_label("Actualizar elemento")
        btn_update.connect("clicked", self.on_update_item)
        prop_box.append(btn_update)

        self.present()
        self.populate_tree()

    # ---- Funciones de árbol ----
    def populate_tree(self):
        self.tree_store.clear()
        for item in self.menu_items:
            t = item["type"]
            if t == "separator":
                text = "--- separador ---"
            elif t in ("menu", "menufile", "include"):
                text = f'[{t}] {item.get("name","")}'
            else:
                text = f'[{t}] {item.get("name","")}'
                if t not in ("menu", "menufile", "include"):
                    text += f' ({item.get("command","")})'
            self.tree_store.append(None, [text, item])

    def get_selected_index(self):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return -1
        return model.get_path(treeiter).get_indices()[0]

    def select_row(self, index):
        if 0 <= index < len(self.menu_items):
            path = Gtk.TreePath.new_from_indices([index])
            self.tree_view.get_selection().select_path(path)
            self.tree_view.scroll_to_cell(path, None, True, 0.5, 0.0)

    # ---- Movimiento de elementos ----
    def on_move_up(self, button):
        idx = self.get_selected_index()
        if idx > 0:
            self.menu_items.insert(idx - 1, self.menu_items.pop(idx))
            self.populate_tree()
            self.select_row(idx - 1)

    def on_move_down(self, button):
        idx = self.get_selected_index()
        if idx != -1 and idx < len(self.menu_items) - 1:
            self.menu_items.insert(idx + 1, self.menu_items.pop(idx))
            self.populate_tree()
            self.select_row(idx + 1)

    # ---- Resto de funciones (abrir, guardar, etc.) ----
    def on_open(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir archivo de menú/toolbar")
        dialog.open(self, None, lambda d, r: self._on_open_finish(d, r))

    def _on_open_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.current_file = Path(file.get_path())
                self.menu_items = parse_menu_file(self.current_file)
                self.populate_tree()
                if self.current_file.name == "toolbar":
                    self.set_title("IceWM Toolbar Editor")
                else:
                    self.set_title("IceWM Menu Editor")
        except GLib.Error:
            pass

    def on_save(self, button):
        save_menu_file(self.current_file, self.menu_items)

    def on_add_item(self, button):
        self.menu_items.append({"type": "prog", "name": "Nuevo programa", "icon": "", "command": "", "is_icerrun": False, "timeout": ""})
        self.populate_tree()

    def on_delete_item(self, button):
        idx = self.get_selected_index()
        if idx != -1:
            del self.menu_items[idx]
            self.populate_tree()

    def on_item_selected(self, selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        item = model[treeiter][1]
        self.combo_type.set_active(ITEM_TYPES.index(item["type"]) if item["type"] in ITEM_TYPES else 0)
        self.entry_name.set_text(item.get("name", ""))
        self.entry_icon.set_text(item.get("icon", ""))
        self.entry_command.set_text(item.get("command", ""))
        self.check_icerrun.set_active(item.get("is_icerrun", False))
        self.entry_timeout.set_text(item.get("timeout", ""))

    def on_type_changed(self, combo):
        active = combo.get_active_text()
        has_name = active not in ("separator",)
        has_icon = active not in ("separator",)
        has_cmd = active not in ("menu", "separator", "include", "menufile")
        is_prog = active in ("prog", "menuprog", "menuprogreload", "restart", "runonce")

        self.entry_name.set_sensitive(has_name)
        self.entry_icon.set_sensitive(has_icon)
        self.entry_command.set_sensitive(has_cmd)
        self.check_icerrun.set_sensitive(is_prog)
        self.entry_timeout.set_sensitive(active == "menuprogreload")

    def on_update_item(self, button):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        item = model[treeiter][1]
        item["type"] = self.combo_type.get_active_text()
        item["name"] = self.entry_name.get_text()
        item["icon"] = self.entry_icon.get_text()
        item["command"] = self.entry_command.get_text()
        item["is_icerrun"] = self.check_icerrun.get_active()
        item["timeout"] = self.entry_timeout.get_text()
        self.populate_tree()

    def on_browse_icon(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar icono")
        dialog.open(self, None, lambda d, r: self._file_selected(d, r, self.entry_icon))

    def on_browse_command(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar programa")
        dialog.open(self, None, lambda d, r: self._file_selected(d, r, self.entry_command))

    def _file_selected(self, dialog, result, entry):
        try:
            file = dialog.open_finish(result)
            if file:
                entry.set_text(file.get_path())
        except GLib.Error:
            pass

if __name__ == "__main__":
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    win = MenuEditorWindow(filepath=file_arg)
    loop = GLib.MainLoop()
    win.connect("destroy", lambda *a: loop.quit())
    loop.run()
