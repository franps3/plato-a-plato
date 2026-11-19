# Módulo dialogos.py (Vista)
# Diálogos reutilizables de confirmación para las pantallas del sistema
# "Plato a Plato". Siguen la paleta de estilos.py y el patrón de popups
# (CTkToplevel) del Agente 2 usado en venta.py.
#
# Se usa para las acciones que requieren contraseña de confirmación:
#   * CU14 borrarHistorial
#   * CU15 reiniciar
#   * CU17 importarDb

import os
import sys

import customtkinter as ctk

from . import estilos


def aplicarIconoVentana(ventana):
    """Aplica logo.ico a una ventana principal o a un CTkToplevel."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    elif getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(__file__))

    rutaIcono = os.path.join(base, "vistas", "recursos", "logo.ico")
    try:
        ventana.iconbitmap(rutaIcono)
    except Exception:
        pass


class PopupPassword(ctk.CTkToplevel):
    """Popup modal que pide una contraseña y ejecuta una acción.

    Args:
        master: Widget padre (vista que lo abre).
        titulo: Texto del encabezado del popup.
        mensaje: Detalle informativo mostrado al usuario.
        onConfirmar: Callable(password: str) invocado con la clave ingresada.
    """

    def __init__(self, master, titulo, mensaje, onConfirmar):
        super().__init__(master)
        self._onConfirmar = onConfirmar
        self.resultado = None

        self.title(titulo)
        aplicarIconoVentana(self)
        self.configure(fg_color=estilos.FONDO)
        self.geometry("460x280")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()  # Modal: bloquea la ventana padre hasta cerrar.

        tarjeta = ctk.CTkFrame(
            self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO,
        )
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            tarjeta, text=titulo, font=estilos.F_SUBTITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(padx=24, pady=(16, 4))
        ctk.CTkLabel(
            tarjeta, text=mensaje, font=estilos.F_PEQUENA,
            text_color=estilos.TEXTO_TENUE, wraplength=380, justify="center",
        ).pack(padx=24, pady=(0, 12))

        self.entradaPass = ctk.CTkEntry(
            tarjeta, show="*", font=estilos.F_NORMAL, height=38,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Contraseña",
        )
        self.entradaPass.pack(padx=24, pady=(0, 14), fill="x")
        self.entradaPass.focus_set()
        self.entradaPass.bind("<Return>", lambda _e: self._confirmar())

        acciones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        acciones.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Confirmar", font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_BARRA_ACTIVO,
            hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._confirmar,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

    def _confirmar(self):
        """Captura la clave y delega en el callback."""
        password = self.entradaPass.get()
        self.destroy()
        if self._onConfirmar is not None:
            self._onConfirmar(password)