# Módulo venta.py (Agente 2 - Vista)
# Pantalla de Venta del sistema "Plato a Plato".
#
# Renderiza:
#   * Barra de búsqueda (filtra localmente el listado, sin tocar el controlador).
#   * Botón de carrito que abre el popup de la venta actual.
#   * Listado de productos (nombre, stock, precio y botón "+" para agregar).
#   * Popup "Carrito" con los ítems (cantidad, subtotal y botones - + x),
#     la banda de Total y los botones Confirmar / Cancelar.
#
# Regla de rol: cero lógica operativa. Sólo lee entradas, invoca métodos del
# controlador y refresca componentes según el resultado.
#
# Notas de decisiones acordadas con el usuario:
#   * El botón "x" (eliminar la línea completa) queda DESHABILITADO hasta que
#     el Agente 3 implemente quitarProdCompleto().
#   * "Cancelar" sólo cierra el popup (deja el carrito intacto).
#   * La búsqueda filtra localmente la lista ya cargada.

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image

from . import estilos
from .iconos import obtenerIconos


def _formatoMonto(valor):
    """Formatea un monto sin decimales, con separador de miles '.'.

    Ej.: 2500 -> '$2.500'; 11300 -> '$11.300'.
    """
    return "$" + f"{valor:,.0f}".replace(",", ".")


