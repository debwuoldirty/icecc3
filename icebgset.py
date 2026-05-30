#!/usr/bin/env python3
import sys, subprocess
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"
ICEWM_PREFERENCES = ICEWM_PRIV_DIR / "preferences"
ICEWM_PREFOVERRIDE = ICEWM_PRIV_DIR / "prefoverride"
IMAGE_EXTENSIONS = (".png", ".xpm", ".jpg", ".jpeg", ".gif", ".bmp", ".img")

def read_current_image():
    for cfg in (ICEWM_PREFOVERRIDE, ICEWM_PREFERENCES):
        if cfg.exists():
            try:
                with open(cfg) as f:
                    for line in f:
                        if line.strip().startswith("DesktopBackgroundImage"):
                            if '"' in line:
                                return line.split('"')[1]
                            else:
                                return line.split("=",1)[1].strip()
            except PermissionError:
                pass
    return ""

def apply_background(image_path, centered):
    ICEWM_PRIV_DIR.mkdir(parents=True, exist_ok=True)
    for cfg in (ICEWM_PREFOVERRIDE, ICEWM_PREFERENCES):
        lines = []
        if cfg.exists():
            with open(cfg) as f:
                lines = f.readlines()
        with open(cfg, 'w') as f:
            found_img = False; found_center = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("DesktopBackgroundImage"):
                    f.write(f'DesktopBackgroundImage = "{image_path}"\n')
                    found_img = True
                elif stripped.startswith("DesktopBackgroundCenter"):
                    f.write(f'DesktopBackgroundCenter = {1 if centered else 0} # 0/1\n')
                    found_center = True
                else:
                    f.write(line)
            if not found_img:
                f.write(f'DesktopBackgroundImage = "{image_path}"\n')
            if not found_center:
                f.write(f'DesktopBackgroundCenter = {1 if centered else 0} # 0/1\n')

    # Aplicar el cambio
    if image_path:
        # Intento con icewmbg <imagen> (método directo)
        try:
            subprocess.run(["icewmbg", image_path], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Si falla, recargamos icewmbg
            subprocess.run(["pkill", "-HUP", "icewmbg"], stderr=subprocess.DEVNULL)
    else:
        # Sin imagen: recargar para que use el color del tema
        subprocess.run(["pkill", "-HUP", "icewmbg"], stderr=subprocess.DEVNULL)

    # Asegurar que icewmbg esté corriendo
    subprocess.Popen(["icewmbg"])

class IceBgSetWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("IceWM Background Setter")
        self.set_default_size(500, 400)

        self.bg_image = read_current_image()
        self.bg_centered = False

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10); vbox.set_margin_bottom(10)
        vbox.set_margin_start(10); vbox.set_margin_end(10)
        self.set_child(vbox)

        hbox_dir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox_dir)
        hbox_dir.append(Gtk.Label(label="Directorio:"))
        self.dir_entry = Gtk.Entry()
        default_dir = str(Path.home() / "Imágenes")
        if self.bg_image and Path(self.bg_image).parent.is_dir():
            default_dir = str(Path(self.bg_image).parent)
        self.dir_entry.set_text(default_dir)
        hbox_dir.append(self.dir_entry)
        btn_browse = Gtk.Button(label="...")
        btn_browse.connect("clicked", self.on_browse_dir)
        hbox_dir.append(btn_browse)
        btn_reload = Gtk.Button(label="Recargar")
        btn_reload.connect("clicked", self.reload_images)
        hbox_dir.append(btn_reload)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(200)
        vbox.append(paned)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(150)
        paned.set_start_child(scrolled)
        self.image_listbox = Gtk.ListBox()
        self.image_listbox.connect("row-selected", self.on_image_selected)
        scrolled.set_child(self.image_listbox)

        self.preview = Gtk.Picture()
        self.preview.set_hexpand(True); self.preview.set_vexpand(True)
        self.preview.set_size_request(200, 150)
        paned.set_end_child(self.preview)

        self.center_check = Gtk.CheckButton(label="Centrar (no mosaico)")
        vbox.append(self.center_check)

        hbox_btn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(hbox_btn)
        btn_apply = Gtk.Button(label="Aplicar")
        btn_apply.set_hexpand(True); btn_apply.connect("clicked", self.on_apply)
        hbox_btn.append(btn_apply)
        btn_ok = Gtk.Button(label="Ok")
        btn_ok.set_hexpand(True); btn_ok.connect("clicked", self.on_ok)
        hbox_btn.append(btn_ok)
        btn_close = Gtk.Button(label="Cerrar")
        btn_close.set_hexpand(True); btn_close.connect("clicked", lambda *a: self.close())
        hbox_btn.append(btn_close)

        self.current_image_path = None
        self.reload_images()
        if self.bg_image:
            self.select_image_in_list(Path(self.bg_image).name)

    def select_image_in_list(self, filename):
        row = self.image_listbox.get_row_at_index(0)
        while row:
            if hasattr(row, 'img_path') and row.img_path.name == filename:
                self.image_listbox.select_row(row)
                break
            row = row.get_next_sibling()

    def on_browse_dir(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar directorio de imágenes")
        dialog.select_folder(self, None, self._on_dir_selected)

    def _on_dir_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.dir_entry.set_text(folder.get_path())
                self.reload_images()
        except GLib.Error:
            pass

    def reload_images(self, *args):
        self.image_listbox.remove_all()
        row = Gtk.ListBoxRow()
        lbl = Gtk.Label(label="<ninguna>", xalign=0)
        lbl.set_margin_top(3); lbl.set_margin_bottom(3)
        row.set_child(lbl)
        self.image_listbox.append(row)
        directory = Path(self.dir_entry.get_text())
        if not directory.is_dir():
            return
        images = sorted([f for f in directory.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS])
        for img_file in images:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=img_file.name, xalign=0, margin_top=3, margin_bottom=3)
            row.set_child(lbl)
            row.img_path = img_file
            self.image_listbox.append(row)

    def on_image_selected(self, listbox, row):
        if row and row.get_index() > 0:
            img_path = row.img_path
            if img_path.exists():
                self.preview.set_filename(str(img_path))
                self.current_image_path = img_path
                return
        self.preview.set_filename(None)
        self.current_image_path = None

    def on_apply(self, *args):
        selected_row = self.image_listbox.get_selected_row()
        if selected_row and selected_row.get_index() > 0:
            img_path = selected_row.img_path
            bg_image = str(img_path)
        else:
            bg_image = ""
        centered = self.center_check.get_active()
        apply_background(bg_image, centered)

    def on_ok(self, *args):
        self.on_apply()
        self.close()

class IceBgSetApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.icebgset")
        self.connect("activate", self.on_activate)
    def on_activate(self, app):
        win = IceBgSetWindow(application=app)
        win.present()

if __name__ == "__main__":
    app = IceBgSetApp()
    app.run(sys.argv)
