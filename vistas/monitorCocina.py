# Módulo vistas/monitorCocina.py
# Vista del Monitor de Cocina (specTP.md).

import customtkinter as ctk
from PIL import Image

from . import estilos
from red.socketServerManager import SocketServerManager


class VistaMonitorCocina(ctk.CTkFrame):
    """Pantalla de escritorio del monitor de cocina.

    Esta vista se encarga de mostrar el estado del servidor, la IP local, la URL
    de acceso, el QR y el número de clientes conectados. La intención es que el
    operador pueda iniciar y detener el servicio sin salir de la app principal.
    """

    def __init__(self, master, controlador):
        """Construye la interfaz del monitor y conecta la vista con el controlador.

        Args:
            master: contenedor padre de CustomTkinter.
            controlador: instancia del controlador de negocio del sistema.
        """
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador

        # Referencia al servidor operativo de cocina. Se usa para consultar el
        # estado, las conexiones activas y generar la URL/QR.
        self.servidorCocina = getattr(controlador, 'socketServerManager', None)
        self._qr_image = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Contenedor principal de la tarjeta del monitor.
        tarjeta = ctk.CTkFrame(self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO)
        tarjeta.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        tarjeta.grid_rowconfigure(0, weight=1)
        tarjeta.grid_columnconfigure(1, weight=1)

        # Lado izquierdo: estado del servidor y accion del usuario.
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

        # Lado derecho: dirección de acceso, QR y botón de copia.
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

        # Se registra el callback del servidor para que la vista se refresque
        # cuando cambien la cantidad de clientes o el estado del servicio.
        if hasattr(self.controlador, 'socketServerManager'):
            self.controlador.socketServerManager._on_status_change = self._actualizarEstado

        self._actualizarEstado(detener=True)

    def _toggleServidor(self):
        """Alterna el estado del monitor de cocina.

        Si el servidor no está corriendo, lo inicia; si ya está activo, lo
        detiene. La acción se delega al controlador, que a su vez invoca al
        SocketServerManager.
        """
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
        """Refresca el contenido visual de la vista según el estado real del servidor.

        Este método se invoca al iniciar, al detener y cada vez que cambia el
        número de clientes conectados. El objetivo es que la pantalla refleje el
        estado real del monitor, incluso si se cambia de pestaña o se recrea la
        vista.
        """
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
        """Activa o desactiva el estado interactivo de los widgets.

        Este método quedó preparado para coordinar habilitación de botones y
        entradas en futuras mejoras visuales o de flujo. Actualmente la lógica
        principal está centrada en la actualización del estado por medio del
        servidor y del botón principal.
        """
        pass

    def _copiarURL(self):
        """Copia la URL de acceso del monitor al portapapeles del sistema."""
        url = self.urlText.get()
        self.controlador._copiarAlPortapapeles(url)
        self._informar(f"URL copiada: {url}")

    def _alerta(self, mensaje):
        """Muestra un cuadro de advertencia con el texto recibido."""
        from CTkMessagebox import CTkMessagebox
        CTkMessagebox(title="Atención", message=mensaje, icon="warning")

    def _informar(self, mensaje):
        """Muestra un mensaje informativo para el usuario de la app."""
        from CTkMessagebox import CTkMessagebox
        CTkMessagebox(title="Información", message=mensaje, icon="info")