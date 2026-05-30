#!/usr/bin/env python3
"""
IceWM Taskbar & Toolbar Configurator (icetaskbar)
Escribe en prefoverride y preferences para máxima compatibilidad.
"""

import sys
import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

# ------------------------------------------------------------
# Rutas
# ------------------------------------------------------------
ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"

PREFERENCES_FILE = ICEWM_PRIV_DIR / "preferences"
PREFOVERRIDE_FILE = ICEWM_PRIV_DIR / "prefoverride"

# ------------------------------------------------------------
# Utilidades de configuración
# ------------------------------------------------------------
def read_effective_preferences():
    opts = {}
    for cfg in (PREFERENCES_FILE, PREFOVERRIDE_FILE):
        if cfg.exists():
            with open(cfg, 'r') as f:
                for line in f:
                    stripped = line.strip()
                    if '=' in stripped and not stripped.startswith('#'):
                        key, val = stripped.split('=', 1)
                        opts[key.strip()] = val.strip().split('#')[0].strip()
    return opts

def write_preference_dual(key, value):
    """Escribe key=value tanto en prefoverride como en preferences."""
    for filepath in (PREFOVERRIDE_FILE, PREFERENCES_FILE):
        if not filepath.exists():
            continue
        lines = []
        with open(filepath, 'r') as f:
            lines = f.readlines()
        with open(filepath, 'w') as f:
            found = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(key + ' ') or stripped.startswith(key + '='):
                    f.write(f'{key} = {value}\n')
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f'{key} = {value}\n')

