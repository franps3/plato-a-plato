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
    """Gestiona el servidor asíncrono y la emisión de tramas JSON."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self._app = FastAPI()
        self._server = None
        self._server_thread = None
        self._loop = None
        self._running = False

        self._sockets = set()
        self._sockets_lock = threading.Lock()
        self._clientes_activos = 0
        self._on_status_change = None

        self.NUEVA_ORDEN = "NUEVA_ORDEN"
        self.ESTADO_CONEXION = "ESTADO_CONEXION"

        self._configurarRutas()

    def iniciar(self) -> dict:
        if self._running:
            return {"ok": True, "mensaje": "Servidor ya iniciado."}

        try:
            from uvicorn import Config, Server

            self._loop = asyncio.new_event_loop()
            config = Config(
                self._app,
                host=self.host,
                port=self.port,
                loop="asyncio",
                lifespan="off",
                log_level="warning",
            )
            self._server = Server(config)

            def _ejecutar():
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
        return self._running

    @property
    def app(self):
        return self._app

    @property
    def clientesActivos(self) -> int:
        return self._clientes_activos

    def conectar(self, websocket: WebSocket):
        self._sockets.add(websocket)
        with self._sockets_lock:
            self._clientes_activos = len(self._sockets)
        self._notificarEstado()

    def desconectar(self, websocket: WebSocket):
        with self._sockets_lock:
            self._sockets.discard(websocket)
            self._clientes_activos = max(0, len(self._sockets))
        self._notificarEstado()

    def _notificarEstado(self):
        cb = self._on_status_change
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def broadcast(self, evento: str, datos: dict) -> dict:
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
        await websocket.send_json(payload)

    def _timestamp(self) -> str:
        try:
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return "0000-00-00T00:00:00Z"

    # ------------------------------------------------------------------
    # Rutas FastAPI
    # ------------------------------------------------------------------

    def _configurarRutas(self):
        @self._app.websocket("/ws/cocina")
        async def websocket_cocina(websocket: WebSocket):
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
            """Entrega la Web App de cocina (cliente monitor)."""
            return COCINA_HTML

    # ------------------------------------------------------------------
    # Métodos auxiliares / compatibilidad con el spec
    # ------------------------------------------------------------------

    @staticmethod
    def obtenerURLAcceso(ip: str | None = None, port: int = 8000) -> str:
        """Devuelve la URL web accesible desde la LAN para abrir el monitor."""
        host = (ip or SocketServerManager.obtenerIP() or "127.0.0.1").strip()
        return f"http://{host}:{port}/cocina"

    @staticmethod
    def obtenerIP() -> str:
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

