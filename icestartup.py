#!/usr/bin/env python3
"""
IceWM Startup Editor (icestartup)
Edita ~/.icewm/startup con soporte para polkit.
"""

import sys
import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gio

# ------------------------------------------------------------
# Rutas
# ------------------------------------------------------------
ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"

STARTUP_FILE = ICEWM_PRIV_DIR / "startup"

# ------------------------------------------------------------
# Funciones de lectura/escritura
# ------------------------------------------------------------
def read_startup():
    """Lee el contenido del archivo startup."""
    if not STARTUP_FILE.exists():
        return "# Archivo startup no encontrado. Crea aquí tus comandos de inicio.\n"
    try:
        with open(STARTUP_FILE, 'r') as f:
            return f.read()
    except PermissionError:
        return "# Sin permisos para leer el archivo startup.\n"

def save_startup(content, parent_window):
    """Guarda el contenido en el archivo startup. Si no hay permisos, usa pkexec."""
    try:
        # Intentar escribir directamente
        with open(STARTUP_FILE, 'w') as f:
            f.write(content)
        return True
    except PermissionError:
        # Usar pkexec para escribir con privilegios
        try:
            # Creamos un archivo temporal y luego lo movemos con pkexec
            tmpfile = STARTUP_FILE.with_suffix('.tmp')
            with open(tmpfile, 'w') as f:
                f.write(content)
            subprocess.run(["pkexec", "mv", str(tmpfile), str(STARTUP_FILE)], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            dialog = Gtk.MessageDialog(
                transient_for=parent_window,
                modal=True,
                buttons=Gtk.ButtonsType.OK,
                text="No se pudo guardar el archivo startup.\n"
                     "Asegúrate de tener permisos y que 'pkexec' esté instalado."
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()
            return False

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class StartupEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="IceWM Startup Editor")
        self.set_default_size(700, 500)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10); vbox.set_margin_bottom(10)
        vbox.set_margin_start(10); vbox.set_margin_end(10)
        self.set_child(vbox)

        # Etiqueta informativa
        lbl = Gtk.Label(label=f"Editando: {STARTUP_FILE}")
        lbl.set_halign(Gtk.Align.START)
        vbox.append(lbl)

        # Editor de texto
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self.textview.get_buffer().set_text(read_startup())
        scrolled.set_child(self.textview)
        vbox.append(scrolled)

        # Botones
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox)

        btn_save = Gtk.Button.new_with_label("Guardar")
        btn_save.set_hexpand(True)
        btn_save.connect("clicked", self.on_save)
        hbox.append(btn_save)

        btn_reload = Gtk.Button.new_with_label("Recargar")
        btn_reload.connect("clicked", self.on_reload)
        hbox.append(btn_reload)

        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *a: self.close())
        hbox.append(btn_close)

        self.present()

    def on_save(self, button):
        buf = self.textview.get_buffer()
        start_iter = buf.get_start_iter()
        end_iter = buf.get_end_iter()
        content = buf.get_text(start_iter, end_iter, False)
        if save_startup(content, self):
            # Mostrar confirmación
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                buttons=Gtk.ButtonsType.OK,
                text="Archivo startup guardado correctamente."
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()

    def on_reload(self, button):
        buf = self.textview.get_buffer()
        buf.set_text(read_startup())

if __name__ == "__main__":
    win = StartupEditorWindow()
    loop = GLib.MainLoop()
    win.connect("destroy", lambda *a: loop.quit())
    loop.run()