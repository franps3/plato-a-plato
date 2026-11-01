# Módulo estadisticas.py (Vista)
# Pantalla de Estadísticas básicas del sistema "Plato a Plato" (MJ2).
#
# Muestra los 7 indicadores de la sesión: total de entradas $, total de
# salidas $, cantidad de productos vendidos, cantidad de combos vendidos,
# cantidad de gastos/reingresos, producto más vendido y combo más vendido.
#
# Regla de rol: cero lógica operativa. Sólo leer entradas, invocar métodos del
# controlador y refrescar componentes según el resultado.

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from . import estilos


def _formatoMonto(valor):
    """Formatea un monto sin decimales, con separador de miles '.'."""
    try:
        return "$" + f"{float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


class VistaEstadisticas(ctk.CTkFrame):
    """Estadísticas básicas de la sesión (MJ2)."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self._construir()
        self.refrescar()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la cabecera y el panel con los 7 indicadores."""
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=24, pady=(18, 10))

        ctk.CTkLabel(
            cabecera, text="Estadísticas", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(side="left")

        ctk.CTkButton(
            cabecera, text="Actualizar", font=estilos.F_BOLD,
            height=44, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self.refrescar,
        ).pack(side="right")

        self.panel = ctk.CTkScrollableFrame(
            self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO,
            scrollbar_button_color=estilos.SCROLL,
            scrollbar_button_hover_color=estilos.SCROLL_HOVER,
        )
        self.panel.pack(fill="both", expand=True, padx=24, pady=(10, 24))

    def refrescar(self):
        """Consulta las estadísticas al controlador y vuelve a renderizar."""
        resultado = self.controlador.verEstadisticas()
        if resultado["ok"]:
            datos = resultado["datos"] or {}
        else:
            datos = {}
            self._alerta(resultado["mensaje"])
        self._render(datos)

    def _render(self, datos):
        """Dibuja los 7 indicadores en el panel."""
        for widget in self.panel.winfo_children():
            widget.destroy()

        def _fila(etiqueta, valor):
            marco = ctk.CTkFrame(self.panel, fg_color=estilos.FILA,
                                 corner_radius=estilos.RADIO)
            marco.pack(fill="x", pady=4, padx=4)
            ctk.CTkLabel(
                marco, text=etiqueta, font=estilos.F_BOLD,
                text_color=estilos.TEXTO_CLARO, anchor="w",
            ).pack(side="left", padx=14, pady=12)
            ctk.CTkLabel(
                marco, text=str(valor), font=estilos.F_PRECIO,
                text_color=estilos.TEXTO_OSCURO, fg_color=estilos.PILL,
                corner_radius=estilos.RADIO_PILL,
            ).pack(side="right", padx=14, pady=10)

        _fila("Total de entradas $",
              _formatoMonto(datos.get("totalEntradas", 0)))
        _fila("Total de salidas $",
              _formatoMonto(datos.get("totalSalidas", 0)))
        _fila("Cantidad de productos vendidos",
              datos.get("cantidadProductosVendidos", 0))
        _fila("Cantidad de combos vendidos",
              datos.get("cantidadCombosVendidos", 0))
        _fila("Cantidad de gastos/reingresos",
              datos.get("cantidadGastos", 0))

        prod = datos.get("productoMasVendido")
        if prod is None:
            textoProd = "Sin datos"
        else:
            _id, nombre, cantidad = prod
            textoProd = f"{nombre} ({cantidad})"
        _fila("Producto más vendido", textoProd)

        combo = datos.get("comboMasVendido")
        if combo is None:
            textoCombo = "Sin datos"
        else:
            _id, nombre, cantidad = combo
            textoCombo = f"{nombre} ({cantidad})"
        _fila("Combo más vendido", textoCombo)

    @staticmethod
    def _alerta(mensaje):
        """Muestra un aviso de error al usuario."""
        CTkMessagebox(title="Atención", message=mensaje, icon="warning")