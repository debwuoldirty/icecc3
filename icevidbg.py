#!/usr/bin/env python3
"""
IceWM Video Background Setter (icevidbg)
Reproduce un vídeo como fondo de pantalla usando xwinwrap + mpv.
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
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv")

# ------------------------------------------------------------
# Funciones de fondo de vídeo
# ------------------------------------------------------------
def start_video(video_path):
    """Inicia el fondo de vídeo con xwinwrap + mpv."""
    stop_video()
    cmd = [
        "xwinwrap", "-ov", "-fs", "--",
        "mpv", "--wid=%WID",
        "--loop",
        "--no-audio",
        "--no-osc",
        "--osd-level=0",
        "--panscan=1.0",
        str(video_path)
    ]
    try:
        subprocess.Popen(cmd, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def stop_video():
    """Detiene el fondo de vídeo matando xwinwrap y mpv."""
    try:
        subprocess.run(["pkill", "-9", "xwinwrap"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def is_video_running():
    """Comprueba si xwinwrap está corriendo."""
    try:
        result = subprocess.run(["pgrep", "-x", "xwinwrap"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

# ------------------------------------------------------------
# Gestión del archivo startup
# ------------------------------------------------------------
def add_to_startup(video_path):
    """Añade el comando de vídeo al archivo startup de IceWM."""
    # Comando exacto que irá al startup
    command_line = (
        f'xwinwrap -ov -fs -- mpv --wid=%WID '
        f'--loop --no-audio --no-osc --osd-level=0 '
        f'--panscan=1.0 "{video_path}" &\n'
    )
    # Leer contenido actual
    if not STARTUP_FILE.exists():
        STARTUP_FILE.touch()
    with open(STARTUP_FILE, 'r') as f:
        lines = f.readlines()
    # Eliminar bloque anterior (si existe)
    new_lines = []
    inside = False
    for line in lines:
        if line.strip() == "### icevidbg-auto":
            inside = True
            continue
        elif line.strip() == "### /icevidbg-auto":
            inside = False
            continue
        if not inside:
            new_lines.append(line)
    # Añadir nuevo bloque
    new_lines.append("### icevidbg-auto\n")
    new_lines.append(command_line)
    new_lines.append("### /icevidbg-auto\n")
    # Escribir
    _safe_write_startup(new_lines)

def remove_from_startup():
    """Elimina el bloque de icevidbg del startup."""
    if not STARTUP_FILE.exists():
        return
    with open(STARTUP_FILE, 'r') as f:
        lines = f.readlines()
    new_lines = []
    inside = False
    for line in lines:
        if line.strip() == "### icevidbg-auto":
            inside = True
            continue
        elif line.strip() == "### /icevidbg-auto":
            inside = False
            continue
        if not inside:
            new_lines.append(line)
    _safe_write_startup(new_lines)

def _safe_write_startup(lines):
    """Escribe en el archivo startup, usando pkexec si no hay permisos."""
    try:
        with open(STARTUP_FILE, 'w') as f:
            f.writelines(lines)
        STARTUP_FILE.chmod(0o755)
    except PermissionError:
        # Crear un script temporal y ejecutarlo con pkexec
        tmp_script = Path("/tmp") / f"icevidbg_startup_{Path.home().name}.sh"
        with open(tmp_script, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"cat > {STARTUP_FILE} << 'EOFCE'\n")
            f.writelines(lines)
            f.write("EOFCE\n")
            f.write(f"chmod 755 {STARTUP_FILE}\n")
        tmp_script.chmod(0o755)
        try:
            subprocess.run(["pkexec", str(tmp_script)], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["sudo", str(tmp_script)], check=True)
        finally:
            tmp_script.unlink(missing_ok=True)

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class VideoBgWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="IceWM Video Background Setter")
        self.set_default_size(500, 200)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10); vbox.set_margin_bottom(10)
        vbox.set_margin_start(10); vbox.set_margin_end(10)
        self.set_child(vbox)

        # Selector de archivo
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox)
        hbox.append(Gtk.Label(label="Archivo de vídeo:"))
        self.entry_video = Gtk.Entry()
        self.entry_video.set_hexpand(True)
        hbox.append(self.entry_video)
        btn_browse = Gtk.Button(label="...")
        btn_browse.connect("clicked", self.on_browse)
        hbox.append(btn_browse)

        # Botones de acción
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(btn_box)

        self.btn_start = Gtk.Button(label="Iniciar fondo")
        self.btn_start.connect("clicked", self.on_start)
        btn_box.append(self.btn_start)

        self.btn_stop = Gtk.Button(label="Detener fondo")
        self.btn_stop.connect("clicked", self.on_stop)
        self.btn_stop.set_sensitive(is_video_running())
        btn_box.append(self.btn_stop)

        # Checkbox auto-inicio
        self.chk_autostart = Gtk.CheckButton(label="Iniciar automáticamente al arrancar IceWM")
        vbox.append(self.chk_autostart)

        # Estado
        self.label_status = Gtk.Label(label="")
        vbox.append(self.label_status)

        # Cerrar
        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *a: self.close())
        vbox.append(btn_close)

        self.present()

    def on_browse(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar archivo de vídeo")
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Archivos de vídeo (*.mp4, *.webm, *.mkv, *.avi, *.mov)")
        for ext in VIDEO_EXTENSIONS:
            filter_video.add_pattern(f"*{ext}")
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_video)
        dialog.set_filters(filter_list)
        dialog.open(self, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.entry_video.set_text(file.get_path())
        except GLib.Error:
            pass

    def on_start(self, button):
        video_path = self.entry_video.get_text().strip()
        if not video_path:
            self.label_status.set_text("Selecciona un archivo de vídeo primero.")
            return
        if start_video(video_path):
            self.label_status.set_text("Fondo de vídeo iniciado.")
            self.btn_stop.set_sensitive(True)
            if self.chk_autostart.get_active():
                add_to_startup(video_path)
        else:
            self.label_status.set_text("Error al iniciar. ¿Está instalado xwinwrap y mpv?")

    def on_stop(self, button):
        if stop_video():
            self.label_status.set_text("Fondo de vídeo detenido.")
            self.btn_stop.set_sensitive(False)
            if self.chk_autostart.get_active():
                remove_from_startup()
        else:
            self.label_status.set_text("No hay fondo de vídeo activo.")

if __name__ == "__main__":
    win = VideoBgWindow()
    loop = GLib.MainLoop()
    win.connect("destroy", lambda *a: loop.quit())
    loop.run()