class VistaVenta(ctk.CTkFrame):
    """Pantalla de venta: catálogo, búsqueda y carrito (CU5, CU9, CU10)."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self.productos = []          # lista de Producto vigente
        self.filtro = ""             # texto de búsqueda actual
        self.popupCarrito = None     # CTkToplevel del carrito (si está abierto)
        self._cargarIconos()
        self._construir()
        self.refrescarProductos()

    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    def _cargarIconos(self):
        """Carga los CTkImage de la vista a partir de los PNG generados."""
        rutas = obtenerIconos()
        self.iconos = {
            "lupa": self._icono(rutas["lupa"], 18),
            "carrito": self._icono(rutas["carrito"], 24),
            "mas": self._icono(rutas["mas"], 18),
            "menos": self._icono(rutas["menos"], 16),
            "cerrar": self._icono(rutas["cerrar"], 12),
        }

    @staticmethod
    def _icono(ruta, tam):
        """Construye un CTkImage cuadrado de lado 'tam' desde un PNG."""
        return ctk.CTkImage(light_image=Image.open(ruta), size=(tam, tam))

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la barra superior (búsqueda + carrito) y el panel de lista."""
        # --- Barra de búsqueda + botón carrito ---
        barraSup = ctk.CTkFrame(self, fg_color="transparent")
        barraSup.pack(fill="x", padx=24, pady=(18, 10))

        # Contenedor blanco con la lupa a la izquierda y el campo a la derecha.
        contenedor = ctk.CTkFrame(
            barraSup, fg_color=estilos.ENTRADA,
            corner_radius=estilos.RADIO_PILL, height=44,
        )
        contenedor.pack(side="left", fill="x", expand=True)
        contenedor.pack_propagate(False)

        ctk.CTkLabel(
            contenedor, text="", image=self.iconos["lupa"],
            fg_color="transparent",
        ).pack(side="left", padx=(14, 4))

        self.entradaBusqueda = ctk.CTkEntry(
            contenedor, fg_color="transparent", border_width=0,
            text_color=estilos.ENTRADA_TEXTO, font=estilos.F_NORMAL,
            placeholder_text="Buscar producto...",
        )
        self.entradaBusqueda.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self.entradaBusqueda.bind("<KeyRelease>", self._alCambiarBusqueda)

        self.botonCarrito = ctk.CTkButton(
            barraSup, text="", image=self.iconos["carrito"],
            width=44, height=44, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._abrirCarrito,
        )
        self.botonCarrito.pack(side="left", padx=(10, 0))

        # --- Panel de lista de productos (con scroll) ---
        self.panel = ctk.CTkScrollableFrame(
            self, fg_color=estilos.FONDO_PANEL, corner_radius=estilos.RADIO,
            scrollbar_button_color=estilos.SCROLL,
            scrollbar_button_hover_color=estilos.SCROLL_HOVER,
        )
        self.panel.pack(fill="both", expand=True, padx=24, pady=(10, 24))

    # ------------------------------------------------------------------
    # Refresco del catálogo
    # ------------------------------------------------------------------
    def refrescarProductos(self):
        """Consulta el catálogo al controlador y vuelve a renderizar la lista."""
        resultado = self.controlador.verProductos()
        if resultado["ok"]:
            self.productos = resultado["datos"] or []
        else:
            self.productos = []
            self._alerta(resultado["mensaje"])
        self._renderProductos()

    def _renderProductos(self):
        """Dibuja en el panel las filas de los productos que pasan el filtro."""
        for widget in self.panel.winfo_children():
            widget.destroy()

        texto = self.filtro.strip().lower()
        for producto in self.productos:
            if texto and texto not in producto.nombre.lower():
                continue
            self._crearFilaProducto(producto)

    def _crearFilaProducto(self, producto):
        """Crea la tarjeta de un producto: nombre, stock, precio y botón +."""
        fila = ctk.CTkFrame(
            self.panel, fg_color=estilos.FILA,
            corner_radius=estilos.RADIO, height=46,
        )
        fila.pack(fill="x", padx=8, pady=4)
        fila.pack_propagate(False)

        # Nombre del producto (ocupa el espacio sobrante a la izquierda).
        ctk.CTkLabel(
            fila, text=producto.nombre, font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(14, 8))

        # Recuadro con el stock disponible.
        ctk.CTkLabel(
            fila, text=str(producto.stock), font=estilos.F_BOLD,
            fg_color=estilos.BADGE_STOCK, text_color=estilos.TEXTO_CLARO,
            corner_radius=8, width=42,
        ).pack(side="left", padx=6)

        # Pastilla blanca con el precio.
        ctk.CTkLabel(
            fila, text=_formatoMonto(producto.precio), font=estilos.F_PRECIO,
            fg_color=estilos.PILL, text_color=estilos.TEXTO_OSCURO,
            corner_radius=estilos.RADIO_PILL, width=96,
        ).pack(side="left", padx=6)

        # Botón "+" para sumar una unidad al carrito.
        ctk.CTkButton(
            fila, text="", image=self.iconos["mas"], width=32, height=32,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=8,
            command=lambda p=producto: self._agregarAlCarrito(p),
        ).pack(side="left", padx=(6, 12))

    # ------------------------------------------------------------------
    # Búsqueda local (filtro sin controlador)
    # ------------------------------------------------------------------
    def _alCambiarBusqueda(self, _evento=None):
        """Filtra la lista localmente ante cada pulsación en la búsqueda."""
        self.filtro = self.entradaBusqueda.get()
        self._renderProductos()

    # ------------------------------------------------------------------
    # Carrito: agregar / abrir popup
    # ------------------------------------------------------------------
    def _agregarAlCarrito(self, producto):
        """Suma una unidad del producto (CU9) y avisa si no hay stock."""
        resultado = self.controlador.agregarProd(producto.idProducto)
        if not resultado["ok"]:
            self._alerta(resultado["mensaje"])

    def _abrirCarrito(self):
        """Abre el popup del carrito; si está vacío, lo avisa."""
        if not self.controlador.carrito:
            self._alerta("El carrito está vacío.")
            return
        if self.popupCarrito is not None and self.popupCarrito.winfo_exists():
            self.popupCarrito.lift()
            return

        self.popupCarrito = ctk.CTkToplevel(self)
        self.popupCarrito.title("Carrito")
        self.popupCarrito.configure(fg_color=estilos.FONDO)
        self.popupCarrito.geometry("560x600")
        self.popupCarrito.resizable(False, False)
        self.popupCarrito.transient(self.winfo_toplevel())

        # Encabezado.
        encabezado = ctk.CTkFrame(
            self.popupCarrito, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        encabezado.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            encabezado, text="Carrito", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(pady=10)

        # Lista de ítems del carrito.
        self.itemsCarrito = ctk.CTkScrollableFrame(
            self.popupCarrito, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
            scrollbar_button_color=estilos.SCROLL,
            scrollbar_button_hover_color=estilos.SCROLL_HOVER,
        )
        self.itemsCarrito.pack(fill="both", expand=True, padx=16, pady=8)

        # Aviso de función pendiente (botón x deshabilitado).
        ctk.CTkLabel(
            self.popupCarrito,
            text="El botón x (eliminar línea) se habilitará cuando el Agente 3 "
                 "implemente quitarProdCompleto().",
            font=estilos.F_PEQUENA, text_color=estilos.TEXTO_TENUE,
            wraplength=520, justify="center",
        ).pack(padx=16, pady=(0, 4))

        # Banda de Total.
        bandaTotal = ctk.CTkFrame(
            self.popupCarrito, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        bandaTotal.pack(fill="x", padx=16, pady=8)
        self.lblTotal = ctk.CTkLabel(
            bandaTotal, text="Total: $0", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        )
        self.lblTotal.pack(pady=12)

        # Botones Confirmar / Cancelar.
        acciones = ctk.CTkFrame(self.popupCarrito, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Confirmar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._confirmarVenta,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._cerrarCarrito,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self._refrescarCarrito()

    # ------------------------------------------------------------------
    # Carrito: contenido y total
    # ------------------------------------------------------------------
    def _refrescarCarrito(self):
        """Redibuja los ítems del carrito y recalcula el total."""
        if self.popupCarrito is None or not self.popupCarrito.winfo_exists():
            return
        for widget in self.itemsCarrito.winfo_children():
            widget.destroy()

        productos = {p.idProducto: p for p in self.productos}
        total = 0.0
        for idProducto, cantidad in self.controlador.carrito.items():
            producto = productos.get(idProducto)
            if producto is None:
                continue
            subtotal = cantidad * producto.precio
            total += subtotal
            self._crearFilaCarrito(producto, cantidad, subtotal)

        self.lblTotal.configure(text="Total: " + _formatoMonto(total))

    def _crearFilaCarrito(self, producto, cantidad, subtotal):
        """Crea una fila del carrito: nombre, xCantidad, subtotal y botones."""
        fila = ctk.CTkFrame(
            self.itemsCarrito, fg_color=estilos.FILA,
            corner_radius=estilos.RADIO, height=46,
        )
        fila.pack(fill="x", padx=4, pady=4)
        fila.pack_propagate(False)

        ctk.CTkLabel(
            fila, text=producto.nombre, font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(12, 6))

        ctk.CTkLabel(
            fila, text=f"x{cantidad}", font=estilos.F_PEQUENA,
            text_color=estilos.TEXTO_CLARO, width=30,
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            fila, text=_formatoMonto(subtotal), font=estilos.F_PRECIO,
            fg_color=estilos.PILL, text_color=estilos.TEXTO_OSCURO,
            corner_radius=estilos.RADIO_PILL, width=92,
        ).pack(side="left", padx=6)

        # Botón "x": DESHABILITADO (pendiente del Agente 3).
        ctk.CTkButton(
            fila, text="", image=self.iconos["cerrar"], width=32, height=32,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=8, state="disabled",
        ).pack(side="left", padx=(4, 10))

        # Botón "+": suma una unidad.
        ctk.CTkButton(
            fila, text="", image=self.iconos["mas"], width=32, height=32,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=8,
            command=lambda p=producto: self._carritoAgregar(p),
        ).pack(side="left", padx=2)

        # Botón "-": resta una unidad (al llegar a 0 quita el ítem).
        ctk.CTkButton(
            fila, text="", image=self.iconos["menos"], width=32, height=32,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=8,
            command=lambda p=producto: self._carritoQuitar(p),
        ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Carrito: acciones de líneas
    # ------------------------------------------------------------------
    def _carritoAgregar(self, producto):
        """Suma una unidad desde el popup (CU9) y refresca el carrito."""
        resultado = self.controlador.agregarProd(producto.idProducto)
        if not resultado["ok"]:
            self._alerta(resultado["mensaje"])
        self._refrescarCarrito()

    def _carritoQuitar(self, producto):
        """Resta una unidad desde el popup (CU9); cierra si queda vacío."""
        self.controlador.quitarProd(producto.idProducto)
        if not self.controlador.carrito:
            self._cerrarCarrito()
            return
        self._refrescarCarrito()

    # ------------------------------------------------------------------
    # Carrito: confirmar / cancelar
    # ------------------------------------------------------------------
    def _confirmarVenta(self):
        """Confirma la venta (CU10), cierra el popup y refresca el catálogo."""
        resultado = self.controlador.confirmarVenta()
        if resultado["ok"]:
            self._cerrarCarrito()
            self.refrescarProductos()
            self._informar("Venta registrada correctamente.")
        else:
            self._alerta(resultado["mensaje"])

    def _cerrarCarrito(self):
        """Cierra el popup del carrito dejando el carrito intacto."""
        if self.popupCarrito is not None and self.popupCarrito.winfo_exists():
            self.popupCarrito.destroy()
        self.popupCarrito = None

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