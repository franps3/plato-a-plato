# Módulo configSesion.py (Vista)
# Pantalla de Configuración de Sesión del sistema "Plato a Plato".
#
# Atiende los casos de uso:
#   * CU13 Exportar Historial: genera un .xlsx con el historial.
#   * CU15 Reiniciar Sistema: borra la sesión y BD local (pide contraseña).
#   * CU16 Exportar Sesión: empaqueta la BD y estado actual en un .zip.
#   * CU17 Importar Sesión: carga/sobrescribe una sesión desde un .zip
#     (pide la clave nueva que se asignará).
#
# Regla de rol: cero lógica operativa. Sólo leer entradas, invocar métodos del
# controlador y refrescar componentes según el resultado.

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from tkinter import filedialog

from . import estilos
from .dialogos import PopupPassword


class VistaConfigSesion(ctk.CTkFrame):
    """Configuración de la sesión: exportar/importar y reiniciar.

    Args:
        master: Contenedor de la vista.
        controlador: Único punto de contacto con la capa de control.
        alVolverLogin: Callable() a ejecutar tras reiniciar/importar,
            para que el shell vuelva al gestor de sesión.
    """

    def __init__(self, master, controlador, alVolverLogin=None):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self.alVolverLogin = alVolverLogin
        self._construir()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la tarjeta central con las acciones de la sesión."""
        titulo = ctk.CTkLabel(
            self, text="Configuración de Sesión", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        )
        titulo.pack(padx=24, pady=(28, 10))

        tarjeta = ctk.CTkFrame(
            self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO,
        )
        tarjeta.pack(fill="both", expand=True, padx=48, pady=(6, 24))

        self._crearAccion(
            tarjeta,
            "Exportar Historial (Excel)",
            "Genera un archivo .xlsx con las ventas y gastos de la sesión.",
            "Exportar .xlsx", self._exportarExcel,
        )
        self._crearAccion(
            tarjeta,
            "Exportar Sesión (respaldo)",
            "Empaqueta la base de datos y el estado actual en un .zip.",
            "Exportar .zip", self._exportarSesion,
        )
        self._crearAccion(
            tarjeta,
            "Importar Sesión",
            "Carga una sesión desde un .zip y asigna una clave nueva.",
            "Importar .zip", self._importarSesion,
        )
        self._crearAccion(
            tarjeta,
            "Reiniciar Sistema",
            "Borra la sesión y la base de datos local. Requiere contraseña.",
            "Reiniciar", self._reiniciar,
        )

    def _crearAccion(self, parent, titulo, detalle, textoBoton, accion):
        """Crea una fila de acción: título, detalle y botón."""
        marco = ctk.CTkFrame(
            parent, fg_color=estilos.FILA, corner_radius=estilos.RADIO,
        )
        marco.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(
            marco, text=titulo, font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(14, 8))
        ctk.CTkButton(
            marco, text=textoBoton, font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=accion,
        ).pack(side="left", padx=(0, 12))

    # ------------------------------------------------------------------
    # CU13: Exportar Historial
    # ------------------------------------------------------------------
    def _exportarExcel(self):
        """Elige destino y exporta el historial a .xlsx (CU13)."""
        ruta = filedialog.asksaveasfilename(
            title="Guardar historial",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
            initialfile="historial_sesion.xlsx",
        )
        if not ruta:
            return  # El usuario canceló el diálogo.
        resultado = self.controlador.exportExcel(ruta)
        if resultado["ok"]:
            self._informar(resultado["mensaje"])
        else:
            self._alerta(resultado["mensaje"])

    # ------------------------------------------------------------------
    # CU16: Exportar Sesión
    # ------------------------------------------------------------------
    def _exportarSesion(self):
        """Elige destino y empaqueta la sesión en un .zip (CU16)."""
        ruta = filedialog.asksaveasfilename(
            title="Guardar sesión",
            defaultextension=".zip",
            filetypes=[("Zip", "*.zip"), ("Todos los archivos", "*.*")],
            initialfile="sesion_respaldo.zip",
        )
        if not ruta:
            return  # El usuario canceló el diálogo.
        resultado = self.controlador.exportarDb(ruta)
        if resultado["ok"]:
            self._informar(resultado["mensaje"])
        else:
            self._alerta(resultado["mensaje"])
    # ------------------------------------------------------------------
    # CU17: Importar Sesión
    # ------------------------------------------------------------------
    def _importarSesion(self):
        """Elige un .zip y pide la clave nueva para importar (CU17)."""
        ruta = filedialog.askopenfilename(
            title="Seleccionar sesión (.zip)",
            filetypes=[("Zip", "*.zip"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return  # El usuario canceló el diálogo.

        def _importarConClave(clave):
            resultado = self.controlador.importarDb(ruta, clave)
            if resultado["ok"]:
                self._informar(resultado["mensaje"])
                if self.alVolverLogin is not None:
                    self.alVolverLogin()
            else:
                self._alerta(resultado["mensaje"])

        PopupPassword(
            self,
            titulo="Importar Sesión",
            mensaje="Ingresá la clave nueva que se asignará a la sesión "
                    "importada.",
            onConfirmar=_importarConClave,
        )

    # ------------------------------------------------------------------
    # CU15: Reiniciar Sistema
    # ------------------------------------------------------------------
    def _reiniciar(self):
        """Pide la contraseña y reinicia el sistema (CU15)."""
        def _reiniciarConClave(clave):
            resultado = self.controlador.reiniciar(clave)
            if resultado["ok"]:
                self._informar(resultado["mensaje"])
                if self.alVolverLogin is not None:
                    self.alVolverLogin()
            else:
                self._alerta(resultado["mensaje"])

        PopupPassword(
            self,
            titulo="Reiniciar Sistema",
            mensaje="Esta acción borra la sesión y la base de datos local. "
                    "Ingresá la contraseña actual para confirmar.",
            onConfirmar=_reiniciarConClave,
        )

    # ------------------------------------------------------------------
    # Diálogos
    # ------------------------------------------------------------------
    @staticmethod
    def _alerta(mensaje):
        """Muestra un aviso de error al usuario."""
        CTkMessagebox(title="Atención", message=mensaje, icon="warning")

    @staticmethod
    def _informar(mensaje):
        """Muestra un aviso informativo al usuario."""
        CTkMessagebox(title="Información", message=mensaje, icon="info")