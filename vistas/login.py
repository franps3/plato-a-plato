# Módulo login.py (Vista)
# Pantalla del Gestor de Sesión del sistema "Plato a Plato".
#
# Atiende:
#   * CU1 Crear sesión: asigna contraseña y monto inicial (fondo/vuelto).
#   * CU2 Iniciar sesión: ingresa la credencial y desbloquea la interfaz.
#   * CU3 Cerrar sesión: se dispara desde el botón Home del shell (menu.py).
#
# Según haySesion() (Agente 3) se muestra la pantalla correcta:
#   * Si ya existe una sesión registrada -> sólo se puede INGRESAR.
#   * Si no existe -> sólo se puede CREAR.
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
        # Pantalla correcta según exista o no una sesión registrada.
        resultado = controlador.haySesion()
        if resultado["ok"] and resultado["datos"]:
            self.existeSesion = True
            self.modo = "ingresar"
        else:
            self.existeSesion = False
            self.modo = "crear"
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

        # Selector de modo: según exista sesión se muestra la pantalla correcta.
        valores = ["Crear sesión"] if not self.existeSesion else ["Ingresar"]
        self.selector = ctk.CTkSegmentedButton(
            tarjeta, values=valores,
            font=estilos.F_NORMAL,
            fg_color=estilos.FONDO,
            selected_color=estilos.BOTON_BARRA_ACTIVO,
            selected_hover_color=estilos.BOTON_BARRA_HOVER,
            unselected_color=estilos.BOTON_BARRA,
            unselected_hover_color=estilos.BOTON_BARRA_HOVER,
        )
        self.selector.set(valores[0])
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
        textoBoton = "Crear sesión" if self.modo == "crear" else "Ingresar"
        self.botonAccion = ctk.CTkButton(
            tarjeta, text=textoBoton, font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA_ACTIVO,
            hover_color=estilos.BOTON_BARRA_HOVER,
            corner_radius=estilos.RADIO, command=self._accion,
        )
        self.botonAccion.pack(padx=40, pady=(20, 32), fill="x")

        # Enter dispara la acción.
        self.entradaPass.bind("<Return>", lambda _e: self._accion())
        self.entradaFondo.bind("<Return>", lambda _e: self._accion())

        # El campo de fondo inicial sólo aplica al crear sesión.
        if self.modo == "crear":
            self.marcoFondo.pack(
                padx=40, pady=(0, 10), fill="x", before=self.botonAccion
            )

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