#!/usr/bin/env python3
"""
IceWM Startup Editor (icestartup)
Editor visual del archivo ~/.icewm/startup.
"""

import sys
import subprocess
from pathlib import Path
import re

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
# Definición de programas detectables (predefinidos)
# ------------------------------------------------------------
KNOWN_APPS = [
    {
        "name": "Sonido (volumeicon)",
        "command": "volumeicon &",
        "binary": "volumeicon",
        "category": "Sonido"
    },
    {
        "name": "Sonido (pasystray)",
        "command": "pasystray &",
        "binary": "pasystray",
        "category": "Sonido"
    },
    {
        "name": "Red (nm-applet)",
        "command": "nm-applet &",
        "binary": "nm-applet",
        "category": "Red"
    },
    {
        "name": "Portal GTK (export GTK_USE_PORTAL=1)",
        "command": "export GTK_USE_PORTAL=1",
        "binary": None,
        "category": "Sistema"
    },
    {
        "name": "Compositor (picom)",
        "command": "picom &",
        "binary": "picom",
        "category": "Apariencia"
    },
    {
        "name": "Batería (xfce4-power-manager)",
        "command": "xfce4-power-manager &",
        "binary": "xfce4-power-manager",
        "category": "Energía"
    },
    {
        "name": "Bluetooth (blueman-applet)",
        "command": "blueman-applet &",
        "binary": "blueman-applet",
        "category": "Red"
    },
    {
        "name": "Clipboard (clipit)",
        "command": "clipit &",
        "binary": "clipit",
        "category": "Utilidades"
    },
]

POLKIT_AGENTS = [
    {
        "name": "Agente Polkit (GNOME)",
        "command": "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 &",
        "binary": "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1",
        "category": "Sistema"
    },
    {
        "name": "Agente Polkit (KDE)",
        "command": "/usr/lib/polkit-kde-authentication-agent-1 &",
        "binary": "/usr/lib/polkit-kde-authentication-agent-1",
        "category": "Sistema"
    },
]

# ------------------------------------------------------------
# Funciones auxiliares
# ------------------------------------------------------------
def read_startup():
    if not STARTUP_FILE.exists():
        return ""
    with open(STARTUP_FILE, 'r') as f:
        return f.read()

