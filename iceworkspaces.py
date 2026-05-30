#!/usr/bin/env python3
"""
IceWM Workspaces Manager (iceworkspaces)
Permite añadir, eliminar y renombrar áreas de trabajo.
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

PREFERENCES_FILE = ICEWM_PRIV_DIR / "preferences"

# ------------------------------------------------------------
# Funciones de lectura/escritura
# ------------------------------------------------------------
def read_workspaces():
    """Lee los nombres de los workspaces desde preferences."""
    names = ["1", "2", "3", "4"]  # default
    if PREFERENCES_FILE.exists():
        with open(PREFERENCES_FILE) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("WorkspaceNames"):
                    # Extraer los nombres entre comillas
                    parts = stripped.split("=", 1)
                    if len(parts) == 2:
                        value = parts[1].strip()
                        # Parsear lista: "1","2","3"
                        names = []
                        current = ""
                        in_quotes = False
                        for ch in value:
                            if ch == '"':
                                in_quotes = not in_quotes
                            elif ch == ',' and not in_quotes:
                                if current.strip():
                                    names.append(current.strip())
                                current = ""
                            else:
                                current += ch
                        if current.strip():
                            names.append(current.strip())
                    break
    return names

def write_workspaces(names):
    """Escribe la línea WorkspaceNames en preferences."""
    # Formatear: WorkspaceNames="nombre1","nombre2",...
    formatted = "WorkspaceNames=" + ",".join(f'"{name}"' for name in names)
    
    lines = []
    if PREFERENCES_FILE.exists():
        with open(PREFERENCES_FILE) as f:
            lines = f.readlines()
    
    found = False
    with open(PREFERENCES_FILE, 'w') as f:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("WorkspaceNames"):
                f.write(formatted + "\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write("\n" + formatted + "\n")

def restart_icewm():
    """Reinicia IceWM para aplicar cambios."""
    try:
        subprocess.run(["pkill", "-1", "icewm"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class WorkspacesWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="IceWM Workspaces Manager")
        self.set_default_size(400, 350)

        # Cargar workspaces actuales
        self.workspaces = read_workspaces()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10); vbox.set_margin_bottom(10)
        vbox.set_margin_start(10); vbox.set_margin_end(10)
        self.set_child(vbox)

        # Título
        vbox.append(Gtk.Label(label="Áreas de trabajo"))
        vbox.append(Gtk.Label(label="Puedes añadir, eliminar o renombrar workspaces."))

        # Lista de workspaces
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-selected", self.on_row_selected)
        scrolled.set_child(self.listbox)
        vbox.append(scrolled)

        # Botones de acción
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox)

        btn_add = Gtk.Button.new_with_label("➕ Añadir")
        btn_add.connect("clicked", self.on_add)
        hbox.append(btn_add)

        btn_remove = Gtk.Button.new_with_label("➖ Eliminar")
        btn_remove.connect("clicked", self.on_remove)
        hbox.append(btn_remove)

        # Editor de nombre
        hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox2)
        hbox2.append(Gtk.Label(label="Nombre:"))
        self.entry_name = Gtk.Entry()
        self.entry_name.set_hexpand(True)
        hbox2.append(self.entry_name)

        btn_rename = Gtk.Button.new_with_label("Renombrar")
        btn_rename.connect("clicked", self.on_rename)
        hbox2.append(btn_rename)

        # Estado
        self.label_status = Gtk.Label(label="")
        vbox.append(self.label_status)

        # Botones finales
        hbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox3)

        btn_save = Gtk.Button.new_with_label("Guardar cambios")
        btn_save.set_hexpand(True)
        btn_save.connect("clicked", self.on_save)
        hbox3.append(btn_save)

        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *a: self.close())
        hbox3.append(btn_close)

        self.populate_list()
        self.present()

    def populate_list(self):
        """Rellena la lista con los nombres actuales."""
        self.listbox.remove_all()
        for name in self.workspaces:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=name, xalign=0)
            lbl.set_margin_top(5); lbl.set_margin_bottom(5)
            lbl.set_margin_start(10)
            row.set_child(lbl)
            self.listbox.append(row)

    def get_selected_index(self):
        """Devuelve el índice del workspace seleccionado, o -1."""
        row = self.listbox.get_selected_row()
        if row is None:
            return -1
        return row.get_index()

    def on_row_selected(self, listbox, row):
        """Al seleccionar un workspace, muestra su nombre en el editor."""
        if row is None:
            return
        idx = row.get_index()
        if 0 <= idx < len(self.workspaces):
            self.entry_name.set_text(self.workspaces[idx])

    def on_add(self, button):
        """Añade un nuevo workspace con nombre por defecto."""
        new_name = f" {len(self.workspaces) + 1} "
        self.workspaces.append(new_name)
        self.populate_list()
        self.label_status.set_text(f"Workspace '{new_name}' añadido.")

    def on_remove(self, button):
        """Elimina el workspace seleccionado."""
        idx = self.get_selected_index()
        if idx < 0:
            self.label_status.set_text("Selecciona un workspace primero.")
            return
        if len(self.workspaces) <= 1:
            self.label_status.set_text("Debe haber al menos un workspace.")
            return
        removed = self.workspaces.pop(idx)
        self.populate_list()
        self.label_status.set_text(f"Workspace '{removed}' eliminado.")

    def on_rename(self, button):
        """Renombra el workspace seleccionado."""
        idx = self.get_selected_index()
        if idx < 0:
            self.label_status.set_text("Selecciona un workspace primero.")
            return
        new_name = self.entry_name.get_text().strip()
        if not new_name:
            self.label_status.set_text("El nombre no puede estar vacío.")
            return
        self.workspaces[idx] = new_name
        self.populate_list()
        # Re-seleccionar
        row = self.listbox.get_row_at_index(idx)
        if row:
            self.listbox.select_row(row)
        self.label_status.set_text(f"Workspace renombrado a '{new_name}'.")

    def on_save(self, button):
        """Guarda los cambios y reinicia IceWM."""
        write_workspaces(self.workspaces)
        restart_icewm()
        self.label_status.set_text("Cambios guardados. IceWM reiniciado.")

if __name__ == "__main__":
    win = WorkspacesWindow()
    loop = GLib.MainLoop()
    win.connect("destroy", lambda *a: loop.quit())
    loop.run()
