#!/usr/bin/env python3
"""
IceWM Control Center 3 (icecc3)
Un lanzador moderno para configurar IceWM.
Licencia: GPL-2.0+
Adaptado del diseño de IceCC 2.9 de Vadim A. Khohlov
"""

import sys
import subprocess
from pathlib import Path
import os
import base64

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib, GdkPixbuf

# ------------------------------------------------------------
# Directorio del script
# ------------------------------------------------------------
SCRIPT_DIR = Path(os.path.realpath(__file__)).parent

# ------------------------------------------------------------
# Logo de IceWM incrustado en Base64
# ------------------------------------------------------------
def get_logo_pixbuf():
    """Carga el logo de IceWM desde Base64 incrustado."""
    logo_base64 = "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"
    try:
        data = base64.b64decode(logo_base64)
        loader = GdkPixbuf.PixbufLoader()
        loader.write(data)
        loader.close()
        return loader.get_pixbuf()
    except Exception:
        return None

# ------------------------------------------------------------
# Configuración de rutas
# ------------------------------------------------------------
ICEWM_CONFIG_DIR = Path.home() / ".icewm"
ICEWM_GLOBAL_DIR = Path("/usr/share/icewm")

CONFIG_FILES = {
    "menu": ICEWM_CONFIG_DIR / "menu",
    "toolbar": ICEWM_CONFIG_DIR / "toolbar",
    "preferences": ICEWM_CONFIG_DIR / "preferences",
    "winoptions": ICEWM_CONFIG_DIR / "winoptions",
    "keys": ICEWM_CONFIG_DIR / "keys",
}

# ------------------------------------------------------------
# Herramientas
# ------------------------------------------------------------
TOOLS = [
    {
        "name": "Editor del menu",
        "icon": "menu",
        "command": lambda: run_command([str(SCRIPT_DIR / "icemc.py"), str(CONFIG_FILES["menu"])]),
        "tooltip": "Editar el menú de aplicaciones"
    },
    {
        "name": "Editor de la barra de herramientas",
        "icon": "toolbar",
        "command": lambda: run_command([str(SCRIPT_DIR / "icemc.py"), str(CONFIG_FILES["toolbar"])]),
        "tooltip": "Añadir y ordenar lanzadores en la barra superior"
    },
    {
        "name": "Configurar Panel Superior",
        "icon": "settings",
        "command": lambda: run_command(str(SCRIPT_DIR / "icetaskbar.py")),
        "tooltip": "Cambiar posición, tamaño y visibilidad de la barra de tareas"
    },
    {
        "name": "Editor de Winoptions",
        "icon": "settings",
        "command": lambda: run_command(str(SCRIPT_DIR / "icewoed.py")),
        "tooltip": "Ajustes por ventana (WinOptions)"
    },
    {
        "name": "Agregar/Quitar Areas de trabajo",
        "icon": "workspaces",
        "command": lambda: run_command(str(SCRIPT_DIR / "iceworkspaces.py")),
        "tooltip": "Añadir, eliminar y renombrar áreas de trabajo"
    },
    {
        "name": "Editar inicio (startup)",
        "icon": "terminal",
        "command": lambda: run_command(["python3", str(SCRIPT_DIR / "icestartup.py")]),
        "tooltip": "Editar el archivo de inicio de IceWM"
    },
    {
        "name": "Editor de teclas",
        "icon": "keyboard",
        "command": lambda: run_command(str(SCRIPT_DIR / "iceked.py")),
        "tooltip": "Atajos de teclado"
    },
    {
        "name": "Cambiar tema",
        "icon": "themes",
        "command": lambda: run_command(str(SCRIPT_DIR / "icets.py")),
        "tooltip": "Explorador de temas visual"
    },
    {
        "name": "Fondo de escritorio",
        "icon": "desktop",
        "command": lambda: run_command(str(SCRIPT_DIR / "icebgset.py")),
        "tooltip": "Cambiar el fondo de pantalla"
    },
    {
        "name": "Fondo de vídeo",
        "icon": "video",   # puedes usar el icono 'video' de nuestro pack Win98
        "command": lambda: run_command(str(SCRIPT_DIR / "icevidbg.py")),
        "tooltip": "Establecer un vídeo como fondo de pantalla"
    },
    {
        "name": "Sonido",
        "icon": "sound",
        "command": lambda: run_command(str(SCRIPT_DIR / "icesndcfg.py")),
        "tooltip": "Ajustes de sonido"
    },
    {
        "name": "Cursores",
        "icon": "mouse",
        "command": lambda: run_command(["python3", str(SCRIPT_DIR / "icecurcfg.py")]),
        "tooltip": "Configurar cursores"
    },
]

