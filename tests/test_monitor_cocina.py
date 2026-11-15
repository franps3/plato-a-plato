import asyncio
import socket
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from red.socketServerManager import SocketServerManager
from red.static.cocina_html import COCINA_HTML


def test_monitor_usa_configuracion_minima_de_uvicorn(monkeypatch):
    captured = {}

    class DummyConfig:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)
            self.app = kwargs.get("app")
            self.host = kwargs.get("host")
            self.port = kwargs.get("port")
            self.log_level = kwargs.get("log_level")
            self.log_config = kwargs.get("log_config")
            self.access_log = kwargs.get("access_log")

    class DummyServer:
        def __init__(self, config):
            self.config = config
            self.should_exit = False
            self.force_exit = False

        async def serve(self):
            await asyncio.sleep(0.01)

    import uvicorn

    monkeypatch.setattr(uvicorn, "Config", DummyConfig)
    monkeypatch.setattr(uvicorn, "Server", DummyServer)

    servidor = SocketServerManager(host="127.0.0.1", port=8000)
    resultado = servidor.iniciar()

    assert resultado["ok"] is True
    assert captured.get("log_config") is None
    assert captured.get("access_log") is False

    servidor.detener()


def test_monitor_html_usa_event_listeners_para_borrar_ordenes():
    assert "onclick=\"marcarListo" not in COCINA_HTML
    assert "addEventListener(\"click\"" in COCINA_HTML
    assert "tarjeta.remove()" in COCINA_HTML


def test_url_acceso_monitor_usa_http_y_ruta_cocina():
    url = SocketServerManager.obtenerURLAcceso("192.168.1.30")
    assert url == "http://192.168.1.30:8000/cocina"
    assert "ws://" not in url


def test_qr_monitor_retorna_imagen_valida():
    imagen = SocketServerManager.generarQR("http://192.168.1.30:8000/cocina")
    assert hasattr(imagen, "size")
    assert imagen.size[0] > 0 and imagen.size[1] > 0


def test_servidor_puede_reiniciarse():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    servidor = SocketServerManager(host="127.0.0.1", port=port)
    assert servidor.iniciar()["ok"] is True
    assert servidor.running is True
    assert servidor.detener()["ok"] is True
    assert servidor.running is False
    assert servidor.iniciar()["ok"] is True
    assert servidor.running is True
    servidor.detener()