def save_startup(content):
    try:
        with open(STARTUP_FILE, 'w') as f:
            f.write(content)
        STARTUP_FILE.chmod(0o755)
        return True
    except PermissionError:
        tmp_script = Path("/tmp") / f"ice_startup_{Path.home().name}.sh"
        with open(tmp_script, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"cat > {STARTUP_FILE} << 'EOFCE'\n")
            f.write(content)
            f.write("EOFCE\n")
            f.write(f"chmod 755 {STARTUP_FILE}\n")
        tmp_script.chmod(0o755)
        try:
            subprocess.run(["pkexec", str(tmp_script)], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        finally:
            tmp_script.unlink(missing_ok=True)
    return False

def is_binary_installed(binary):
    if binary is None:
        return True
    if binary.startswith('/'):
        return Path(binary).exists()
    result = subprocess.run(["which", binary], capture_output=True, text=True)
    return result.returncode == 0

def get_installed_polkit():
    for agent in POLKIT_AGENTS:
        if is_binary_installed(agent["binary"]):
            return agent
    return None

def get_all_apps():
    apps = list(KNOWN_APPS)
    polkit = get_installed_polkit()
    if polkit:
        for i, app in enumerate(apps):
            if app["name"].startswith("Portal GTK"):
                apps.insert(i, polkit)
                break
    return apps

def scan_executables():
    """Devuelve una lista de programas encontrados en el sistema."""
    paths = set()

    # 1. Binarios en PATH estándar
    for p in Path("/usr/bin").iterdir():
        if p.is_file() and not p.is_symlink():
            paths.add(p.name)
    for p in Path("/usr/local/bin").iterdir():
        if p.is_file() and not p.is_symlink():
            paths.add(p.name)

    # 2. Flatpaks instalados (detección real)
    try:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("ID"):
                    paths.add(f"flatpak run {line}")
    except FileNotFoundError:
        pass

    # 3. Aplicaciones del sistema (archivos .desktop) - limpiar duplicados
    apps_dirs = [
        Path("/usr/share/applications"),
        Path.home() / ".local/share/applications",
    ]
    for d in apps_dirs:
        if d.is_dir():
            for f in d.glob("*.desktop"):
                try:
                    content = f.read_text(errors='ignore')
                    # Solo procesar si tiene sección [Desktop Entry]
                    if "[Desktop Entry]" not in content:
                        continue
                    name_match = re.search(r'^Name=(.+)$', content, re.MULTILINE)
                    exec_match = re.search(r'^Exec=(.+)$', content, re.MULTILINE)
                    if name_match and exec_match:
                        name = name_match.group(1).strip()
                        cmd = exec_match.group(1).strip()
                        cmd = re.sub(r'%[fFuUdDnNickvm]', '', cmd).strip()
                        if not cmd.startswith("flatpak"):
                            entry = f"{name} ({cmd})"
                            paths.add(entry)
                except Exception:
                    pass

    return sorted(paths)

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class StartupEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="IceWM Startup Editor")
        self.set_default_size(650, 450)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10); vbox.set_margin_bottom(10)
        vbox.set_margin_start(10); vbox.set_margin_end(10)
        self.set_child(vbox)

        vbox.append(Gtk.Label(label="Programas que se inician con IceWM"))
        vbox.append(Gtk.Label(label="Marca los que quieras activar. Las líneas personalizadas se conservan."))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.check_listbox = Gtk.ListBox()
        scrolled.set_child(self.check_listbox)
        vbox.append(scrolled)

        hbox_add = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox_add)
        btn_add = Gtk.Button.new_with_label("➕ Añadir programa...")
        btn_add.connect("clicked", self.on_add_program)
        hbox_add.append(btn_add)
        btn_remove = Gtk.Button.new_with_label("➖ Quitar seleccionado")
        btn_remove.connect("clicked", self.on_remove_program)
        hbox_add.append(btn_remove)

        lbl_preview = Gtk.Label(label="Vista previa del archivo startup:")
        vbox.append(lbl_preview)
        self.preview_text = Gtk.TextView()
        self.preview_text.set_editable(False)
        self.preview_text.set_monospace(True)
        scrolled_preview = Gtk.ScrolledWindow()
        scrolled_preview.set_min_content_height(150)
        scrolled_preview.set_child(self.preview_text)
        vbox.append(scrolled_preview)

        hbox_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox_btns)

        btn_save = Gtk.Button.new_with_label("Guardar")
        btn_save.set_hexpand(True)
        btn_save.connect("clicked", self.on_save)
        hbox_btns.append(btn_save)

        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *a: self.close())
        hbox_btns.append(btn_close)

        self.all_apps = get_all_apps()
        self.populate_visual()
        self.present()

    def populate_visual(self, *args):
        self.check_listbox.remove_all()
        content = read_startup()
        lines = content.splitlines()

        for app in self.all_apps:
            installed = is_binary_installed(app["binary"])
            if not installed:
                continue

            cmd_check = app["command"].replace(' &','').strip()
            if cmd_check == "export GTK_USE_PORTAL=1":
                active = cmd_check in lines
            else:
                binary_name = Path(cmd_check).name
                active = any(binary_name in line for line in lines)

            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_top(3); hbox.set_margin_bottom(3)
            hbox.set_margin_start(5); hbox.set_margin_end(5)

            chk = Gtk.CheckButton(label=app["name"])
            chk.set_active(active)
            chk.connect("toggled", self.on_check_toggled, app)
            hbox.append(chk)

            lbl_cat = Gtk.Label(label=f"[{app['category']}]")
            lbl_cat.set_sensitive(False)
            hbox.append(lbl_cat)

            row.set_child(hbox)
            self.check_listbox.append(row)

        self.update_preview()

    def on_check_toggled(self, check, app):
        self.update_preview()

    def on_add_program(self, button):
        dialog = Gtk.Dialog(title="Añadir programa al inicio", transient_for=self)
        dialog.set_default_size(400, 300)

        content_area = dialog.get_content_area()
        content_area.set_margin_top(5); content_area.set_margin_bottom(5)
        content_area.set_margin_start(5); content_area.set_margin_end(5)

        entry_search = Gtk.Entry()
        entry_search.set_placeholder_text("Buscar programa...")
        content_area.append(entry_search)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        listbox = Gtk.ListBox()
        scrolled.set_child(listbox)
        content_area.append(scrolled)

        all_programs = scan_executables()

        def populate_list(filter_text=""):
            listbox.remove_all()
            for prog in all_programs:
                if filter_text and filter_text.lower() not in prog.lower():
                    continue
                row = Gtk.ListBoxRow()
                lbl = Gtk.Label(label=prog, xalign=0)
                lbl.set_margin_top(3); lbl.set_margin_bottom(3)
                lbl.set_margin_start(5)
                row.set_child(lbl)
                listbox.append(row)

        populate_list()
        entry_search.connect("changed", lambda e: populate_list(e.get_text()))

        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Añadir", Gtk.ResponseType.OK)
        dialog.present()

        dialog.connect("response", self._on_add_dialog_response, listbox, dialog)

    def _on_add_dialog_response(self, dialog, response, listbox, dialog_widget):
        if response == Gtk.ResponseType.OK:
            row = listbox.get_selected_row()
            if row:
                program = row.get_child().get_label()
                # Determinar el comando correcto
                if program.startswith("flatpak run"):
                    cmd = f"{program} &"
                    name = program
                elif '(' in program and program.endswith(')'):
                    # Formato "Nombre (comando)"
                    name = program.split('(')[0].strip()
                    cmd_part = program.split('(')[1].rstrip(')')
                    cmd = f"{cmd_part} &"
                else:
                    name = program
                    cmd = f"{program} &"
                new_app = {
                    "name": name,
                    "command": cmd,
                    "binary": cmd.split()[0],
                    "category": "Personalizado"
                }
                self.all_apps.append(new_app)
                self.populate_visual()
        dialog.destroy()

    def on_remove_program(self, button):
        row = self.check_listbox.get_selected_row()
        if row is None:
            return
        chk = row.get_child().get_first_child()
        app_name = chk.get_label()
        for app in self.all_apps:
            if app["name"] == app_name and app.get("category") == "Personalizado":
                self.all_apps.remove(app)
                self.populate_visual()
                break

    def update_preview(self):
        content = read_startup()
        lines = content.splitlines()

        desired_commands = []
        child = self.check_listbox.get_first_child()
        while child:
            row = child
            chk = row.get_child().get_first_child()
            app_name = chk.get_label()
            for app in self.all_apps:
                if app["name"] == app_name and chk.get_active():
                    desired_commands.append(app["command"])
                    break
            child = child.get_next_sibling()

        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#!'):
                new_lines.append(line)
                continue
            found = False
            for app in self.all_apps:
                cmd = app["command"].replace(' &','').strip()
                if cmd == "export GTK_USE_PORTAL=1":
                    if stripped == cmd:
                        found = True
                        if app["command"] in desired_commands:
                            new_lines.append(app["command"])
                        break
                else:
                    binary_name = Path(cmd).name
                    if binary_name in stripped:
                        found = True
                        if app["command"] in desired_commands:
                            new_lines.append(app["command"])
                        break
            if not found:
                new_lines.append(line)

        for cmd in desired_commands:
            if cmd not in new_lines:
                new_lines.append(cmd)

        buffer = self.preview_text.get_buffer()
        buffer.set_text("\n".join(new_lines))

    def on_save(self, button):
        buffer = self.preview_text.get_buffer()
        start, end = buffer.get_bounds()
        content = buffer.get_text(start, end, False)

        if not content.strip():
            content = "# No hay programas configurados\n"

        if save_startup(content):
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                buttons=Gtk.ButtonsType.OK,
                text="Archivo startup guardado correctamente."
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                buttons=Gtk.ButtonsType.OK,
                text="Error al guardar. Revisa los permisos."
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()

if __name__ == "__main__":
    win = StartupEditorWindow()
    loop = GLib.MainLoop()
    win.connect("destroy", lambda *a: loop.quit())
    loop.run()
