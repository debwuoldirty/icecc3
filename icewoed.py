#!/usr/bin/env python3
"""
IceWM Winoptions Editor (icewoed)
Basado en icewoed.cpp de Vadim A. Khohlov
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

DEFAULT_WINOPTIONS = ICEWM_PRIV_DIR / "winoptions"

# Opciones de estilo
OPTION_NAMES = [
    "allWorkspaces",
    "ignoreWinList",
    "ignoreTaskBar",
    "ignoreQuickSwitch",
    "fullKeys",
    "fMove", "fResize", "fClose", "fMinimize", "fMaximize", "fHide", "fRollup",
    "dTitleBar", "dSysMenu", "dBorder", "dResize", "dClose", "dMinimize", "dMaximize",
    "noFocusOnAppRaise", "ignoreNoFocusHint", "doNotCover",
    "startMaximized", "startMaximizedVert", "startMaximizedHorz",
    "startMinimized", "startMinimizedVert", "startMinimizedHorz",
    "doNotFocus"
]

LAYER_NAMES = ["DeskTop", "Below", "Normal", "OnTop", "Dock", "AboveDock", "Menu"]
TRAY_OPTIONS = ["Ignore", "Minimized", "Exclusive"]

# ------------------------------------------------------------
# Parser del archivo winoptions
# ------------------------------------------------------------
def parse_winoptions(filepath):
    wins = {}
    if not filepath.exists():
        return wins
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                head, opt_val = line.split(":", 1)
            except ValueError:
                continue
            head = head.strip()
            opt_val = opt_val.strip()
            parts = head.split(".")
            if len(parts) < 1:
                continue
            opt = parts[-1]
            class_name = parts[0] if len(parts) > 0 else ""
            name = parts[1] if len(parts) > 1 else ""
            role = parts[2] if len(parts) > 2 else ""
            if len(parts) > 3:
                name = ".".join(parts[1:-1])
                role = ""
            win_key = (class_name, name, role)
            if win_key not in wins:
                wins[win_key] = {"class": class_name, "name": name, "role": role}
                wins[win_key]["icon"] = ""
                wins[win_key]["workspace"] = -1
                wins[win_key]["layer"] = 2
                wins[win_key]["geometry"] = ""
                wins[win_key]["tray"] = 0
                wins[win_key]["options"] = {}
                for i, oname in enumerate(OPTION_NAMES):
                    wins[win_key]["options"][oname] = (5 <= i <= 18)
            if opt == "icon":
                wins[win_key]["icon"] = opt_val
            elif opt == "workspace":
                try:
                    wins[win_key]["workspace"] = int(opt_val)
                except ValueError:
                    pass
            elif opt == "layer":
                if opt_val in LAYER_NAMES:
                    wins[win_key]["layer"] = LAYER_NAMES.index(opt_val)
            elif opt == "geometry":
                wins[win_key]["geometry"] = opt_val
            elif opt == "tray":
                if opt_val in TRAY_OPTIONS:
                    wins[win_key]["tray"] = TRAY_OPTIONS.index(opt_val)
            elif opt in OPTION_NAMES:
                wins[win_key]["options"][opt] = (opt_val == "1")
    return wins

def save_winoptions(filepath, wins):
    with open(filepath, 'w') as f:
        for win_key, data in wins.items():
            wclass = data["class"]
            wname = data["name"]
            wrole = data["role"]
            base = wclass
            if wname:
                base += f".{wname}"
            if wrole:
                base += f".{wrole}"
            if data["icon"]:
                f.write(f'{base}.icon: {data["icon"]}\n')
            if data["workspace"] != -1:
                f.write(f'{base}.workspace: {data["workspace"]}\n')
            if data["layer"] != 2:
                f.write(f'{base}.layer: {LAYER_NAMES[data["layer"]]}\n')
            if data["geometry"]:
                f.write(f'{base}.geometry: {data["geometry"]}\n')
            if data["tray"] != 0:
                f.write(f'{base}.tray: {TRAY_OPTIONS[data["tray"]]}\n')
            for oname in OPTION_NAMES:
                val = data["options"].get(oname, False)
                default = (5 <= OPTION_NAMES.index(oname) <= 18)
                if val != default:
                    f.write(f'{base}.{oname}: {1 if val else 0}\n')
            f.write("\n")
    try:
        subprocess.run(["pkill", "-1", "icewm"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class WinoptionsEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="IceWM Winoptions Editor")
        self.set_default_size(700, 500)

        self.current_file = DEFAULT_WINOPTIONS
        self.win_data = parse_winoptions(self.current_file)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5); vbox.set_margin_bottom(5)
        vbox.set_margin_start(5); vbox.set_margin_end(5)
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
        btn_add = Gtk.Button.new_with_label("Añadir Ventana")
        btn_add.connect("clicked", self.on_add_window)
        toolbar.append(btn_add)
        btn_del = Gtk.Button.new_with_label("Eliminar")
        btn_del.connect("clicked", self.on_delete_window)
        toolbar.append(btn_del)

        # Panel horizontal
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(250)
        vbox.append(paned)

        # Lista de ventanas
        self.list_store = Gtk.ListStore(str, str, str)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        renderer = Gtk.CellRendererText()
        col_class = Gtk.TreeViewColumn("Clase", renderer, text=0)
        col_name = Gtk.TreeViewColumn("Nombre", renderer, text=1)
        col_role = Gtk.TreeViewColumn("Rol", renderer, text=2)
        self.tree_view.append_column(col_class)
        self.tree_view.append_column(col_name)
        self.tree_view.append_column(col_role)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.tree_view)
        paned.set_start_child(scrolled)

        self.tree_view.get_selection().connect("changed", self.on_selection_changed)

        # Panel de edición
        edit_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        edit_box.set_margin_top(5); edit_box.set_margin_bottom(5)
        edit_box.set_margin_start(5); edit_box.set_margin_end(5)
        paned.set_end_child(edit_box)

        # Datos básicos
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        edit_box.append(grid)

        grid.attach(Gtk.Label(label="Clase:"), 0, 0, 1, 1)
        self.entry_class = Gtk.Entry()
        grid.attach(self.entry_class, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Nombre:"), 0, 1, 1, 1)
        self.entry_name = Gtk.Entry()
        grid.attach(self.entry_name, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Rol:"), 0, 2, 1, 1)
        self.entry_role = Gtk.Entry()
        grid.attach(self.entry_role, 1, 2, 1, 1)

        # Icono
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        edit_box.append(hbox)
        hbox.append(Gtk.Label(label="Icono:"))
        self.entry_icon = Gtk.Entry()
        hbox.append(self.entry_icon)
        btn_icon = Gtk.Button.new_with_label("...")
        btn_icon.connect("clicked", self.on_browse_icon)
        hbox.append(btn_icon)

        # Workspace
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        edit_box.append(hbox)
        hbox.append(Gtk.Label(label="Workspace (-1 = todos):"))
        self.spin_workspace = Gtk.SpinButton.new_with_range(-1, 10, 1)
        hbox.append(self.spin_workspace)

        # Layer
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        edit_box.append(hbox)
        hbox.append(Gtk.Label(label="Capa:"))
        self.combo_layer = Gtk.ComboBoxText()
        for name in LAYER_NAMES:
            self.combo_layer.append_text(name)
        hbox.append(self.combo_layer)

        # Geometry
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        edit_box.append(hbox)
        hbox.append(Gtk.Label(label="Geometría:"))
        self.entry_geometry = Gtk.Entry()
        hbox.append(self.entry_geometry)

        # Tray
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        edit_box.append(hbox)
        hbox.append(Gtk.Label(label="Bandeja:"))
        self.combo_tray = Gtk.ComboBoxText()
        for name in TRAY_OPTIONS:
            self.combo_tray.append_text(name)
        hbox.append(self.combo_tray)

        # Opciones booleanas
        lbl_opts = Gtk.Label(label="Opciones de ventana:")
        edit_box.append(lbl_opts)
        scrolled_opts = Gtk.ScrolledWindow()
        scrolled_opts.set_min_content_height(150)
        edit_box.append(scrolled_opts)
        self.opts_flow = Gtk.FlowBox()
        self.opts_flow.set_max_children_per_line(2)
        scrolled_opts.set_child(self.opts_flow)
        self.check_buttons = {}
        for oname in OPTION_NAMES:
            chk = Gtk.CheckButton(label=oname)
            self.opts_flow.append(chk)
            self.check_buttons[oname] = chk

        # Botón actualizar
        btn_update = Gtk.Button.new_with_label("Actualizar ventana")
        btn_update.connect("clicked", self.on_update_window)
        edit_box.append(btn_update)

        self.populate_list()
        self.present()

    def populate_list(self):
        self.list_store.clear()
        for key, data in self.win_data.items():
            self.list_store.append([data["class"], data["name"], data["role"]])

    def on_open(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir archivo winoptions")
        dialog.open(self, None, self._on_open_finish)

    def _on_open_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.current_file = Path(file.get_path())
                self.win_data = parse_winoptions(self.current_file)
                self.populate_list()
        except GLib.Error:
            pass

    def on_save(self, button):
        save_winoptions(self.current_file, self.win_data)

    def on_add_window(self, button):
        dialog = Gtk.Dialog(title="Añadir ventana", transient_for=self)
        dialog.set_default_size(300, 150)
        content = dialog.get_content_area()
        content.set_margin_top(5); content.set_margin_bottom(5)
        content.set_margin_start(5); content.set_margin_end(5)

        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        content.append(grid)

        grid.attach(Gtk.Label(label="Clase:"), 0, 0, 1, 1)
        entry_class = Gtk.Entry()
        grid.attach(entry_class, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Nombre:"), 0, 1, 1, 1)
        entry_name = Gtk.Entry()
        grid.attach(entry_name, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Rol:"), 0, 2, 1, 1)
        entry_role = Gtk.Entry()
        grid.attach(entry_role, 1, 2, 1, 1)

        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Aceptar", Gtk.ResponseType.OK)
        dialog.present()

        def on_response(dialog, response):
            if response == Gtk.ResponseType.OK:
                wclass = entry_class.get_text()
                wname = entry_name.get_text()
                wrole = entry_role.get_text()
                key = (wclass, wname, wrole)
                if key not in self.win_data:
                    self.win_data[key] = {
                        "class": wclass, "name": wname, "role": wrole,
                        "icon": "", "workspace": -1, "layer": 2,
                        "geometry": "", "tray": 0, "options": {}
                    }
                    for i, oname in enumerate(OPTION_NAMES):
                        self.win_data[key]["options"][oname] = (5 <= i <= 18)
                    self.populate_list()
            dialog.destroy()

        dialog.connect("response", on_response)

    def on_delete_window(self, button):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        wclass = model[treeiter][0]
        wname = model[treeiter][1]
        wrole = model[treeiter][2]
        key = (wclass, wname, wrole)
        if key in self.win_data:
            del self.win_data[key]
            self.populate_list()

    def on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        wclass = model[treeiter][0]
        wname = model[treeiter][1]
        wrole = model[treeiter][2]
        key = (wclass, wname, wrole)
        if key in self.win_data:
            data = self.win_data[key]
            self.entry_class.set_text(data["class"])
            self.entry_name.set_text(data["name"])
            self.entry_role.set_text(data["role"])
            self.entry_icon.set_text(data["icon"])
            self.spin_workspace.set_value(data["workspace"])
            self.combo_layer.set_active(data["layer"])
            self.entry_geometry.set_text(data["geometry"])
            self.combo_tray.set_active(data["tray"])
            for oname in OPTION_NAMES:
                self.check_buttons[oname].set_active(data["options"].get(oname, False))

    def on_update_window(self, button):
        selection = self.tree_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        old_key = (model[treeiter][0], model[treeiter][1], model[treeiter][2])
        new_class = self.entry_class.get_text()
        new_name = self.entry_name.get_text()
        new_role = self.entry_role.get_text()
        new_key = (new_class, new_name, new_role)

        if old_key in self.win_data:
            data = self.win_data.pop(old_key)
        else:
            data = {"icon": "", "workspace": -1, "layer": 2, "geometry": "", "tray": 0, "options": {}}
        data["class"] = new_class
        data["name"] = new_name
        data["role"] = new_role
        data["icon"] = self.entry_icon.get_text()
        data["workspace"] = self.spin_workspace.get_value_as_int()
        data["layer"] = self.combo_layer.get_active()
        data["geometry"] = self.entry_geometry.get_text()
        data["tray"] = self.combo_tray.get_active()
        for oname in OPTION_NAMES:
            data["options"][oname] = self.check_buttons[oname].get_active()
        self.win_data[new_key] = data
        self.populate_list()

    def on_browse_icon(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar icono")
        dialog.open(self, None, self._on_browse_icon_finish)

    def _on_browse_icon_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.entry_icon.set_text(file.get_path())
        except GLib.Error:
            pass

if __name__ == "__main__":
    win = WinoptionsEditorWindow()
    loop = GLib.MainLoop()
    win.connect("destroy", lambda *a: loop.quit())
    loop.run()
