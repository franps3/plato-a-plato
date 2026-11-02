# Módulo compilar.py (Build)
# Empaqueta la aplicación "Plato a Plato" en un ejecutable portable con
# PyInstaller (stack definido en docs/AGENTS.md).
#
# Uso:
#   python compilar.py            -> dist/PlatoAPlato.exe (un solo archivo)
#   python compilar.py --onedir   -> dist/PlatoAPlato/ (carpeta: arranca más rápido)
#
# Qué arma el build:
#   * --windowed: sin consola detrás (los errores quedan en plato.log).
#   * --add-data vistas/recursos: los PNG de íconos de las vistas.
#   * --add-data logo.png: logo del sistema disponible en runtime.
#   * --collect-all customtkinter y CTkMessagebox: sus temas y datos internos.
#   * Ícono del .exe generado al vuelo desde logo.png; si la conversión
#     falla, se compila igual sin ícono (el build no se corta).
#
# Portabilidad: al abrir el binario, bd.db / plato.log / bd_respaldo.db se
# crean en la MISMA carpeta del .exe (ver CARPETA_BASE en acceso/mainDAO.py),
# así el ejecutable viaja con sus datos: copiá el .exe y listo.
#
# Los artefactos (build/, dist/, *.spec) están ignorados por git.

import os
import shutil
import subprocess
import sys
import tempfile

CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
NOMBRE = "PlatoAPlato"                              # nombre del .exe
PUNTO_ENTRADA = "main.py"                           # script de arranque
ICONO_FUENTE = os.path.join(CARPETA_BASE, "vistas", "recursos", "logo.png")  # logo del sistema


def _crearIcono(carpetaTemporal):
    """Genera el .ico del ejecutable desde el PNG de la casa.

    Retorna la ruta del .ico o None si no se pudo generar (el build sigue).
    """
    try:
        from PIL import Image

        if not os.path.exists(ICONO_FUENTE):
            return None
        rutaIco = os.path.join(carpetaTemporal, NOMBRE + ".ico")
        imagen = Image.open(ICONO_FUENTE).convert("RGBA")
        imagen.save(
            rutaIco, "ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                   (128, 128), (256, 256)],
        )
        return rutaIco
    except Exception as err:   # Build "best effort": nunca corta el empaquetado.
        print("Aviso: no se pudo generar el icono (%s)." % err)
        print("Se compila sin icono personalizado.")
        return None


def _ordenPyInstaller(icono, unSoloArchivo):
    """Arma la lista de argumentos con la que se invoca a PyInstaller."""
    orden = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",              # Sobrescribe dist/build sin preguntar.
        "--clean",                  # Descarta cachés previos.
        "--windowed",               # App de escritorio: sin consola.
        "--name", NOMBRE,
        # PNG de íconos de las vistas (se generan en runtime si faltan).
        "--add-data",
        os.path.join(CARPETA_BASE, "vistas", "recursos")
        + os.pathsep
        + os.path.join("vistas", "recursos"),
        # Logo del sistema (disponible en runtime junto al ejecutable).
        "--add-data",
        os.path.join(CARPETA_BASE, "vistas", "recursos", "logo.png")
        + os.pathsep
        + os.path.join("vistas", "recursos"),
        # Temas y datos internos de las librerías de UI.
        "--collect-all", "customtkinter",
        "--collect-all", "CTkMessagebox",
        PUNTO_ENTRADA,
    ]
    # La variante de salida va antes del punto de entrada.
    orden.insert(-1, "--onefile" if unSoloArchivo else "--onedir")
    if icono is not None:
        orden.insert(-1, "--icon")
        orden.insert(-1, icono)
    return orden


def main():
    """Compila el ejecutable portable y reporta dónde quedó."""
    unSoloArchivo = "--onedir" not in sys.argv

    # El .ico se genera en una carpeta temporal: no ensucia el repo.
    carpetaTemporal = tempfile.mkdtemp(prefix="platoIco_")
    try:
        icono = _crearIcono(carpetaTemporal)
        orden = _ordenPyInstaller(icono, unSoloArchivo)
        print("Compilando " + NOMBRE + "...")
        print("Orden: " + " ".join(orden))
        subprocess.run(orden, check=True, cwd=CARPETA_BASE)
    except subprocess.CalledProcessError as err:
        print("Error de PyInstaller (código %s)." % err.returncode)
        print("Revisá que PyInstaller esté instalado: pip install pyinstaller")
        return 1
    finally:
        shutil.rmtree(carpetaTemporal, ignore_errors=True)

    # Ruta final del artefacto generado.
    if unSoloArchivo:
        destino = os.path.join(
            "dist", NOMBRE + (".exe" if os.name == "nt" else "")
        )
    else:
        destino = os.path.join("dist", NOMBRE)
    print("Listo: " + os.path.abspath(destino))
    print("Los datos (bd.db, plato.log) se crean junto al ejecutable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())