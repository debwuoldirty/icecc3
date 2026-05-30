#!/usr/bin/env python3
"""
IceWM Cursor Configurator (icecurcfg)
Soporte para temas XCursor y cursores XPM.
"""

import sys, subprocess, shutil, tarfile
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf

# ------------------------------------------------------------
# Rutas
# ------------------------------------------------------------
ICEWM_PRIV_DIR = Path.home() / ".icewm"
if not ICEWM_PRIV_DIR.exists():
    ICEWM_PRIV_DIR = Path.home() / ".config" / "icewm"

CURSORS_DIR = ICEWM_PRIV_DIR / "cursors"
PREFOVERRIDE_FILE = ICEWM_PRIV_DIR / "prefoverride"
PREFERENCES_FILE = ICEWM_PRIV_DIR / "preferences"
XRESOURCES_FILE = Path.home() / ".Xresources"
STARTUP_FILE = ICEWM_PRIV_DIR / "startup"

XCURSOR_SEARCH_DIRS = [
    Path.home() / ".icons",
    Path.home() / ".local" / "share" / "icons",
    Path("/usr/share/icons"),
]

CURSOR_NAMES = [
    ("left", "Flecha normal"), ("move", "Movimiento"), ("right", "Flecha derecha"),
    ("sizeB", "Redimensionar abajo"), ("sizeBL", "Redimensionar esquina inf. izq."),
    ("sizeBR", "Redimensionar esquina inf. der."), ("sizeL", "Redimensionar izquierda"),
    ("sizeR", "Redimensionar derecha"), ("sizeT", "Redimensionar arriba"),
    ("sizeTL", "Redimensionar esquina sup. izq."), ("sizeTR", "Redimensionar esquina sup. der."),
]

# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------
def load_pixbuf_safe(path, w, h):
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
        return pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
    except:
        return None

def is_valid_cursor_theme(d):
    return (d/"index.theme").is_file() or (d/"cursor.theme").is_file()

def scan_themes():
    themes = {}
    for d in XCURSOR_SEARCH_DIRS:
        if not d.exists(): continue
        for child in d.iterdir():
            if child.is_dir() and (child/"cursors").is_dir() and is_valid_cursor_theme(child):
                themes[child.name] = child
    return dict(sorted(themes.items()))

def get_theme_info(d):
    info = {"name": d.name, "description": ""}
    for fn in ("index.theme", "cursor.theme"):
        fp = d/fn
        if fp.exists():
            try:
                with open(fp) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("Name="): info["name"] = line.split("=",1)[1].strip()
                        elif line.startswith("Comment="): info["description"] = line.split("=",1)[1].strip()
            except: pass
            break
    return info

def write_cursor_theme(name):
    """Escribe en preferences, prefoverride y Xresources."""
    for fp in (PREFERENCES_FILE, PREFOVERRIDE_FILE):
        if not fp.exists(): continue
        lines = []
        with open(fp) as f: lines = f.readlines()
        with open(fp,'w') as f:
            found = False
            for line in lines:
                if line.strip().startswith("CursorTheme"):
                    f.write(f'CursorTheme = "{name}"\n')
                    found = True
                else: f.write(line)
            if not found: f.write(f'CursorTheme = "{name}"\n')
    lines = []
    if XRESOURCES_FILE.exists():
        with open(XRESOURCES_FILE) as f: lines = f.readlines()
    with open(XRESOURCES_FILE,'w') as f:
        found = False
        for line in lines:
            if line.startswith("Xcursor.theme:"):
                f.write(f"Xcursor.theme: {name}\n")
                found = True
            else: f.write(line)
        if not found: f.write(f"Xcursor.theme: {name}\n")
    subprocess.run(["xrdb","-merge",str(XRESOURCES_FILE)], stderr=subprocess.DEVNULL)
    subprocess.run(["xsetroot","-cursor_name","left_ptr"], stderr=subprocess.DEVNULL)

