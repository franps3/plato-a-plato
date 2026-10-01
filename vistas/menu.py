# Módulo menu.py (shell de la aplicación)
# Contenedor principal de las vistas del sistema "Plato a Plato".
#
# Responsabilidades (decisiones acordadas con el usuario):
#   * Crear la ventana raíz (CTk) y el área de contenido intercambiable.
#   * Armar la BARRA SUPERIOR compartida: botón Home + los accesos a Venta,
#     Configuración de Productos, Configuración de Sesión e Historial.
#   * Pantalla inicial: Gestor de Sesión (login). La barra superior sólo se
#     muestra una vez autenticado.
#   * Home cierra la sesión (controlador.cerrarSesion) y vuelve al login.
#   * Configuración de Productos es una vista real (CU4-CU8, vistas/config.py).
#   * Configuración de Sesión es una vista real (CU13, CU15-CU17,
#     vistas/configSesion.py).
#   * Historial es una vista real (CU12, CU14, vistas/historial.py).
#
# Regla de rol: cero lógica operativa. Sólo orquesta pantallas y delega en
# las vistas y el controlador.

import customtkinter as ctk
from PIL import Image

from . import estilos
from .iconos import obtenerIconos

# Ancho/alto de la ventana raíz.
ANCHO_VENTANA = 1080
ALTO_VENTANA = 620


class Aplicacion(ctk.CTk):
    """Ventana raíz: maneja la navegación entre las vistas del sistema."""

    def __init__(self, controlador):
        super().__init__()
        self.controlador = controlador

        self.title("Plato a Plato")
        self.geometry(f"{ANCHO_VENTANA}x{ALTO_VENTANA}")
        self.minsize(900, 560)
        self.configure(fg_color=estilos.FONDO)

        # Estado de navegación.
        self.vistaActual = None
        self.nombreVista = None

        self._cargarIconos()
        self._construirBarra()
        self._construirContenido()

        # Pantalla inicial: gestor de sesión.
        self.mostrarLogin()

    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    def _cargarIconos(self):
        """Carga los CTkImage que usa la barra superior."""
        rutas = obtenerIconos()
        self.iconoHome = ctk.CTkImage(
            light_image=Image.open(rutas["casa"]), size=(26, 26)
        )

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construirBarra(self):
        """Crea la barra superior (oculta hasta autenticar)."""
        self.barra = ctk.CTkFrame(self, fg_color=estilos.FONDO_BARRA, height=64)
        # No se empaqueta acá: se hace al autenticar.

        # Botón Home (izquierda).
        self.botonHome = ctk.CTkButton(
            self.barra, text="", image=self.iconoHome, width=52, height=44,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._home,
        )
        self.botonHome.pack(side="left", padx=(18, 8), pady=10)

        # Botones de navegación (centro).
        self.botonesNav = {}
        definiciones = [
            ("venta", "Venta", lambda: self.mostrarVenta()),
            ("configProd", "Configuración de\nProductos",
             lambda: self.mostrarConfigProductos()),
            ("configSesion", "Configuración de\nSesión",
             lambda: self.mostrarConfigSesion()),
            ("historial", "Historial", lambda: self.mostrarHistorial()),
        ]
        for clave, etiqueta, accion in definiciones:
            boton = ctk.CTkButton(
                self.barra, text=etiqueta, font=estilos.F_PEQUENA,
                width=132, height=44,
                fg_color=estilos.BOTON_BARRA,
                hover_color=estilos.BOTON_BARRA_HOVER,
                corner_radius=estilos.RADIO, command=accion,
            )
            boton.pack(side="left", padx=6, pady=10)
            self.botonesNav[clave] = boton

    def _construirContenido(self):
        """Crea el contenedor donde se intercambian las vistas."""
        self.contenido = ctk.CTkFrame(self, fg_color=estilos.FONDO)
        self.contenido.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Cambio de vistas
    # ------------------------------------------------------------------
    def _limpiarContenido(self):
        """Destruye la vista actual para liberar el contenedor."""
        if self.vistaActual is not None:
            self.vistaActual.destroy()
            self.vistaActual = None

    def _resaltarBoton(self, clave):
        """Resalta el botón de la vista activa en la barra superior."""
        for c, boton in self.botonesNav.items():
            color = (
                estilos.BOTON_BARRA_ACTIVO if c == clave
                else estilos.BOTON_BARRA
            )
            boton.configure(fg_color=color)

    def _entrarModoApp(self):
        """Muestra la barra superior (usuario autenticado)."""
        if not self.barra.winfo_ismapped():
            self.barra.pack(fill="x", before=self.contenido)

    def _salirModoApp(self):
        """Oculta la barra superior (vuelta al login)."""
        if self.barra.winfo_ismapped():
            self.barra.pack_forget()

    # ------------------------------------------------------------------
    # Pantallas
    # ------------------------------------------------------------------
    def mostrarLogin(self):
        """Muestra el gestor de sesión como pantalla inicial."""
        # Import local para evitar ciclos de importación.
        from .login import VistaLogin

        self._limpiarContenido()
        self._salirModoApp()
        self.nombreVista = "login"
        self.vistaActual = VistaLogin(
            self.contenido, self.controlador, alAutenticar=self._alAutenticar
        )
        self.vistaActual.pack(fill="both", expand=True)

    def _alAutenticar(self, _sesion):
        """Callback invocado por el login al autenticar con éxito."""
        self._entrarModoApp()
        self.mostrarVenta()

    def mostrarVenta(self):
        """Muestra la pantalla de Venta (CU5, CU9, CU10)."""
        from .venta import VistaVenta

        self._entrarModoApp()
        self._limpiarContenido()
        self.nombreVista = "venta"
        self.vistaActual = VistaVenta(self.contenido, self.controlador)
        self.vistaActual.pack(fill="both", expand=True)
        self._resaltarBoton("venta")

    def mostrarConfigProductos(self):
        """Muestra la Configuración de Productos (CU4-CU8)."""
        from .config import VistaConfigProductos

        self._entrarModoApp()
        self._limpiarContenido()
        self.nombreVista = "configProd"
        self.vistaActual = VistaConfigProductos(self.contenido, self.controlador)
        self.vistaActual.pack(fill="both", expand=True)
        self._resaltarBoton("configProd")

    def mostrarConfigSesion(self):
        """Muestra la Configuración de Sesión (CU13, CU15-CU17)."""
        from .configSesion import VistaConfigSesion

        self._entrarModoApp()
        self._limpiarContenido()
        self.nombreVista = "configSesion"
        self.vistaActual = VistaConfigSesion(
            self.contenido, self.controlador, alVolverLogin=self.mostrarLogin
        )
        self.vistaActual.pack(fill="both", expand=True)
        self._resaltarBoton("configSesion")

    def mostrarHistorial(self):
        """Muestra el Historial (CU12, CU14)."""
        from .historial import VistaHistorial

        self._entrarModoApp()
        self._limpiarContenido()
        self.nombreVista = "historial"
        self.vistaActual = VistaHistorial(self.contenido, self.controlador)
        self.vistaActual.pack(fill="both", expand=True)
        self._resaltarBoton("historial")

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------
    def _home(self):
        """Cierra la sesión y vuelve al gestor de sesión."""
        self.controlador.cerrarSesion()
        self.mostrarLogin()