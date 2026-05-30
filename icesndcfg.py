#!/usr/bin/env python3
"""
IceWM Sound Configurator (icesndcfg)
Basado en icesndcfg.cpp y guievent.h de Vadim A. Khohlov
"""

import sys
import subprocess
import shutil
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

# ------------------------------------------------------------
# Rutas y eventos
# ------------------------------------------------------------
ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"

ICEWM_SOUNDS_DIR = ICEWM_PRIV_DIR / "sounds"

GUI_EVENTS = [
    "startup", "shutdown", "restart", "closeAll", "launchApp",
    "workspaceChange", "windowOpen", "windowClose", "dialogOpen",
    "dialogClose", "windowMin", "windowMax", "windowRestore",
    "windowHide", "windowRollup", "windowLower", "windowSized",
    "windowMoved", "startMenu"
]

def copy_file(src, dst):
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"Error copiando {src} -> {dst}: {e}")
        return False

def play_sound(filepath):
    try:
        subprocess.run(["aplay", str(filepath)], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        try:
            subprocess.run(["paplay", str(filepath)], stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("No se encontró un reproductor de sonido (aplay o paplay)")

class SoundConfigWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("IceWM Sound Configurator")
        self.set_default_size(600, 400)

        self.ice_sounds_dir = ICEWM_SOUNDS_DIR
        self.sounds_dir = Path.home() / "Music"

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5); vbox.set_margin_bottom(5)
        vbox.set_margin_start(5); vbox.set_margin_end(5)
        self.set_child(vbox)

        # Directorio de sonidos IceWM
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(hbox)
        hbox.append(Gtk.Label(label="Dir. sonidos IceWM:"))
        self.entry_ice_dir = Gtk.Entry()
        self.entry_ice_dir.set_text(str(self.ice_sounds_dir))
        hbox.append(self.entry_ice_dir)
        btn_ice_dir = Gtk.Button.new_with_label("...")
        btn_ice_dir.connect("clicked", self.on_browse_ice_dir)
        hbox.append(btn_ice_dir)

        # Panel con listas
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(300)
        vbox.append(paned)

        # Lista de eventos
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        left_box.set_margin_top(5); left_box.set_margin_bottom(5)
        left_box.set_margin_start(5); left_box.set_margin_end(5)
        paned.set_start_child(left_box)
        left_box.append(Gtk.Label(label="Eventos IceWM:"))
        scrolled_events = Gtk.ScrolledWindow()
        self.events_listbox = Gtk.ListBox()
        for ev in GUI_EVENTS:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=ev, xalign=0))
            self.events_listbox.append(row)
        scrolled_events.set_child(self.events_listbox)
        left_box.append(scrolled_events)

        # Lista de sonidos disponibles
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        right_box.set_margin_top(5); right_box.set_margin_bottom(5)
        right_box.set_margin_start(5); right_box.set_margin_end(5)
        paned.set_end_child(right_box)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        right_box.append(hbox)
        hbox.append(Gtk.Label(label="Dir. sonidos:"))
        self.entry_sounds_dir = Gtk.Entry()
        self.entry_sounds_dir.set_text(str(self.sounds_dir))
        hbox.append(self.entry_sounds_dir)
        btn_browse = Gtk.Button.new_with_label("...")
        btn_browse.connect("clicked", self.on_browse_sounds_dir)
        hbox.append(btn_browse)
        btn_reload = Gtk.Button.new_with_label("Recargar")
        btn_reload.connect("clicked", self.reload_sounds)
        hbox.append(btn_reload)

        scrolled_sounds = Gtk.ScrolledWindow()
        self.sounds_listbox = Gtk.ListBox()
        scrolled_sounds.set_child(self.sounds_listbox)
        right_box.append(scrolled_sounds)

        # Botones de acción
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(btn_box)

        btn_play_event = Gtk.Button.new_with_label("Reproducir evento")
        btn_play_event.connect("clicked", self.on_play_event)
        btn_box.append(btn_play_event)

        btn_play_sound = Gtk.Button.new_with_label("Reproducir sonido")
        btn_play_sound.connect("clicked", self.on_play_sound)
        btn_box.append(btn_play_sound)

        btn_set = Gtk.Button.new_with_label("Asignar")
        btn_set.connect("clicked", self.on_set)
        btn_box.append(btn_set)

        btn_unset = Gtk.Button.new_with_label("Quitar")
        btn_unset.connect("clicked", self.on_unset)
        btn_box.append(btn_unset)

        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *args: self.close())
        btn_box.append(btn_close)

        self.reload_sounds()

    def reload_sounds(self, *args):
        self.sounds_listbox.remove_all()
        directory = Path(self.entry_sounds_dir.get_text())
        if not directory.is_dir():
            return
        wav_files = sorted([f for f in directory.iterdir() if f.suffix.lower() == ".wav"])
        for wav in wav_files:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=wav.name, xalign=0))
            row.wav_path = wav
            self.sounds_listbox.append(row)

    def get_selected_event(self):
        row = self.events_listbox.get_selected_row()
        if row:
            return row.get_child().get_label()
        return None

    def get_selected_sound_path(self):
        row = self.sounds_listbox.get_selected_row()
        if row and hasattr(row, 'wav_path'):
            return row.wav_path
        return None

    def on_browse_ice_dir(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar directorio de sonidos de IceWM")
        dialog.select_folder(self, None, self._on_ice_dir_selected)

    def _on_ice_dir_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.ice_sounds_dir = Path(folder.get_path())
                self.entry_ice_dir.set_text(str(self.ice_sounds_dir))
        except GLib.Error:
            pass

    def on_browse_sounds_dir(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar directorio con archivos .wav")
        dialog.select_folder(self, None, self._on_sounds_dir_selected)

    def _on_sounds_dir_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.sounds_dir = Path(folder.get_path())
                self.entry_sounds_dir.set_text(str(self.sounds_dir))
                self.reload_sounds()
        except GLib.Error:
            pass

    def on_play_event(self, button):
        event = self.get_selected_event()
        if event:
            wav_file = self.ice_sounds_dir / f"{event}.wav"
            if wav_file.exists():
                play_sound(wav_file)
            else:
                print(f"No hay sonido para el evento {event}")

    def on_play_sound(self, button):
        sound_path = self.get_selected_sound_path()
        if sound_path:
            play_sound(sound_path)

    def on_set(self, button):
        event = self.get_selected_event()
        sound_path = self.get_selected_sound_path()
        if event and sound_path:
            dest = self.ice_sounds_dir / f"{event}.wav"
            if copy_file(sound_path, dest):
                print(f"Sonido {event} asignado correctamente.")
            else:
                print("Error al copiar el archivo de sonido.")

    def on_unset(self, button):
        event = self.get_selected_event()
        if event:
            wav_file = self.ice_sounds_dir / f"{event}.wav"
            try:
                wav_file.unlink()
                print(f"Sonido {event} eliminado.")
            except FileNotFoundError:
                print(f"No existía sonido para {event}")

class SoundConfigApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.icesndcfg")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = SoundConfigWindow(application=app)
        win.present()

if __name__ == "__main__":
    app = SoundConfigApp()
    app.run(sys.argv)