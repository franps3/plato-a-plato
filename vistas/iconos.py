# Módulo iconos.py (Agente 2 - Vista)
# Genera con Pillow los íconos PNG usados por las vistas (casa, lupa, carrito,
# más, menos, cerrar y configuración). Los dibuja de forma vectorial y los
# guarda en /vistas/recursos para no depender de archivos externos ni de
# íconos de fuentes del sistema.
#
# Uso:
#   from vistas.iconos import obtenerIconos
#   iconos = obtenerIconos()   # {nombre: ruta_png}
#
# Si los PNG ya existen en /vistas/recursos NO se regeneran (idempotente).

import math
import os

from PIL import Image, ImageDraw

# Carpeta destino de los íconos generados.
DIRECTORIO_RECURSOS = os.path.join(os.path.dirname(__file__), "recursos")

# Factor de supermuestreo para dibujar con bordes suaves (antialiasing).
_ESCALA = 4

# Colores por defecto de cada ícono (los diseños los muestran oscuros sobre
# botones claros, salvo los símbolos +, -, x que van en gris oscuro).
COLOR_OSCURO = (51, 51, 61, 255)    # #33333D
COLOR_GRIS = (90, 90, 105, 255)     # #5A5A69


def _lienzo(tamano, escala=_ESCALA):
    """Crea un lienzo RGBA transparente y su ImageDraw ampliados.

    Retorna (imagen, dibujo) al tamaño final (imagen) y un dibujo sobre una
    imagen temporal ampliada por 'escala' para dibujar con precisión.
    """
    actual = tamano * escala
    alto = Image.new("RGBA", (actual, actual), (0, 0, 0, 0))
    return alto, ImageDraw.Draw(alto), actual


def _finalizar(alto, tamano, escala=_ESCALA):
    """Reduce la imagen ampliada al tamaño final con suavizado (LANCZOS)."""
    return alto.resize((tamano, tamano), Image.LANCZOS)


def _dibujarCasa(tamano=48, color=COLOR_OSCURO):
    """Dibuja un ícono de casa (home): techo triangular y cuerpo rectangular."""
    alto, dibujo, actual = _lienzo(tamano)
    # Proporciones relativas al lienzo.
    ancho = actual
    # Techo: triángulo que ocupa la mitad superior.
    dibujo.polygon(
        [
            (ancho * 0.5, ancho * 0.10),
            (ancho * 0.92, ancho * 0.46),
            (ancho * 0.08, ancho * 0.46),
        ],
        fill=color,
    )
    # Cuerpo de la casa.
    dibujo.rectangle(
        [ancho * 0.22, ancho * 0.44, ancho * 0.78, ancho * 0.88],
        fill=color,
    )
    # Puerta (recorte transparente).
    dibujo.rectangle(
        [ancho * 0.42, ancho * 0.62, ancho * 0.58, ancho * 0.88],
        fill=(0, 0, 0, 0),
    )
    return _finalizar(alto, tamano)


def _dibujarLupa(tamano=28, color=COLOR_OSCURO):
    """Dibuja una lupa (búsqueda): aro + mango diagonal."""
    alto, dibujo, actual = _lienzo(tamano)
    ancho = actual
    grosor = max(2, int(ancho * 0.10))
    # Aro de la lupa.
    r = ancho * 0.26
    cx, cy = ancho * 0.42, ancho * 0.42
    dibujo.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=color,
        width=grosor,
    )
    # Mango diagonal.
    dibujo.line(
        [(cx + r * 0.72, cy + r * 0.72), (ancho * 0.86, ancho * 0.86)],
        fill=color,
        width=grosor,
    )
    return _finalizar(alto, tamano)


def _dibujarCarrito(tamano=36, color=COLOR_OSCURO):
    """Dibuja un carrito de compras: canasto, mango y dos ruedas."""
    alto, dibujo, actual = _lienzo(tamano)
    ancho = actual
    grosor = max(2, int(ancho * 0.07))
    # Mango curvo (línea en L).
    dibujo.line(
        [(ancho * 0.08, ancho * 0.16), (ancho * 0.24, ancho * 0.16)],
        fill=color,
        width=grosor,
    )
    dibujo.line(
        [(ancho * 0.24, ancho * 0.16), (ancho * 0.36, ancho * 0.62)],
        fill=color,
        width=grosor,
    )
    # Canasto (trapecial).
    dibujo.line(
        [(ancho * 0.30, ancho * 0.34), (ancho * 0.90, ancho * 0.34)],
        fill=color,
        width=grosor,
    )
    dibujo.line(
        [(ancho * 0.90, ancho * 0.34), (ancho * 0.78, ancho * 0.62)],
        fill=color,
        width=grosor,
    )
    dibujo.line(
        [(ancho * 0.78, ancho * 0.62), (ancho * 0.36, ancho * 0.62)],
        fill=color,
        width=grosor,
    )
    # Ruedas.
    rr = ancho * 0.06
    for cx in (ancho * 0.44, ancho * 0.76):
        cy = ancho * 0.80
        dibujo.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color)
    return _finalizar(alto, tamano)


