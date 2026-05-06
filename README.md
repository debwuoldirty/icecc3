# 🧊 IceWM Control Center 3 (IceCC3)

![Licencia](https://img.shields.io/badge/licencia-GPLv2-blue.svg)
![Plataforma](https://img.shields.io/badge/plataforma-Linux-lightgrey)
![Gestor de ventanas](https://img.shields.io/badge/gestor-IceWM-5b8cc4)
![Versión](https://img.shields.io/badge/versión-1.0.3-green)

**IceWM Control Center** es una suite de herramientas gráficas para configurar el gestor de ventanas [IceWM](https://ice-wm.org/) sin necesidad de editar archivos manualmente.  
Basado en el proyecto original de **Vadim A. Khohlov** (2002‑2004), ahora reescrito en Python 3 y GTK 4 para las distribuciones modernas.

>  Cambia temas, fondos, cursores, atajos, menús, barras y más, todo desde una sola ventana.

---

Panel principal de IceCC3

---

##  Herramientas incluidas

| Icono | Herramienta | Descripción |
|:---:|---|:---|
 **Editor de menús** | Añade, elimina y reordena aplicaciones en el menú de IceWM. |
 **Editor de la barra de herramientas** | Administra los lanzadores de la barra superior (prog, iconos, comandos). |
 **Configurar barra** | Ajusta posición, tamaño, doble altura y elementos visibles de la barra de tareas. |
 **Editor de teclas** | Define atajos de teclado (Ctrl+Alt+...). |
 **Cambiar tema** | Explora y aplica temas con vista previa, autor y descripción. |
 **Fondo de escritorio** | Selecciona imágenes de cualquier carpeta y aplícalas al instante. |
 **Sonido** | Asigna archivos WAV a eventos de IceWM (inicio, cierre, cambio de escritorio…). |
 **Cursores** | Cambia el tema del cursor (XCursor) e instala nuevos temas desde `.tar.gz`. |
 **Editar inicio (startup)** | Editor integrado de `~/.icewm/startup` con soporte para `pkexec` (contraseña). |

---

## Dependencias

- `python` (3.6+)
- `gtk4`
- `python-gobject`
- `polkit` (opcional, para guardar archivos protegidos con contraseña)

En Arch Linux se instalan automáticamente con el paquete AUR.

---

## Instalación

### Desde AUR (recomendado para Arch Linux)
```bash
yay -S icecc3

## Desde GitHub (compilación manual)

git clone https://github.com/debwuoldirty/icecc3
cd icecc3
makepkg -si

######


## Licencia

Este proyecto se distribuye bajo la licencia GNU General Public License v2.0 (GPL‑2.0+).
Véase el archivo LICENSE para más detalles.


## Créditos

Vadim A. Khohlov – creador del IceWM Control Center original (2002‑2004).
debwuoldirty – adaptación a Python 3 + GTK4, mantenimiento y empaquetado para Arch Linux.