def restart_icewm():
    try:
        subprocess.run(["pkill", "-1", "icewm"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class TaskbarConfigWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Configuración de Barras")
        self.set_default_size(480, 650)

        self.prefs = read_effective_preferences()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10); vbox.set_margin_bottom(10)
        vbox.set_margin_start(10); vbox.set_margin_end(10)
        self.set_child(vbox)

        # ── Barra de tareas (ventanas) ──
        frame = Gtk.Frame(label="Barra de tareas (ventanas)")
        vbox.append(frame)
        grid = Gtk.Grid()
        grid.set_column_spacing(10); grid.set_row_spacing(8)
        grid.set_margin_top(8); grid.set_margin_bottom(8)
        grid.set_margin_start(8); grid.set_margin_end(8)
        frame.set_child(grid)

        self.chk_top = Gtk.CheckButton(label="Arriba")
        self.chk_top.set_active(self.prefs.get("TaskBarAtTop", "0") == "1")
        self.chk_top.connect("toggled", lambda w: self._update("TaskBarAtTop", "1" if w.get_active() else "0"))
        grid.attach(self.chk_top, 0, 0, 1, 1)

        self.chk_double = Gtk.CheckButton(label="Doble altura")
        self.chk_double.set_active(self.prefs.get("TaskBarDoubleHeight", "0") == "1")
        self.chk_double.connect("toggled", lambda w: self._update("TaskBarDoubleHeight", "1" if w.get_active() else "0"))
        grid.attach(self.chk_double, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Iconos (px):", xalign=0), 0, 1, 1, 1)
        self.spin_task_icon = Gtk.SpinButton.new_with_range(16, 128, 8)
        self.spin_task_icon.set_value(int(self.prefs.get("TaskBarIconSize", "32")))
        self.spin_task_icon.connect("value-changed", lambda w: self._update("TaskBarIconSize", str(w.get_value_as_int())))
        grid.attach(self.spin_task_icon, 1, 1, 1, 1)

        # ── Barra de herramientas (lanzadores) ──
        frame2 = Gtk.Frame(label="Barra de herramientas (lanzadores)")
        vbox.append(frame2)
        grid2 = Gtk.Grid()
        grid2.set_column_spacing(10); grid2.set_row_spacing(8)
        grid2.set_margin_top(8); grid2.set_margin_bottom(8)
        grid2.set_margin_start(8); grid2.set_margin_end(8)
        frame2.set_child(grid2)

        self.chk_toolbar = Gtk.CheckButton(label="Mostrar barra separada")
        self.chk_toolbar.set_active(self.prefs.get("ShowToolBar", "0") == "1")
        self.chk_toolbar.connect("toggled", lambda w: self._update("ShowToolBar", "1" if w.get_active() else "0"))
        grid2.attach(self.chk_toolbar, 0, 0, 1, 1)

        self.chk_toolbar_bottom = Gtk.CheckButton(label="Poner barra abajo")
        self.chk_toolbar_bottom.set_active(self.prefs.get("ToolBarAtTop", "1") == "0")
        self.chk_toolbar_bottom.connect("toggled", lambda w: self._update("ToolBarAtTop", "0" if w.get_active() else "1"))
        grid2.attach(self.chk_toolbar_bottom, 1, 0, 1, 1)

        grid2.attach(Gtk.Label(label="Iconos (px):", xalign=0), 0, 1, 1, 1)
        self.spin_tool_icon = Gtk.SpinButton.new_with_range(16, 128, 8)
        self.spin_tool_icon.set_value(int(self.prefs.get("ToolBarIconSize", "32")))
        self.spin_tool_icon.connect("value-changed", lambda w: self._update("ToolBarIconSize", str(w.get_value_as_int())))
        grid2.attach(self.spin_tool_icon, 1, 1, 1, 1)

        # ── Tamaños generales de iconos ──
        frame3 = Gtk.Frame(label="Tamaños generales (afectan si el tema no los define)")
        vbox.append(frame3)
        grid3 = Gtk.Grid()
        grid3.set_column_spacing(10); grid3.set_row_spacing(8)
        grid3.set_margin_top(8); grid3.set_margin_bottom(8)
        grid3.set_margin_start(8); grid3.set_margin_end(8)
        frame3.set_child(grid3)

        for i, (label, key) in enumerate([
            ("SmallIconSize", "SmallIconSize"),
            ("LargeIconSize", "LargeIconSize"),
            ("HugeIconSize", "HugeIconSize"),
        ]):
            grid3.attach(Gtk.Label(label=f"{label} (px):", xalign=0), 0, i, 1, 1)
            spin = Gtk.SpinButton.new_with_range(16, 256, 8)
            spin.set_value(int(self.prefs.get(key, "16")))
            spin.connect("value-changed", lambda w, k=key: self._update(k, str(w.get_value_as_int())))
            grid3.attach(spin, 1, i, 1, 1)

        # ── Elementos visibles ──
        frame4 = Gtk.Frame(label="Elementos en la barra de tareas")
        vbox.append(frame4)
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_margin_top(8); flow.set_margin_bottom(8)
        flow.set_margin_start(8); flow.set_margin_end(8)
        frame4.set_child(flow)

        for label, key in [
            ("Escritorios", "TaskBarShowWorkspaces"),
            ("Lista ventanas", "TaskBarShowWindows"),
            ("Botón Escritorio", "TaskBarShowShowDesktopButton"),
            ("Bandeja sistema", "TaskBarShowTray"),
            ("Reloj", "TaskBarShowClock"),
            ("CPU", "TaskBarShowCPUStatus"),
            ("Red", "TaskBarShowNetStatus"),
            ("Batería", "TaskBarShowAPMStatus"),
        ]:
            chk = Gtk.CheckButton(label=label)
            chk.set_active(self.prefs.get(key, "1") == "1")
            chk.connect("toggled", lambda w, k=key: self._update(k, "1" if w.get_active() else "0"))
            flow.append(chk)

        # ── Botones ──
        self.lbl_status = Gtk.Label(label="Cambios guardados en prefoverride + preferences")
        vbox.append(self.lbl_status)

        hbox_btn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox_btn)
        btn_restart = Gtk.Button(label="Reiniciar IceWM")
        btn_restart.set_hexpand(True)
        btn_restart.connect("clicked", lambda b: restart_icewm())
        hbox_btn.append(btn_restart)
        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *args: self.close())
        hbox_btn.append(btn_close)

    def _update(self, key, value):
        write_preference_dual(key, value)
        self.prefs[key] = value
        self.lbl_status.set_text(f"✔ {key} = {value}  (aplicar reinicio)")

# ------------------------------------------------------------
# App
# ------------------------------------------------------------
class TaskbarConfigApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.icetaskbar")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = TaskbarConfigWindow(application=app)
        win.present()

if __name__ == "__main__":
    app = TaskbarConfigApp()
    app.run(sys.argv)
