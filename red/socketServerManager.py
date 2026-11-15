# Módulo red/socketServerManager.py
# Capa de red del Monitor de Cocina:
# - Inicia FastAPI + Uvicorn en un hilo daemon.
# - Gestiona socket WebSocket por cliente con handshake ESTADO_CONEXION.
# - Emite eventos JSON (NUEVA_ORDEN, ESTADO_CONEXION) a todos los
#   monitores activos.
# - Provee QR dinámico y detección de IP local para la vista de PC.
#
# Reglas de resiliencia (specTP.md):
# - La caída de red o la ausencia de monitores NO interrumpe la
#   transacción local.
# - El cliente web se reconexa automáticamente cada 3 segundos.

import asyncio
import socket
import threading
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from qrcode import make as qrcode_make
from PIL import Image

from red.static.cocina_html import COCINA_HTML

app = FastAPI(title="Plato a Plato - Monitor de Cocina")

# Estado del gestor de sockets
class SocketServerManager:
    """Gestiona el backend del monitor de cocina.

    Esta clase encapsula la lógica necesaria para exponer una vista web de
    cocina, mantener la conexión en tiempo real con los navegadores activos y
    emitir eventos cuando llega una nueva venta.

    La clase opera sobre tres capas conceptuales:
      1. servidor HTTP/WebSocket (FastAPI + Uvicorn);
      2. gestión de clientes conectados;
      3. generación de datos auxiliares (IP, URL, QR).
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Inicializa el gestor con el host y puerto del monitor.

        Args:
            host: dirección de escucha del servidor. Por defecto se usa
                0.0.0.0 para aceptar conexiones desde la red local.
            port: puerto HTTP/WebSocket del monitor. El valor esperado por la
                aplicación es 8000.
        """
        self.host = host
        self.port = port
        self._app = FastAPI()
        self._server = None
        self._server_thread = None
        self._loop = None
        self._running = False

        # Conjunto de clientes WebSocket conectados. Se usa para saber cuántos
        # clientes están activos y para enviar eventos a todos a la vez.
        self._sockets = set()
        self._sockets_lock = threading.Lock()
        self._clientes_activos = 0

        # Callback opcional que puede ser registrado por la vista desktop para
        # refrescar el estado del servidor en la UI cuando cambian los clientes.
        self._on_status_change = None

        # Identificadores de mensajes emitidos por la capa de red.
        self.NUEVA_ORDEN = "NUEVA_ORDEN"
        self.ESTADO_CONEXION = "ESTADO_CONEXION"

        # Crea las rutas GET/WebSocket del servicio.
        self._configurarRutas()

    def iniciar(self) -> dict:
        """Levanta el servicio HTTP/WebSocket del monitor en un hilo separado.

        El servidor no se ejecuta en el hilo principal de la app para evitar
        bloquear la UI de escritorio. Al iniciar, se crea un event loop propio y
        se lanza Uvicorn con la aplicación FastAPI interna.

        Returns:
            dict: respuesta normalizada con ok, mensaje y estado.
        """
        if self._running:
            return {"ok": True, "mensaje": "Servidor ya iniciado."}

        try:
            from uvicorn import Config, Server

            # Cada instancia del monitor tiene su propio loop para evitar
            # interferencias con otros hilos o con la app principal.
            self._loop = asyncio.new_event_loop()
            config = Config(
                self._app,
                host=self.host,
                port=self.port,
                loop="asyncio",
                lifespan="off",
                log_level="warning",
                log_config=None,
                access_log=False,
            )
            self._server = Server(config)

            def _ejecutar():
                """Función target del hilo del servidor.

                Ejecuta el loop de Uvicorn y deja el estado sincronizado cuando
                el servicio termina o se corta por shutdown.
                """
                asyncio.set_event_loop(self._loop)
                try:
                    self._loop.run_until_complete(self._server.serve())
                except RuntimeError as exc:
                    if "Event loop stopped before Future completed" not in str(exc):
                        raise
                finally:
                    self._server = None
                    self._running = False
                    self._server_thread = None

            self._server_thread = threading.Thread(
                target=_ejecutar, daemon=True, name="MonitorCocinaServer"
            )
            self._server_thread.start()
            self._running = True
            return {"ok": True, "mensaje": f"Servidor iniciado en {self.host}:{self.port}."}
        except Exception as err:
            self._running = False
            self._server = None
            return {"ok": False, "mensaje": f"No se pudo iniciar el servidor: {err}"}

    def detener(self) -> dict:
        """Detiene el servicio del monitor y limpia todos los clientes activos.

        El cierre es controlado: marca la señal de salida del servidor y
        finaliza el hilo de ejecución asociado. Además limpia la colección de
        sockets para dejar el estado en 0 clientes conectados.

        Returns:
            dict: respuesta con ok y mensaje del resultado.
        """
        if not self._running and self._server is None:
            return {"ok": True, "mensaje": "Servidor no estaba iniciado."}

        try:
            self._running = False
            if self._server is not None and self._loop is not None:
                try:
                    self._server.should_exit = True
                    self._server.force_exit = True
                except Exception:
                    pass
                if self._loop.is_running():
                    self._loop.call_soon_threadsafe(setattr, self._server, "should_exit", True)
            if self._server_thread is not None:
                self._server_thread.join(timeout=20)
            self._server = None
            self._server_thread = None
            self._sockets.clear()
            self._clientes_activos = 0
            return {"ok": True, "mensaje": "Servidor detenido."}
        except Exception as err:
            return {"ok": False, "mensaje": f"No se pudo detener el servidor: {err}"}

    @property
    def running(self) -> bool:
        """Indica si el servidor está actualmente activo."""
        return self._running

    @property
    def app(self):
        """Devuelve la aplicación FastAPI interna para uso externo."""
        return self._app

    @property
    def clientesActivos(self) -> int:
        """Cantidad de navegadores conectados al monitor en este momento."""
        return self._clientes_activos

    def conectar(self, websocket: WebSocket):
        """Registra un cliente WebSocket recién conectado.

        Cuando un navegador abre la página del monitor, se agrega a la colección
        de sockets activos. Entonces se actualiza el contador y se notifica a la
        UI para que muestre la cantidad de clientes conectados.
        """
        self._sockets.add(websocket)
        with self._sockets_lock:
            self._clientes_activos = len(self._sockets)
        self._notificarEstado()

    def desconectar(self, websocket: WebSocket):
        """Elimina un cliente WebSocket cuando se cierra la conexión."""
        with self._sockets_lock:
            self._sockets.discard(websocket)
            self._clientes_activos = max(0, len(self._sockets))
        self._notificarEstado()

    def _notificarEstado(self):
        """Invoca callback externo para sincronizar la vista desktop.

        La vista de escritorio registra una función que actualiza texto, QR y
        estado del servidor. Esto permite que los cambios de conectividad se
        reflejen rápidamente en la UI.
        """
        cb = self._on_status_change
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def broadcast(self, evento: str, datos: dict) -> dict:
        """Emite un mensaje JSON a todos los clientes conectados.

        Se usa para notificar a la cocina que llegó una nueva venta o que hubo un
        cambio en el estado del servidor. El payload se envía como un diccionario
        serializable en JSON.

        Args:
            evento: nombre lógico del evento.
            datos: contenido del payload asociado.

        Returns:
            dict con contador de mensajes entregados y errores si los hubo.
        """
        if not self._running or not self._sockets:
            return {"ok": True, "mensaje": "Sin sockets activos."}

        payload = {
            "evento": evento,
            "timestamp": datos.get("timestamp", self._timestamp()),
            "datos": datos,
        }

        resultado = {"enviados": 0, "error": None}
        loop = self._loop or asyncio.new_event_loop()
        futuros = []

        try:
            for socket in list(self._sockets):
                futuros.append(
                    asyncio.run_coroutine_threadsafe(
                        self._send_json(socket, payload), loop
                    )
                )

            for fut in futuros:
                try:
                    fut.result(timeout=1)
                    resultado["enviados"] += 1
                except Exception as err:
                    resultado["error"] = err

            return resultado
        except Exception as err:
            return {"ok": False, "mensaje": str(err), "enviados": 0, "error": err}

    async def _send_json(self, websocket: WebSocket, payload: dict):
        """Envía un payload JSON a un WebSocket concreto."""
        await websocket.send_json(payload)

    def _timestamp(self) -> str:
        """Genera un timestamp ISO 8601 UTC para todos los eventos emitidos."""
        try:
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return "0000-00-00T00:00:00Z"

    # ------------------------------------------------------------------
    # Rutas FastAPI
    # ------------------------------------------------------------------

    def _configurarRutas(self):
        """Define las rutas HTTP y WebSocket del monitor de cocina.

        La ruta /ws/cocina permite mantener un canal de comunicaciones en tiempo
        real con cada navegador abierto en la pantalla de cocina. La ruta /cocina
        sirve la página HTML que renderiza la interfaz del monitor.
        """

        @self._app.websocket("/ws/cocina")
        async def websocket_cocina(websocket: WebSocket):
            """Acepta un cliente WebSocket y lo mantiene vivo mientras exista.

            Al conectarse, se registra el cliente y se le envía un handshake
            inicial con el estado del servidor. Luego queda atento a mensajes del
            cliente (si existieran) hasta que la conexión se cierre.
            """
            await websocket.accept()
            self.conectar(websocket)

            handshake = {
                "estado": "CONECTADO",
                "servidor": "Plato a Plato Host",
                "clientes_activos": self._clientes_activos,
            }

            try:
                await websocket.send_json(
                    {
                        "evento": self.ESTADO_CONEXION,
                        "timestamp": self._timestamp(),
                        "datos": handshake,
                    }
                )

                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                self.desconectar(websocket)

        @self._app.get("/cocina", response_class=HTMLResponse)
        async def pagina_cocina():
            """Entrega la Web App del monitor de cocina al navegador."""
            return COCINA_HTML

    # ------------------------------------------------------------------
    # Métodos auxiliares / compatibilidad con el spec
    # ------------------------------------------------------------------

    @staticmethod
    def obtenerURLAcceso(ip: str | None = None, port: int = 8000) -> str:
        """Genera la URL del navegador para abrir el monitor.

        Esta URL es distinta de la conexión WebSocket interna. El navegador debe
        abrir la ruta HTTP /cocina, mientras que el socket de comunicación real se
        usa desde JavaScript dentro de esa página.
        """
        host = (ip or SocketServerManager.obtenerIP() or "127.0.0.1").strip()
        return f"http://{host}:{port}/cocina"

    @staticmethod
    def obtenerIP() -> str:
        """Detecta la IP local del equipo para compartir el acceso de la cocina.

        La técnica usa un socket UDP para consultar la interfaz de salida
        activa sin requerir una conexión real a internet. Si falla, devuelve
        127.0.0.1 como valor de respaldo.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
            return ip or "127.0.0.1"
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def generarQR(url: str) -> Image.Image:
        """Genera una imagen QR para la URL del monitor.

        El valor de retorno es una imagen PIL, utilizable directamente para
        mostrarse en una label o widget de escritorio. Si la librería no puede
        devolver un objeto de imagen nativo, se devuelve un fallback blanco.
        """
        qr = qrcode_make(url)
        imagen = getattr(qr, "get_image", None)
        if callable(imagen):
            qr = imagen()
        if isinstance(qr, Image.Image):
            return qr
        if hasattr(qr, "convert"):
            try:
                return qr.convert("RGB")
            except Exception:
                pass
        return Image.new("RGB", (240, 240), color="white")

