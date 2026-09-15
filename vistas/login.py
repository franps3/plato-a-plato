# Módulo login.py (Agente 2 - Vista) - PROVISIONAL
# Pantalla del Gestor de Sesión del sistema "Plato a Plato".
#
# Atiende:
#   * CU1 Crear sesión: asigna contraseña y monto inicial (fondo/vuelto).
#   * CU2 Iniciar sesión: ingresa la credencial y desbloquea la interfaz.
#   * CU3 Cerrar sesión: se dispara desde el botón Home del shell (menu.py).
#
# DECISIÓN ACORDADA: el controlador aún no expone un método para saber si ya
# existe una sesión registrada. Mientras el Agente 3 agregue haySesion(), se
# muestran AMBAS opciones y el usuario elige: "Ingresar" o "Crear sesión".
# Cuando exista haySesion(), esta vista mostrará la pantalla correcta.
#
# Regla de rol: cero lógica operativa. Sólo leer entradas, invocar métodos del
# controlador y refrescar según el resultado.
#
# NOTA: diseño PENDIENTE del PNG del usuario; usa la paleta de estilos.py.

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from . import estilos


class VistaLogin(ctk.CTkFrame):
    """Gestor de sesión: crea o inicia la sesión única del sistema."""

    def __init__(self, master, controlador, alAutenticar=None):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        # Callback que invoca el shell cuando la sesión queda activa.
        self.alAutenticar = alAutenticar
        self.modo = "ingresar"  # "ingresar" o "crear"
        self._construir()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la tarjeta central con el formulario de sesión."""
        tarjeta = ctk.CTkFrame(
            self, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO, width=420,
        )
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            tarjeta, text="Plato a Plato", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(padx=40, pady=(32, 4))
        ctk.CTkLabel(
            tarjeta, text="Gestor de sesión", font=estilos.F_PEQUENA,
            text_color=estilos.TEXTO_TENUE,
        ).pack(padx=40, pady=(0, 18))

        # Selector de modo: Ingresar / Crear sesión.
        self.selector = ctk.CTkSegmentedButton(
            tarjeta, values=["Ingresar", "Crear sesión"],
            font=estilos.F_NORMAL, command=self._cambiarModo,
            fg_color=estilos.FONDO,
            selected_color=estilos.BOTON_BARRA_ACTIVO,
            selected_hover_color=estilos.BOTON_BARRA_HOVER,
            unselected_color=estilos.BOTON_BARRA,
            unselected_hover_color=estilos.BOTON_BARRA_HOVER,
        )
        self.selector.set("Ingresar")
        self.selector.pack(padx=40, pady=(0, 18), fill="x")

        # Campo de contraseña.
        ctk.CTkLabel(
            tarjeta, text="Contraseña", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(padx=40, fill="x")
        self.entradaPass = ctk.CTkEntry(
            tarjeta, show="*", font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Mínimo 4 caracteres",
        )
        self.entradaPass.pack(padx=40, pady=(4, 14), fill="x")

        # Campo de fondo inicial (sólo visible al crear sesión).
        self.marcoFondo = ctk.CTkFrame(tarjeta, fg_color="transparent")
        ctk.CTkLabel(
            self.marcoFondo, text="Fondo inicial (vuelto)", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x")
        self.entradaFondo = ctk.CTkEntry(
            self.marcoFondo, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Ej.: 5000",
        )
        self.entradaFondo.pack(pady=(4, 0), fill="x")

        # Botón principal de acción.
        self.botonAccion = ctk.CTkButton(
            tarjeta, text="Ingresar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA_ACTIVO,
            hover_color=estilos.BOTON_BARRA_HOVER,
            corner_radius=estilos.RADIO, command=self._accion,
        )
        self.botonAccion.pack(padx=40, pady=(20, 32), fill="x")

        # Enter dispara la acción.
        self.entradaPass.bind("<Return>", lambda _e: self._accion())
        self.entradaFondo.bind("<Return>", lambda _e: self._accion())

    # ------------------------------------------------------------------
    # Cambio de modo
    # ------------------------------------------------------------------
    def _cambiarModo(self, valor):
        """Alterna entre ingresar y crear sesión, mostrando u ocultando fondo."""
        if valor == "Crear sesión":
            self.modo = "crear"
            self.marcoFondo.pack(
                padx=40, pady=(0, 10), fill="x", before=self.botonAccion
            )
            self.botonAccion.configure(text="Crear sesión")
        else:
            self.modo = "ingresar"
            self.marcoFondo.pack_forget()
            self.botonAccion.configure(text="Ingresar")

    # ------------------------------------------------------------------
    # Acción principal (CU1 / CU2)
    # ------------------------------------------------------------------
    def _accion(self):
        """Crea o inicia la sesión según el modo elegido."""
        password = self.entradaPass.get()

        if self.modo == "crear":
            fondo = self._parsearFondo(self.entradaFondo.get())
            if fondo is None:
                self._alerta("El fondo inicial debe ser un número válido.")
                return
            resultado = self.controlador.crearSesion(password, fondo)
        else:
            resultado = self.controlador.iniciarSesion(password)

        if resultado["ok"]:
            self.entradaPass.delete(0, "end")
            if self.alAutenticar is not None:
                self.alAutenticar(resultado["datos"])
        else:
            self._alerta(resultado["mensaje"])

    @staticmethod
    def _parsearFondo(texto):
        """Convierte el texto del fondo a float; None si no es numérico."""
        texto = (texto or "").strip().replace(".", "").replace(",", ".")
        if texto == "":
            return None
        try:
            return float(texto)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Diálogos
    # ------------------------------------------------------------------
    @staticmethod
    def _alerta(mensaje):
        """Muestra un aviso de error al usuario."""
        CTkMessagebox(title="Atención", message=mensaje, icon="warning")