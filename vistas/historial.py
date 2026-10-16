# Módulo historial.py (Vista)
# Pantalla de Historial del sistema "Plato a Plato".
#
# Atiende los casos de uso:
#   * CU12 Ver Historial: renderiza la lista de ventas y gastos registrados.
#   * CU14 Descartar Historial: limpia el registro de movimientos sin
#     alterar el stock (pide contraseña de confirmación).
#
# Regla de rol: cero lógica operativa. Sólo leer entradas, invocar métodos del
# controlador y refrescar componentes según el resultado.

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from . import estilos
from .dialogos import PopupPassword


def _formatoMonto(valor):
    """Formatea un monto sin decimales, con separador de miles '.'."""
    return "$" + f"{valor:,.0f}".replace(",", ".")


class VistaHistorial(ctk.CTkFrame):
    """Historial de movimientos: ventas, gastos y reinserciones (CU12/CU14)."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self.movimientos = []        # lista de dicts del historial
        self._construir()
        self.refrescarHistorial()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la cabecera con el botón de descartar y el panel de lista."""
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=24, pady=(18, 10))

        ctk.CTkLabel(
            cabecera, text="Historial", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(side="left")

        ctk.CTkButton(
            cabecera, text="Descartar historial", font=estilos.F_BOLD,
            height=44, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._descartarHistorial,
        ).pack(side="right")

        self.panel = ctk.CTkScrollableFrame(
            self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO,
            scrollbar_button_color=estilos.SCROLL,
            scrollbar_button_hover_color=estilos.SCROLL_HOVER,
        )
        self.panel.pack(fill="both", expand=True, padx=24, pady=(10, 24))

    # ------------------------------------------------------------------
    # Listado (CU12)
    # ------------------------------------------------------------------
    def refrescarHistorial(self):
        """Consulta el historial al controlador y vuelve a renderizar."""
        resultado = self.controlador.verHistorial()
        if resultado["ok"]:
            self.movimientos = resultado["datos"] or []
        else:
            self.movimientos = []
            self._alerta(resultado["mensaje"])
        self._renderMovimientos()

    def _renderMovimientos(self):
        """Dibuja en el panel una fila por cada movimiento del historial."""
        for widget in self.panel.winfo_children():
            widget.destroy()
        for movimiento in self.movimientos:
            self._crearFilaMovimiento(movimiento)
        if not self.movimientos:
            ctk.CTkLabel(
                self.panel,
                text="Aún no hay movimientos registrados.",
                font=estilos.F_NORMAL, text_color=estilos.TEXTO_TENUE,
            ).pack(pady=18)

    @staticmethod
    def _etiquetaTipo(tipo):
        """Devuelve la etiqueta visible para el tipo de movimiento."""
        return {
            "venta": "Venta",
            "gasto": "Gasto",
            "reinsertar": "Reinserción",
        }.get(tipo, tipo)

    def _crearFilaMovimiento(self, movimiento):
        """Crea la tarjeta de un movimiento con sus datos alineados (COR1).

        Layout de la fila con columnas fijas para que todos los elementos
        queden alineados entre filas:
            [Tipo]  [Fecha y hora]  [Detalle ..............]  [Monto]

        En la segunda fila se muestra el detalle de la venta (productos y
        cantidades) o la descripción del gasto secundario (COR1).
        """
        tipo = movimiento["tipo"]
        fila = ctk.CTkFrame(
            self.panel, fg_color=estilos.FILA,
            corner_radius=estilos.RADIO,
        )
        fila.pack(fill="x", padx=8, pady=4)
        # La columna 2 (detalle) absorbe el espacio sobrante.
        fila.grid_columnconfigure(2, weight=1)

        # Columna 0: tipo de movimiento (ancho fijo, alineado a la izquierda).
        ctk.CTkLabel(
            fila, text=self._etiquetaTipo(tipo), font=estilos.F_BOLD,
            fg_color=estilos.BADGE_STOCK, text_color=estilos.TEXTO_CLARO,
            corner_radius=8, width=110, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(12, 10))

        # Columna 1: fecha y hora (ancho fijo, mismo patrón en todas las filas).
        ctk.CTkLabel(
            fila, text=movimiento["fechaHora"][:19], font=estilos.F_PEQUENA,
            text_color=estilos.TEXTO_TENUE, anchor="w", width=132,
        ).grid(row=0, column=1, sticky="w", padx=4, pady=(12, 10))

        # Detalle principal según el tipo de movimiento.
        if tipo == "venta":
            principal = ", ".join(
                d["nombre"] for d in movimiento["detalles"]
            ) or "Venta"
        else:
            principal = movimiento.get("nombre", "")

        # ¿Hay una segunda línea (detalle de venta / descripción del gasto)?
        tieneSecundario = (tipo == "venta" and movimiento["detalles"]) or (
            tipo != "venta" and movimiento.get("descripcion")
        )
        padyPrincipal = (12, 2) if tieneSecundario else (12, 10)
        ctk.CTkLabel(
            fila, text=principal, font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w", justify="left",
        ).grid(row=0, column=2, sticky="ew", padx=6, pady=padyPrincipal)

        # Columna 3: monto neto (ancho fijo, alineado a la derecha).
        ctk.CTkLabel(
            fila, text=_formatoMonto(movimiento["montoNeto"]),
            font=estilos.F_PRECIO, fg_color=estilos.PILL,
            text_color=estilos.TEXTO_OSCURO,
            corner_radius=estilos.RADIO_PILL, width=110,
        ).grid(row=0, column=3, sticky="e", padx=(6, 12), pady=(12, 10))

        # Segunda fila: detalle de la venta (productos y cantidades) o la
        # descripción del gasto secundario (COR1).
        if tipo == "venta" and movimiento["detalles"]:
            detalle = "  ·  ".join(
                f"{d['nombre']} x{d['cantidad']}"
                for d in movimiento["detalles"]
            )
            ctk.CTkLabel(
                fila, text=detalle, font=estilos.F_PEQUENA,
                text_color=estilos.TEXTO_TENUE, justify="left", anchor="w",
            ).grid(row=1, column=2, columnspan=2, sticky="ew", padx=6, pady=(0, 8))
        elif tipo != "venta" and movimiento.get("descripcion"):
            ctk.CTkLabel(
                fila, text=movimiento["descripcion"], font=estilos.F_PEQUENA,
                text_color=estilos.TEXTO_TENUE, justify="left", anchor="w",
            ).grid(row=1, column=2, columnspan=2, sticky="ew", padx=6, pady=(0, 8))

    # ------------------------------------------------------------------
    # CU14: Descartar historial
    # ------------------------------------------------------------------
    def _descartarHistorial(self):
        """Pide la contraseña de confirmación y limpia los movimientos."""

        def _descartarConClave(clave):
            resultado = self.controlador.borrarHistorial(clave)
            if resultado["ok"]:
                self.refrescarHistorial()
                self._informar(resultado["mensaje"])
            else:
                self._alerta(resultado["mensaje"])

        PopupPassword(
            self,
            titulo="Descartar Historial",
            mensaje="Se borrarán todas las ventas y gastos registrados. "
                    "El stock no se modifica. Ingresá la contraseña para "
                    "confirmar.",
            onConfirmar=_descartarConClave,
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