# Módulo estilos.py (Agente 2 - Vista)
# Paleta de colores, tipografías y constantes visuales compartidas por todas
# las vistas de la aplicación "Plato a Plato".
#
# IMPORTANTE: los valores provienen de los diseños PNG entregados por el
# usuario (paleta violácea). Si un diseño futuro los cambia, se ajustan acá
# una sola vez y todas las vistas lo heredan.

# ---------------------------------------------------------------------------
# Colores de fondo
# ---------------------------------------------------------------------------
FONDO = "#5C5C70"            # fondo general de la aplicación
FONDO_PANEL = "#6E6E82"      # paneles y contenedores
FONDO_BARRA = "#5C5C70"      # barra superior de navegación

# ---------------------------------------------------------------------------
# Filas / tarjetas de producto
# ---------------------------------------------------------------------------
FILA = "#6E6E82"             # fondo de la tarjeta de producto
FILA_HOVER = "#7A7A90"       # fondo al pasar el mouse
BADGE_STOCK = "#7C7C90"      # recuadro del número de stock

# ---------------------------------------------------------------------------
# Botones de la barra superior
# ---------------------------------------------------------------------------
BOTON_BARRA = "#6E6E82"
BOTON_BARRA_HOVER = "#7E7E94"
BOTON_BARRA_ACTIVO = "#83839A"   # botón de la vista actual

# ---------------------------------------------------------------------------
# Botones claros (íconos sobre fondo claro)
# ---------------------------------------------------------------------------
BOTON_CLARO = "#8F8F8F"
BOTON_CLARO_HOVER = "#CFCFDA"

# ---------------------------------------------------------------------------
# Pastillas de precio y campos de entrada
# ---------------------------------------------------------------------------
PILL = "#FFFFFF"             # pastilla blanca del precio
ENTRADA = "#FFFFFF"          # barra de búsqueda / campos de texto
ENTRADA_TEXTO = "#33333D"    # texto escrito en campos claros

# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------
TEXTO_CLARO = "#FFFFFF"
TEXTO_OSCURO = "#33333D"
TEXTO_TENUE = "#C8C8D6"

# ---------------------------------------------------------------------------
# Barras de desplazamiento
# ---------------------------------------------------------------------------
SCROLL = "#8A8AA0"
SCROLL_HOVER = "#A0A0B4"

# ---------------------------------------------------------------------------
# Varios
# ---------------------------------------------------------------------------
ACENTO = "#8A8AA0"
RADIO = 12                   # radio de esquinas estándar
RADIO_PILL = 18              # radio de las pastillas de precio

# ---------------------------------------------------------------------------
# Tipografías (Segoe UI disponible en Windows)
# ---------------------------------------------------------------------------
FUENTE = "Segoe UI"
F_TITULO = (FUENTE, 26, "bold")
F_SUBTITULO = (FUENTE, 18, "bold")
F_NORMAL = (FUENTE, 14)
F_BOLD = (FUENTE, 14, "bold")
F_PEQUENA = (FUENTE, 12)
F_PRECIO = (FUENTE, 14, "bold")