def _dibujarMas(tamano=22, color=COLOR_GRIS):
    """Dibuja un signo más (+)."""
    alto, dibujo, actual = _lienzo(tamano)
    ancho = actual
    grosor = max(2, int(ancho * 0.16))
    dibujo.line(
        [(ancho * 0.5, ancho * 0.2), (ancho * 0.5, ancho * 0.8)],
        fill=color,
        width=grosor,
    )
    dibujo.line(
        [(ancho * 0.2, ancho * 0.5), (ancho * 0.8, ancho * 0.5)],
        fill=color,
        width=grosor,
    )
    return _finalizar(alto, tamano)


def _dibujarMenos(tamano=22, color=COLOR_GRIS):
    """Dibuja un signo menos (-)."""
    alto, dibujo, actual = _lienzo(tamano)
    ancho = actual
    grosor = max(2, int(ancho * 0.16))
    dibujo.line(
        [(ancho * 0.2, ancho * 0.5), (ancho * 0.8, ancho * 0.5)],
        fill=color,
        width=grosor,
    )
    return _finalizar(alto, tamano)


def _dibujarCerrar(tamano=20, color=COLOR_GRIS):
    """Dibuja una cruz (x) para cerrar/eliminar."""
    alto, dibujo, actual = _lienzo(tamano)
    ancho = actual
    grosor = max(2, int(ancho * 0.16))
    dibujo.line(
        [(ancho * 0.24, ancho * 0.24), (ancho * 0.76, ancho * 0.76)],
        fill=color,
        width=grosor,
    )
    dibujo.line(
        [(ancho * 0.76, ancho * 0.24), (ancho * 0.24, ancho * 0.76)],
        fill=color,
        width=grosor,
    )
    return _finalizar(alto, tamano)


def _dibujarConfiguracion(tamano=24, color=COLOR_GRIS):
    """Dibuja una rueda dentada (engranaje) para configurar un producto."""
    alto, dibujo, actual = _lienzo(tamano)
    ancho = actual
    cx = cy = ancho * 0.5
    radio = ancho * 0.33           # radio del cuerpo de la rueda
    radioExterior = ancho * 0.46   # hasta la punta de los dientes

    def _punto(angulo, radioLectura):
        """Devuelve (x, y) de un punto a 'radio' del centro en 'angulo'."""
        return (
            cx + math.cos(angulo) * radioLectura,
            cy + math.sin(angulo) * radioLectura,
        )

    # Dientes: 8 triángulos distribuidos alrededor de la circunferencia.
    dientes = 8
    for i in range(dientes):
        ang = 2 * math.pi * i / dientes
        paso = 2 * math.pi / dientes
        base1 = _punto(ang - paso * 0.18, radio)
        base2 = _punto(ang + paso * 0.18, radio)
        punta = _punto(ang, radioExterior)
        dibujo.polygon([base1, base2, punta], fill=color)

    # Cuerpo de la rueda (tapa la base de los dientes).
    dibujo.ellipse(
        [cx - radio, cy - radio, cx + radio, cy + radio],
        fill=color,
    )
    # Hueco central (recorte transparente).
    hueco = ancho * 0.13
    dibujo.ellipse(
        [cx - hueco, cy - hueco, cx + hueco, cy + hueco],
        fill=(0, 0, 0, 0),
    )
    return _finalizar(alto, tamano)


# Definición de íconos: nombre -> (función de dibujo, tamaño, nombre de archivo)
_ICONOS = {
    "casa": (_dibujarCasa, 48, "casa.png"),
    "lupa": (_dibujarLupa, 28, "lupa.png"),
    "carrito": (_dibujarCarrito, 36, "carrito.png"),
    "mas": (_dibujarMas, 22, "mas.png"),
    "menos": (_dibujarMenos, 22, "menos.png"),
    "cerrar": (_dibujarCerrar, 20, "cerrar.png"),
    "configuracion": (_dibujarConfiguracion, 24, "configuracion.png"),
}


def generarIconos(forzar=False):
    """Genera los PNG de íconos en /vistas/recursos si no existen.

    Args:
        forzar: si es True, regenera los PNG aunque ya existan.
    """
    os.makedirs(DIRECTORIO_RECURSOS, exist_ok=True)
    for nombre, (dibujar, tamano, archivo) in _ICONOS.items():
        ruta = os.path.join(DIRECTORIO_RECURSOS, archivo)
        if forzar or not os.path.exists(ruta):
            imagen = dibujar(tamano)
            imagen.save(ruta, "PNG")


def obtenerIconos():
    """Garantiza la existencia de los íconos y devuelve {nombre: ruta}.

    La Vista usa este diccionario para cargar los CTkImage. Es idempotente:
    sólo dibuja los que faltan.
    """
    generarIconos()
    return {
        nombre: os.path.join(DIRECTORIO_RECURSOS, archivo)
        for nombre, (_, _, archivo) in _ICONOS.items()
    }