# ------------------------------------------------------------
# Funciones auxiliares
# ------------------------------------------------------------
_active_window = None

def get_icon_pixbuf(name):
    """Carga un icono desde Base64 incrustado."""
    import base64
    from icons_base64 import ICONS_BASE64
    if name in ICONS_BASE64:
        try:
            data = base64.b64decode(ICONS_BASE64[name])
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)
            loader.close()
            return loader.get_pixbuf()
        except Exception:
            pass
    return None

def open_file_with_editor(file_path):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        file_path.touch()
    uri = GLib.filename_to_uri(str(file_path), None)
    Gio.AppInfo.launch_default_for_uri(uri, None)

def run_command(command):
    if isinstance(command, str):
        cmd_list = command.split()
    else:
        cmd_list = command
    try:
        subprocess.Popen(cmd_list, start_new_session=True)
    except FileNotFoundError:
        show_error(f"No se encontró el comando '{cmd_list[0]}'.")

def show_error(msg):
    global _active_window
    dialog = Gtk.MessageDialog(
        transient_for=_active_window,
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=msg
    )
    dialog.present()
    dialog.connect("response", lambda d, r: d.close())

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class IceCCWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        global _active_window
        _active_window = self

        self.set_title("IceWM Control Center")
        self.set_default_size(500, 400)

        # Cabecera con logo
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        logo_pixbuf = get_logo_pixbuf()
        if logo_pixbuf:
            logo_image = Gtk.Image.new_from_pixbuf(logo_pixbuf)
            logo_image.set_pixel_size(38)
            header_box.append(logo_image)

        title_label = Gtk.Label(label="IceWM Control Center")
        header_box.append(title_label)

        header.set_title_widget(header_box)
        self.set_titlebar(header)

        # Cargar tema CSS retro
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(str(SCRIPT_DIR / "icewm-retro.css"))
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Caja vertical principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(vbox)

        # Panel de iconos estilo Control Panel
        flowbox = Gtk.FlowBox()
        flowbox.set_max_children_per_line(3)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_margin_top(10)
        flowbox.set_margin_bottom(10)
        flowbox.set_margin_start(10)
        flowbox.set_margin_end(10)
        flowbox.set_column_spacing(20)
        flowbox.set_row_spacing(15)

        for tool in TOOLS:
            btn = Gtk.Button()
            btn.set_tooltip_text(tool["tooltip"])
            btn.add_css_class("icon-button")
            btn.connect("clicked", lambda widget, cmd=tool["command"]: cmd())

            vbox_icon = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            vbox_icon.set_margin_top(5)
            vbox_icon.set_margin_bottom(5)
            vbox_icon.set_margin_start(5)
            vbox_icon.set_margin_end(5)

            icon_name = tool.get("icon", "")
            custom_icon = get_icon_pixbuf(icon_name)
            if custom_icon:
                icon = Gtk.Image.new_from_pixbuf(custom_icon)
            else:
                icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(48)
            vbox_icon.append(icon)

            label = Gtk.Label(label=tool["name"])
            label.set_wrap(True)
            label.set_max_width_chars(12)
            label.set_justify(Gtk.Justification.CENTER)
            vbox_icon.append(label)

            btn.set_child(vbox_icon)
            flowbox.append(btn)

        vbox.append(flowbox)

        btn_exit = Gtk.Button.new_with_label("Salir")
        btn_exit.set_margin_bottom(10)
        vbox.append(btn_exit)
        btn_exit.connect("clicked", lambda _: self.close())

# ------------------------------------------------------------
# Aplicación GTK
# ------------------------------------------------------------
class IceCCApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.controlcenter")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = IceCCWindow(application=app)
        win.present()

# ------------------------------------------------------------
# Punto de entrada
# ------------------------------------------------------------
if __name__ == "__main__":
    app = IceCCApp()
    app.run(sys.argv)
