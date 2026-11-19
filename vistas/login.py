# Módulo login.py (Vista)
# Pantalla del Gestor de Sesión del sistema "Plato a Plato".
#
# Atiende:
#   * CU1 Crear sesión: asigna contraseña; el fondo inicial es la suma de
#     los montos de las cajas creadas (COR7).
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
from .dialogos import aplicarIconoVentana


def _formatoMonto(valor):
    """Formatea un monto sin decimales, con separador de miles '.'.

    Ej.: 2500 -> '$2.500'; 11300 -> '$11.300'.
    """
    return "$" + f"{valor:,.0f}".replace(",", ".")


class VistaLogin(ctk.CTkFrame):
    """Gestor de sesión: crea o inicia la sesión única del sistema."""

    @staticmethod
    def _calcularAnchoTarjeta(anchoVentana):
        """Devuelve un ancho de tarjeta adaptable a la resolución actual."""
        if anchoVentana <= 0:
            return 580
        return max(520, min(680, int(anchoVentana * 0.84)))

    def __init__(self, master, controlador, alAutenticar=None):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        # Callback que invoca el shell cuando la sesión queda activa.
        self.alAutenticar = alAutenticar
        # COR4: sin selector de modo. Según exista o no una sesión registrada
        # la pantalla muestra directamente el formulario de ingresar o crear.
        resultado = controlador.haySesion()
        if resultado["ok"] and resultado["datos"]:
            self.modo = "ingresar"
        else:
            self.modo = "crear"
        # MJ1: cajas (medios de pago) definidas al crear la sesión.
        self.cajas = []          # list[(nombre, monto)]
        self.popupCaja = None    # CTkToplevel "Nueva caja"
        self.tarjetaLogin = None
        self._construir()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la tarjeta central con el formulario de sesión."""
        self.pack(fill="both", expand=True)

        if self.modo == "crear":
            contenedorScroll = ctk.CTkScrollableFrame(
                self, fg_color=estilos.FONDO,
                scrollbar_button_color=estilos.SCROLL,
                scrollbar_button_hover_color=estilos.SCROLL_HOVER,
            )
        else:
            contenedorScroll = ctk.CTkFrame(
                self, fg_color=estilos.FONDO,
            )
        contenedorScroll.pack(fill="both", expand=True, padx=12, pady=12)
        contenedorScroll.grid_columnconfigure(0, weight=1)

        ancho = self._calcularAnchoTarjeta(self.winfo_width() or 1200)
        tarjeta = ctk.CTkFrame(
            contenedorScroll, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO, width=ancho,
        )
        self.tarjetaLogin = tarjeta
        padding_top = 90 if self.modo == "crear" else 200
        tarjeta.grid(
            row=0, column=0, padx=12, pady=(padding_top, 12), sticky="n"
        )
        tarjeta.grid_columnconfigure(0, weight=1)
        self.bind("<Configure>", self._ajustarAnchoTarjeta)

        ctk.CTkLabel(
            tarjeta, text="Plato a Plato", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(padx=40, pady=(32, 4))
        ctk.CTkLabel(
            tarjeta, text="Gestor de sesión", font=estilos.F_PEQUENA,
            text_color=estilos.TEXTO_TENUE,
        ).pack(padx=40, pady=(0, 18))

        # COR4: el selector de crear/iniciar sesión fue eliminado; la pantalla
        # muestra directamente el formulario correspondiente (self.modo).

        # Campo de contraseña.
        ctk.CTkLabel(
            tarjeta, text="Contraseña", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(padx=40, pady=(6, 0), fill="x")
        self.entradaPass = ctk.CTkEntry(
            tarjeta, show="*", font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Mínimo 4 caracteres",
        )
        self.entradaPass.pack(padx=40, pady=(4, 14), fill="x")

        # --- Pregunta de seguridad (MJ3): obligatoria al crear sesión ---
        self.marcoSeguridad = ctk.CTkFrame(tarjeta, fg_color="transparent")
        ctk.CTkLabel(
            self.marcoSeguridad, text="Pregunta de seguridad", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self.marcoSeguridad,
            text="Se usará para restablecer la contraseña si la olvidás.",
            font=estilos.F_PEQUENA, text_color=estilos.TEXTO_TENUE,
            justify="left", anchor="w", wraplength=400,
        ).pack(fill="x", pady=(0, 4))
        self.entradaPregunta = ctk.CTkEntry(
            self.marcoSeguridad, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
            placeholder_text="Ej.: ¿Cuál es tu comida favorita?",
        )
        self.entradaPregunta.pack(fill="x", pady=(0, 8))
        self.entradaRespuesta = ctk.CTkEntry(
            self.marcoSeguridad, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, show="*",
            placeholder_text="Respuesta de seguridad",
        )
        self.entradaRespuesta.pack(fill="x", pady=(0, 4))
        self.marcoCajas = ctk.CTkFrame(tarjeta, fg_color="transparent")
        ctk.CTkLabel(
            self.marcoCajas, text="Cajas / medios de pago (opcional)",
            font=estilos.F_BOLD, text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self.marcoCajas,
            text="El fondo inicial de la sesión será la suma de los "
                 "montos de las cajas agregadas. Si no agregás cajas "
                 "se usará la \"Caja principal\".",
            font=estilos.F_PEQUENA, text_color=estilos.TEXTO_TENUE,
            justify="left", anchor="w", wraplength=400,
        ).pack(fill="x", pady=(0, 4))
        self.contenedorCajas = ctk.CTkFrame(
            self.marcoCajas, fg_color="transparent"
        )
        self.contenedorCajas.pack(fill="x", pady=(2, 6))
        ctk.CTkButton(
            self.marcoCajas, text="+ Agregar caja", font=estilos.F_BOLD,
            height=36, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._abrirPopupCaja,
        ).pack(fill="x")
        self._renderCajas()

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

        # En modo ingresar: opción de recuperar contraseña (MJ3).
        if self.modo == "ingresar":
            ctk.CTkButton(
                tarjeta, text="¿Olvidaste tu contraseña?", font=estilos.F_PEQUENA,
                fg_color="transparent", hover_color=estilos.BOTON_BARRA_HOVER,
                text_color=estilos.TEXTO_TENUE, height=28,
                command=self._abrirRecuperacion,
            ).pack(padx=40, pady=(0, 8), anchor="e")

        # El marco de seguridad y de cajas sólo aplican al crear (COR7/MJ3).
        if self.modo == "crear":
            self.marcoSeguridad.pack(
                padx=40, pady=(0, 10), fill="x", before=self.botonAccion
            )
            self.marcoCajas.pack(
                padx=40, pady=(0, 10), fill="x", before=self.botonAccion
            )

    def _ajustarAnchoTarjeta(self, _evento=None):
        """Mantiene la tarjeta del login dentro del ancho disponible."""
        if self.tarjetaLogin is None:
            return
        ancho = self._calcularAnchoTarjeta(self.winfo_width() or 1200)
        self.tarjetaLogin.configure(width=ancho)

    # ------------------------------------------------------------------
    # Acción principal (CU1 / CU2)
    # ------------------------------------------------------------------
    def _accion(self):
        """Crea o inicia la sesión según el modo elegido."""
        password = self.entradaPass.get()

        if self.modo == "crear":
            # COR7: el fondo inicial es la suma de los montos de las cajas.
            # MJ3: pregunta y respuesta de seguridad obligatorias.
            resultado = self.controlador.crearSesion(
                password, self.cajas or None,
                preguntaSeguridad=self.entradaPregunta.get(),
                respuestaSeguridad=self.entradaRespuesta.get(),
            )
        else:
            resultado = self.controlador.iniciarSesion(password)

        if resultado["ok"]:
            self.entradaPass.delete(0, "end")
            if self.alAutenticar is not None:
                self.alAutenticar(resultado["datos"])
        else:
            self._alerta(resultado["mensaje"])

    # ------------------------------------------------------------------
    # Cajas / medios de pago (MJ1): creación de múltiples cajas
    # ------------------------------------------------------------------
    def _abrirPopupCaja(self):
        """Abre el popup para cargar una caja (nombre + monto, MJ1)."""
        if self.popupCaja is not None and self.popupCaja.winfo_exists():
            return
        self.popupCaja = ctk.CTkToplevel(self)
        self.popupCaja.title("Nueva caja")
        self.popupCaja.configure(fg_color=estilos.FONDO)
        self.popupCaja.geometry("380x320")
        self.popupCaja.resizable(False, False)
        self.popupCaja.transient(self.winfo_toplevel())
        self.popupCaja.grab_set()

        aplicarIconoVentana(self.popupCaja)

        tarjeta = ctk.CTkFrame(
            self.popupCaja, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            tarjeta, text="Nueva caja", font=estilos.F_SUBTITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(padx=24, pady=(16, 4))
        ctk.CTkLabel(
            tarjeta, text="Nombre y monto inicial de la caja "
                          "(ej. Efectivo, Mercado Pago).",
            font=estilos.F_PEQUENA, text_color=estilos.TEXTO_TENUE,
            wraplength=320, justify="center",
        ).pack(padx=24, pady=(0, 12))

        self.nombreCajaEntry = ctk.CTkEntry(
            tarjeta, font=estilos.F_NORMAL, height=38,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
            placeholder_text="Nombre (ej.: Efectivo)",
        )
        self.nombreCajaEntry.pack(padx=24, pady=(0, 8), fill="x")
        self.montoCajaEntry = ctk.CTkEntry(
            tarjeta, font=estilos.F_NORMAL, height=38,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
            placeholder_text="Monto inicial (ej.: 2000)",
        )
        self.montoCajaEntry.pack(padx=24, pady=(0, 14), fill="x")

        acciones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        acciones.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._cerrarPopupCaja,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Agregar", font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_BARRA_ACTIVO,
            hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._confirmarPopupCaja,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self.nombreCajaEntry.focus_set()
        self.nombreCajaEntry.bind(
            "<Return>", lambda _e: self._confirmarPopupCaja()
        )
        self.montoCajaEntry.bind(
            "<Return>", lambda _e: self._confirmarPopupCaja()
        )

    def _confirmarPopupCaja(self):
        """Valida y agrega la caja cargada en el popup (MJ1)."""
        nombre = self.nombreCajaEntry.get().strip()
        monto = self._parsearMonto(self.montoCajaEntry.get())
        if not nombre:
            self._alerta("El nombre de la caja no puede ser vacío.")
            return
        if monto is None or monto < 0:
            self._alerta("El monto de la caja debe ser un número válido.")
            return
        self.cajas.append((nombre, monto))
        self._renderCajas()
        self._cerrarPopupCaja()

    def _cerrarPopupCaja(self):
        """Cierra el popup de nueva caja, si está abierto."""
        if self.popupCaja is not None and self.popupCaja.winfo_exists():
            self.popupCaja.destroy()
        self.popupCaja = None

    def _renderCajas(self):
        """Redibuja los chips de cajas agregadas (MJ1)."""
        for widget in self.contenedorCajas.winfo_children():
            widget.destroy()
        for idx, (nombre, monto) in enumerate(self.cajas):
            chip = ctk.CTkFrame(
                self.contenedorCajas, fg_color=estilos.FILA,
                corner_radius=estilos.RADIO_PILL,
            )
            chip.pack(fill="x", pady=2)
            ctk.CTkLabel(
                chip, text=f"{nombre} · {_formatoMonto(monto)}",
                font=estilos.F_NORMAL, text_color=estilos.TEXTO_CLARO,
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=(12, 4), pady=5)
            ctk.CTkButton(
                chip, text="✕", width=28, height=28,
                fg_color="transparent", hover_color=estilos.BOTON_BARRA_HOVER,
                corner_radius=8, font=estilos.F_BOLD,
                command=lambda i=idx: self._quitarCaja(i),
            ).pack(side="right", padx=(0, 6))

    def _quitarCaja(self, idx):
        """Elimina una caja de la lista (MJ1)."""
        if 0 <= idx < len(self.cajas):
            self.cajas.pop(idx)
            self._renderCajas()

    def _abrirRecuperacion(self):
        """Abre el popup para restablecer la contraseña (MJ3)."""
        resultado = self.controlador.verPreguntaSeguridad()
        if not resultado["ok"]:
            self._alerta(resultado["mensaje"])
            return
        pregunta = (resultado["datos"] or {}).get("pregunta", "")
        if not pregunta:
            self._alerta("No hay pregunta de seguridad registrada.")
            return

        popup = ctk.CTkToplevel(self)
        popup.title("Recuperar contraseña")
        aplicarIconoVentana(popup)

        popup.configure(fg_color=estilos.FONDO)
        popup.geometry("420x360")
        popup.resizable(False, False)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        tarjeta = ctk.CTkFrame(
            popup, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO,
        )
        tarjeta.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            tarjeta, text="Recuperar contraseña", font=estilos.F_SUBTITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(padx=24, pady=(16, 4))
        ctk.CTkLabel(
            tarjeta, text=pregunta, font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, wraplength=360, justify="center",
        ).pack(padx=24, pady=(8, 12))

        entradaRespuesta = ctk.CTkEntry(
            tarjeta, font=estilos.F_NORMAL, height=38,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, show="*",
            placeholder_text="Respuesta de seguridad",
        )
        entradaRespuesta.pack(padx=24, pady=(0, 8), fill="x")
        entradaNueva = ctk.CTkEntry(
            tarjeta, font=estilos.F_NORMAL, height=38,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, show="*",
            placeholder_text="Nueva contraseña (mín. 4 caracteres)",
        )
        entradaNueva.pack(padx=24, pady=(0, 14), fill="x")

        def _confirmar():
            respuesta = entradaRespuesta.get()
            nueva = entradaNueva.get()
            popup.destroy()
            resultado = self.controlador.recuperarPassword(respuesta, nueva)
            if resultado["ok"]:
                self._informar(resultado["mensaje"])
            else:
                self._alerta(resultado["mensaje"])

        acciones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        acciones.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=popup.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Restablecer", font=estilos.F_BOLD, height=40,
            fg_color=estilos.BOTON_BARRA_ACTIVO,
            hover_color=estilos.BOTON_BARRA_HOVER,
            command=_confirmar,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        entradaRespuesta.focus_set()
    # ------------------------------------------------------------------
    @staticmethod
    def _parsearMonto(texto):
        """Convierte el texto a float; None si no es numérico.

        Acepta separador de miles '.' y decimal ',' (ej.: '2.500' -> 2500).
        """
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
    @staticmethod
    def _informar(mensaje):
        """Muestra un aviso informativo al usuario."""
        CTkMessagebox(title="Información", message=mensaje, icon="info")

    @staticmethod
    def _alerta(mensaje):
        """Muestra un aviso de error al usuario."""
        CTkMessagebox(title="Atención", message=mensaje, icon="warning")