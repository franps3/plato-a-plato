# Módulo vistas/monitorCocina.py
# Vista del Monitor de Cocina (specTP.md).

import customtkinter as ctk
from PIL import Image

from . import estilos
from red.socketServerManager import SocketServerManager


class VistaMonitorCocina(ctk.CTkFrame):
    """Vista que muestra el Monitor de Cocina en la aplicación desktop."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self.servidorCocina = getattr(controlador, 'socketServerManager', None)
        self._qr_image = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        tarjeta = ctk.CTkFrame(self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO)
        tarjeta.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        tarjeta.grid_rowconfigure(0, weight=1)
        tarjeta.grid_columnconfigure(1, weight=1)

        izquierda = ctk.CTkFrame(tarjeta, fg_color="transparent")
        izquierda.grid(row=0, column=0, sticky="ns", padx=20, pady=20)

        self.labelEstado = ctk.CTkLabel(izquierda, text="Servidor: DETENIDO",
                                          font=estilos.F_BOLD, text_color=estilos.TEXTO_OSCURO)
        self.labelEstado.pack(anchor="w")

        self.labelClientes = ctk.CTkLabel(izquierda, text="Clientes conectados: 0",
                                            font=estilos.F_PEQUENA, text_color=estilos.TEXTO_TENUE)
        self.labelClientes.pack(anchor="w", pady=(6, 0))

        self.btnIniciar = ctk.CTkButton(izquierda, text="Iniciar Servidor",
                                          command=self._toggleServidor, height=36, font=estilos.F_BOLD)
        self.btnIniciar.pack(anchor="w", pady=(12, 0))

        derecha = ctk.CTkFrame(tarjeta, fg_color="transparent")
        derecha.grid(row=0, column=1, sticky="ns", padx=20, pady=20)

        self.labelIP = ctk.CTkLabel(derecha, text="IP: -",
                                    font=estilos.F_PEQUENA, text_color=estilos.TEXTO_TENUE)
        self.labelIP.pack(anchor="w")

        self.labelQR = ctk.CTkLabel(derecha, text="QR\nNo generado",
                                    width=120, height=120,
                                    fg_color=estilos.ENTRADA,
                                    text_color=estilos.ENTRADA_TEXTO,
                                    corner_radius=estilos.RADIO)
        self.labelQR.pack(pady=10)

        self.urlText = ctk.CTkEntry(derecha, width=200,
                                    placeholder_text="http://127.0.0.1:8000/cocina")
        self.urlText.pack(pady=(0, 8))
        self.urlText.insert(0, "http://127.0.0.1:8000/cocina")

        self.btnCopiar = ctk.CTkButton(derecha, text="Copiar URL", width=80, height=28,
                                         command=self._copiarURL)
        self.btnCopiar.pack()

        if hasattr(self.controlador, 'socketServerManager'):
            self.controlador.socketServerManager._on_status_change = self._actualizarEstado

        self._actualizarEstado(detener=True)

    def _toggleServidor(self):
        if self.servidorCocina is None or not self.servidorCocina.running:
            resultado = self.controlador.iniciarServidorCocina()
            if resultado["ok"]:
                self.servidorCocina = self.controlador.socketServerManager
                self.labelEstado.configure(text="Servidor: INICIADO",
                                           text_color=estilos.TEXTO_CLARO)
                self.btnIniciar.configure(text="Detener Servidor")
                self._actualizarEstado()
                self._habilitarControles(True)
            else:
                self._alerta(resultado["mensaje"])
        else:
            resultado = self.controlador.detenerServidorCocina()
            if resultado["ok"]:
                self.servidorCocina = getattr(self.controlador, 'socketServerManager', None)
                self.labelEstado.configure(text="Servidor: DETENIDO",
                                           text_color=estilos.TEXTO_OSCURO)
                self.btnIniciar.configure(text="Iniciar Servidor")
                self._actualizarEstado()
                self._habilitarControles(False)
            else:
                self._alerta(resultado["mensaje"])

    def _actualizarEstado(self, detener=False, **kwargs):
        if self.servidorCocina is None and hasattr(self.controlador, 'socketServerManager'):
            self.servidorCocina = self.controlador.socketServerManager

        if self.servidorCocina is None or not getattr(self.servidorCocina, 'running', False):
            self.labelEstado.configure(text="Servidor: DETENIDO",
                                       text_color=estilos.TEXTO_OSCURO)
            self.labelClientes.configure(text="Clientes conectados: 0")
            self.btnIniciar.configure(text="Iniciar Servidor")
            self._habilitarControles(False)
            ip = self.controlador.obtenerIPCocina() or "127.0.0.1"
            self.labelIP.configure(text=f"IP: {ip}")
            self.urlText.delete(0, "end")
            self.urlText.insert(0, f"http://{ip}:8000/cocina")
            self.labelQR.configure(image=None, text="QR\nNo generado")
            return

        ip = self.controlador.obtenerIPCocina() or "127.0.0.1"
        self.labelIP.configure(text=f"IP: {ip}")
        self.labelEstado.configure(text="Servidor: INICIADO",
                                   text_color=estilos.TEXTO_CLARO)
        self.btnIniciar.configure(text="Detener Servidor")

        try:
            clientes = self.servidorCocina.clientesActivos
        except Exception:
            clientes = 0
        self.labelClientes.configure(text=f"Clientes conectados: {clientes}")

        url = self.servidorCocina.obtenerURLAcceso(ip, self.servidorCocina.port)
        self.urlText.delete(0, "end")
        self.urlText.insert(0, url)

        try:
            qr_imagen = self.servidorCocina.generarQR(url)
            qr_imagen = qr_imagen.resize((120, 120))
            self._qr_image = ctk.CTkImage(light_image=qr_imagen, dark_image=qr_imagen, size=(120, 120))
            self.labelQR.configure(image=self._qr_image, text="")
        except Exception:
            self._qr_image = None
            self.labelQR.configure(image=None, text=f"QR\n{url[:30]}...")

    def _habilitarControles(self, estado):
        pass

    def _copiarURL(self):
        url = self.urlText.get()
        self.controlador._copiarAlPortapapeles(url)
        self._informar(f"URL copiada: {url}")

    def _alerta(self, mensaje):
        from CTkMessagebox import CTkMessagebox
        CTkMessagebox(title="Atención", message=mensaje, icon="warning")

    def _informar(self, mensaje):
        from CTkMessagebox import CTkMessagebox
        CTkMessagebox(title="Información", message=mensaje, icon="info")