def make_permanent(theme_name, parent_window):
    """Intenta hacer permanente el tema en ~/.icewm/startup. Si falla, pide permisos elevados."""
    # Intentar escribir directamente
    try:
        if not STARTUP_FILE.exists():
            STARTUP_FILE.touch()
        lines = []
        with open(STARTUP_FILE) as f:
            lines = f.readlines()
        new_lines = []
        found_export = False
        found_xrdb = False
        for line in lines:
            if line.strip().startswith("export XCURSOR_THEME="):
                new_lines.append(f'export XCURSOR_THEME="{theme_name}"\n')
                found_export = True
            elif "xrdb -merge" in line and "Xresources" in line:
                new_lines.append('[ -f "$HOME/.Xresources" ] && xrdb -merge "$HOME/.Xresources"\n')
                found_xrdb = True
            else:
                new_lines.append(line)
        if not found_export:
            new_lines.append(f'export XCURSOR_THEME="{theme_name}"\n')
        if not found_xrdb:
            new_lines.append('[ -f "$HOME/.Xresources" ] && xrdb -merge "$HOME/.Xresources"\n')
        with open(STARTUP_FILE, 'w') as f:
            f.writelines(new_lines)
        STARTUP_FILE.chmod(0o755)
        return True
    except PermissionError:
        # Intentar con pkexec
        try:
            subprocess.run(["pkexec", "sed", "-i",
                            f"/export XCURSOR_THEME=/d; /xrdb -merge.*Xresources/d",
                            str(STARTUP_FILE)], check=True)
            subprocess.run(["pkexec", "bash", "-c",
                            f"echo 'export XCURSOR_THEME=\"{theme_name}\"' >> {STARTUP_FILE} && "
                            f"echo '[ -f \"$HOME/.Xresources\" ] && xrdb -merge \"$HOME/.Xresources\"' >> {STARTUP_FILE} && "
                            f"chmod +x {STARTUP_FILE}"], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Mostrar instrucciones manuales
            dialog = Gtk.MessageDialog(
                transient_for=parent_window,
                modal=True,
                buttons=Gtk.ButtonsType.OK,
                text=f"No se pudo modificar {STARTUP_FILE}.\n\n"
                     "Puedes hacerlo manualmente ejecutando en la terminal:\n\n"
                     f"sudo sed -i '/export XCURSOR_THEME=/d; /xrdb.*Xresources/d' {STARTUP_FILE}\n"
                     f"echo 'export XCURSOR_THEME=\"{theme_name}\"' | sudo tee -a {STARTUP_FILE}\n"
                     f"echo '[ -f \"$HOME/.Xresources\" ] && xrdb -merge \"$HOME/.Xresources\"' | sudo tee -a {STARTUP_FILE}\n"
                     f"sudo chmod +x {STARTUP_FILE}\n\n"
                     "O simplemente edita el archivo con sudo nano y añade esas líneas."
            )
            dialog.present()
            return False

def restart_icewm():
    try:
        subprocess.run(["pkill","-1","icewm"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

# ------------------------------------------------------------
# Ventana principal (el resto del código se mantiene igual, solo cambia on_apply_theme)
# ------------------------------------------------------------
class CursorConfigWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("IceWM Cursor Configurator")
        self.set_default_size(750, 520)

        self.cursor_data = {name: None for name,_ in CURSOR_NAMES}
        self.themes = scan_themes()

        notebook = Gtk.Notebook()
        self.set_child(notebook)

        # ================== Pestaña 1: Temas XCursor ==================
        page1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        page1.set_margin_top(10); page1.set_margin_bottom(10)
        page1.set_margin_start(10); page1.set_margin_end(10)
        notebook.append_page(page1, Gtk.Label(label="Temas XCursor"))

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        left.set_size_request(220, -1)
        page1.append(left)

        left.append(Gtk.Label(label="Temas instalados:"))
        scrolled = Gtk.ScrolledWindow(); scrolled.set_vexpand(True)
        self.theme_listbox = Gtk.ListBox()
        self.theme_listbox.connect("row-selected", self.on_theme_selected)
        scrolled.set_child(self.theme_listbox)
        left.append(scrolled)

        btn_refresh = Gtk.Button.new_with_label("Refrescar lista")
        btn_refresh.connect("clicked", self.refresh_themes)
        left.append(btn_refresh)

        btn_install = Gtk.Button.new_with_label("Instalar tema...")
        btn_install.connect("clicked", self.on_install_theme)
        left.append(btn_install)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right.set_hexpand(True)
        page1.append(right)

        self.theme_name_label = Gtk.Label()
        self.theme_name_label.set_markup("<b>Seleccione un tema</b>")
        right.append(self.theme_name_label)

        self.theme_desc_label = Gtk.Label(wrap=True)
        right.append(self.theme_desc_label)

        btn_apply = Gtk.Button.new_with_label("Aplicar tema")
        btn_apply.set_hexpand(True)
        btn_apply.connect("clicked", self.on_apply_theme)
        right.append(btn_apply)

        btn_restart = Gtk.Button.new_with_label("Reiniciar IceWM")
        btn_restart.connect("clicked", lambda b: restart_icewm())
        right.append(btn_restart)

        self.lbl_note = Gtk.Label(wrap=True, margin_top=10)
        self.lbl_note.set_markup("<i>Nota: Firefox y otras apps pueden necesitar reinicio manual para mostrar el nuevo cursor.</i>")
        right.append(self.lbl_note)

        self.status_label = Gtk.Label()
        right.append(self.status_label)

        # ================== Pestaña 2: Cursores XPM ==================
        page2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page2.set_margin_top(10); page2.set_margin_bottom(10)
        page2.set_margin_start(10); page2.set_margin_end(10)
        notebook.append_page(page2, Gtk.Label(label="Cursores XPM"))

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        page2.append(hbox)

        left2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        left2.set_size_request(340, -1)
        hbox.append(left2)

        left2.append(Gtk.Label(label="Directorio:"))
        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        left2.append(dir_box)
        self.entry_dir = Gtk.Entry(text=str(CURSORS_DIR), editable=False)
        dir_box.append(self.entry_dir)
        btn_open = Gtk.Button.new_with_label("Abrir")
        btn_open.connect("clicked", lambda b: subprocess.Popen(["xdg-open", str(CURSORS_DIR)]))
        dir_box.append(btn_open)

        scrolled2 = Gtk.ScrolledWindow(); scrolled2.set_vexpand(True)
        self.xpm_listbox = Gtk.ListBox()
        self.xpm_listbox.connect("row-selected", self.on_xpm_selected)
        scrolled2.set_child(self.xpm_listbox)
        left2.append(scrolled2)

        btn_import = Gtk.Button.new_with_label("Importar carpeta...")
        btn_import.connect("clicked", self.on_import_folder)
        left2.append(btn_import)

        right2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right2.set_hexpand(True)
        hbox.append(right2)

        frame = Gtk.Frame(label="Vista previa"); right2.append(frame)
        self.preview_picture = Gtk.Picture()
        self.preview_picture.set_size_request(128,128)
        frame.set_child(self.preview_picture)

        self.cursor_name_label = Gtk.Label(label="Selecciona un cursor")
        right2.append(self.cursor_name_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        right2.append(btn_box)
        btn_browse = Gtk.Button.new_with_label("Examinar...")
        btn_browse.connect("clicked", self.on_browse_xpm)
        btn_box.append(btn_browse)
        btn_default = Gtk.Button.new_with_label("Por defecto")
        btn_default.connect("clicked", self.on_default_xpm)
        btn_box.append(btn_default)

        btn_save = Gtk.Button.new_with_label("Guardar todo")
        btn_save.set_hexpand(True)
        btn_save.connect("clicked", self.on_save_xpm)
        right2.append(btn_save)

        # ── Cerrar ──
        btn_close = Gtk.Button.new_with_label("Cerrar")
        btn_close.connect("clicked", lambda *a: self.close())
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(vbox_main)
        vbox_main.append(notebook)
        hbox_close = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox_close.set_halign(Gtk.Align.END)
        hbox_close.set_margin_top(5); hbox_close.set_margin_bottom(5)
        hbox_close.set_margin_end(10)
        hbox_close.append(btn_close)
        vbox_main.append(hbox_close)

        self.load_xpm_cursors()
        self.populate_xpm_list()
        self.populate_theme_list()

    # ================== Temas XCursor ==================
    def refresh_themes(self, *args):
        self.themes = scan_themes()
        self.populate_theme_list()

    def populate_theme_list(self):
        self.theme_listbox.remove_all()
        for name in self.themes:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=name, xalign=0, margin_start=5, margin_top=3, margin_bottom=3))
            self.theme_listbox.append(row)

    def on_theme_selected(self, listbox, row):
        if row is None: return
        idx = row.get_index()
        keys = list(self.themes.keys())
        if idx < len(keys):
            info = get_theme_info(self.themes[keys[idx]])
            self.theme_name_label.set_markup(f"<b>{info['name']}</b>")
            self.theme_desc_label.set_text(info["description"])

    def on_apply_theme(self, button):
        row = self.theme_listbox.get_selected_row()
        if not row: return
        name = list(self.themes.keys())[row.get_index()]
        write_cursor_theme(name)
        self.status_label.set_text(f"Tema '{name}' aplicado temporalmente.")

        dlg = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"¿Desea hacer permanente el tema '{name}'?\n\nSe añadirá a {STARTUP_FILE}.\nSi no tienes permisos, se pedirá la contraseña."
        )
        dlg.connect("response", self._on_permanent_dialog_response, name)
        dlg.present()

    def _on_permanent_dialog_response(self, dialog, response, name):
        if response == Gtk.ResponseType.YES:
            success = make_permanent(name, self)
            if success:
                self.status_label.set_text(f"Tema '{name}' guardado permanentemente. Reinicie IceWM o la sesión.")
            else:
                self.status_label.set_text("No se pudo hacer permanente. Revisa los permisos.")
        else:
            self.status_label.set_text(f"Tema '{name}' aplicado solo esta sesión. Use 'Reiniciar IceWM' para actualizar ventanas.")
        dialog.destroy()

    def on_install_theme(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar archivo comprimido (tar.gz/tar.xz/tar.bz2)")
        filter_tar = Gtk.FileFilter(); filter_tar.set_name("Comprimidos")
        filter_tar.add_pattern("*.tar.gz"); filter_tar.add_pattern("*.tar.xz"); filter_tar.add_pattern("*.tar.bz2")
        model = Gio.ListStore.new(Gtk.FileFilter); model.append(filter_tar)
        dialog.set_filters(model)
        dialog.open(self, None, self._on_install_finish)

    def _on_install_finish(self, dialog, result):
        try:
            f = dialog.open_finish(result)
            if f:
                dest = Path.home() / ".local" / "share" / "icons"
                dest.mkdir(parents=True, exist_ok=True)
                with tarfile.open(Path(f.get_path())) as tar:
                    tar.extractall(dest)
                self.refresh_themes()
                Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK,
                                  text="Tema instalado.").present()
        except Exception as e:
            Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK,
                              text=f"Error: {e}").present()

    # ================== Cursores XPM (sin cambios) ==================
    def load_xpm_cursors(self):
        self.cursor_data = {name: None for name,_ in CURSOR_NAMES}
        if CURSORS_DIR.exists():
            for f in CURSORS_DIR.iterdir():
                if f.suffix.lower() in (".xpm", ".png"):
                    stem = f.stem
                    if stem in self.cursor_data: self.cursor_data[stem] = f

    def populate_xpm_list(self):
        self.xpm_listbox.remove_all()
        for name, desc in CURSOR_NAMES:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_top(3); hbox.set_margin_bottom(3)
            hbox.set_margin_start(5); hbox.set_margin_end(5)
            thumb = Gtk.Picture(); thumb.set_size_request(24,24)
            path = self.cursor_data.get(name)
            if path:
                try: thumb.set_paintable(Gdk.Texture.new_from_filename(str(path)))
                except: pass
            hbox.append(thumb)
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            vbox.append(Gtk.Label(label=f"<b>{name}</b>", use_markup=True, xalign=0))
            vbox.append(Gtk.Label(label=desc, xalign=0))
            hbox.append(vbox)
            status = "Personalizado" if path else "Por defecto"
            hbox.append(Gtk.Label(label=status, xalign=1, hexpand=True))
            row.set_child(hbox)
            self.xpm_listbox.append(row)

    def get_selected_xpm_name(self):
        row = self.xpm_listbox.get_selected_row()
        if row is None: return None
        idx = row.get_index()
        return CURSOR_NAMES[idx][0] if idx < len(CURSOR_NAMES) else None

    def on_xpm_selected(self, listbox, row):
        if row is None: return
        name = self.get_selected_xpm_name()
        if not name: return
        path = self.cursor_data.get(name)
        if path:
            try: self.preview_picture.set_paintable(Gdk.Texture.new_from_filename(str(path)))
            except: pass
        else:
            self.preview_picture.set_filename(None)
        for n, desc in CURSOR_NAMES:
            if n == name:
                self.cursor_name_label.set_text(f"{n} - {desc}")
                break

    def on_browse_xpm(self, button):
        name = self.get_selected_xpm_name()
        if not name: return
        dialog = Gtk.FileDialog()
        dialog.set_title(f"Seleccionar imagen para {name}")
        filter_img = Gtk.FileFilter(); filter_img.set_name("Imágenes (*.xpm, *.png)")
        filter_img.add_pattern("*.xpm"); filter_img.add_pattern("*.png")
        model = Gio.ListStore.new(Gtk.FileFilter); model.append(filter_img)
        dialog.set_filters(model)
        dialog.open(self, None, lambda d, r: self._on_xpm_file_selected(d, r, name))

    def _on_xpm_file_selected(self, dialog, result, name):
        try:
            f = dialog.open_finish(result)
            if f:
                self.cursor_data[name] = Path(f.get_path())
                self.populate_xpm_list()
        except: pass

    def on_default_xpm(self, button):
        name = self.get_selected_xpm_name()
        if name: self.cursor_data[name] = None; self.populate_xpm_list()

    def on_save_xpm(self, button):
        CURSORS_DIR.mkdir(parents=True, exist_ok=True)
        for name, path in self.cursor_data.items():
            dest = CURSORS_DIR / f"{name}.xpm"
            if path is None: dest.unlink(missing_ok=True)
            else: shutil.copy2(path, dest)
        restart_icewm()
        Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK,
                          text="Cursores guardados e IceWM reiniciado.").present()

    def on_import_folder(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar carpeta con cursores XPM")
        dialog.select_folder(self, None, self._on_import_folder_selected)

    def _on_import_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                folder_path = Path(folder.get_path())
                for f in folder_path.iterdir():
                    if f.suffix.lower() in (".xpm", ".png"):
                        stem = f.stem
                        if stem in self.cursor_data: self.cursor_data[stem] = f
                self.populate_xpm_list()
        except: pass

# ------------------------------------------------------------
# App
# ------------------------------------------------------------
class CursorConfigApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.icecc.icecurcfg")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = CursorConfigWindow(application=app)
        win.present()

if __name__ == "__main__":
    print("Iniciando configurador de cursores...")
    app = CursorConfigApp()
    app.run(sys.argv)
