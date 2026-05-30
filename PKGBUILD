pkgname=icecc3
pkgver=1.0
pkgrel=2
pkgdesc="Centro de Control para IceWM (herramientas gráficas de configuración)"
arch=('any')
license=('GPL')
depends=('python' 'gtk4' 'python-gobject')
source=('icecc3.tar.gz')
sha256sums=('SKIP')

package() {
    mkdir -p "$pkgdir/opt/icecc3"
    cp -r "$srcdir/icecc3/"* "$pkgdir/opt/icecc3/"
    
    # Script para agregar al menú
    cat > "$pkgdir/opt/icecc3/icecc-add-menu" << 'SCRIPT'
#!/bin/bash
MENU_FILE="$HOME/.icewm/menu"
if [ -f "$MENU_FILE" ]; then
    if ! grep -q "IceWM Control Center" "$MENU_FILE"; then
        echo 'prog "IceWM Control Center" /usr/share/icewm/icewm.png /opt/icecc3/icecc3.py' >> "$MENU_FILE"
        echo "Entrada añadida al menú de IceWM."
    else
        echo "La entrada ya existe en el menú."
    fi
else
    echo "No se encontró ~/.icewm/menu. Copia el menú de ejemplo: cp /usr/share/icewm/menu ~/.icewm/menu"
fi
SCRIPT
    chmod +x "$pkgdir/opt/icecc3/icecc-add-menu"

    # Archivo .desktop
    mkdir -p "$pkgdir/usr/share/applications"
    cat > "$pkgdir/usr/share/applications/icecc.desktop" << EOF
[Desktop Entry]
Name=IceWM Control Center
Comment=Configura IceWM gráficamente
Exec=/opt/icecc3/icecc3.py
Icon=/usr/share/icewm/icewm.png
Terminal=false
Type=Application
Categories=Settings;DesktopSettings;
EOF
}

post_install() {
    if [ -n "$SUDO_USER" ]; then
        su "$SUDO_USER" -c "/opt/icecc3/icecc-add-menu"
    else
        echo "Para añadir al menú de IceWM, ejecuta: /opt/icecc3/icecc-add-menu"
    fi
}