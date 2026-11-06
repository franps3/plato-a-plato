# Módulo red/static/cocina_html.py
# Fuente de la Web App de cocina (cliente monitor) del módulo
# Monitor de Cocina (specTP.md).
#
# La app recibe eventos WebSocket (NUEVA_ORDEN, ESTADO_CONEXION) y
# muestra la tarjeta del pedido en tiempo real. Incluye:
# - Sonido auditivo (Web Audio API) al recibir una nueva orden.
# - Estado de "En preparación" / "Listo" por tarjeta.
# - Reconexión automática cada 3 segundos tras caída de conexión.

COOKA_HTML = r"""

