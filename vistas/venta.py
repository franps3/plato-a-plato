# Módulo venta.py (Agente 2 - Vista)
# Pantalla de Venta del sistema "Plato a Plato".
#
# Renderiza:
#   * Barra de búsqueda (filtra localmente el listado, sin tocar el controlador).
#   * Botón de carrito que abre el popup de la venta actual.
#   * Botón "Gasto" que abre el popup "Registrar Gasto" (CU11).
#   * Listado de productos (nombre, stock, precio y botón "+" para agregar).
#   * Popup "Carrito" con los ítems (cantidad, subtotal y botones - + x),
#     la banda de Total y los botones Confirmar / Cancelar.
#   * Popup "Registrar Gasto" (CU11) con los campos nombre, descripción y
#     monto; registra el egreso y descuenta el valor de caja.
#
# Regla de rol: cero lógica operativa. Sólo lee entradas, invoca métodos del
# controlador y refresca componentes según el resultado.
#
# Notas de decisiones acordadas con el usuario:
#   * El botón "x" elimina la línea completa del carrito (quitarProdCompleto).
#   * "Cancelar" sólo cierra el popup (deja el carrito intacto).
#   * La búsqueda filtra localmente la lista ya cargada.
#   * El botón "Gasto" abre el popup de CU11; un gasto no puede superar la
#     caja disponible (lo valida el controlador).

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
    """Pantalla de venta: catálogo, búsqueda, carrito y gastos (CU5, CU9, CU10 y CU11)."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self.productos = []          # lista de Producto vigente
        self.filtro = ""             # texto de búsqueda actual
        self.popupCarrito = None     # CTkToplevel del carrito (si está abierto)
        self.popupGasto = None       # CTkToplevel "Registrar Gasto" (CU11)
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

        # Botón "Gasto": abre el popup para registrar un egreso (CU11).
        self.botonGasto = ctk.CTkButton(
            barraSup, text="Gasto", font=estilos.F_BOLD,
            width=92, height=44, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._abrirGasto,
        )
        self.botonGasto.pack(side="left", padx=(10, 0))

        self.botonCarrito = ctk.CTkButton(
            barraSup, text="", image=self.iconos["carrito"],
            width=44, height=44, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._abrirCarrito,
        )
        self.botonCarrito.pack(side="left", padx=(10, 0))

        # Total de caja visible (MJ7): suma de todas las cajas de la sesión.
        self.lblCajaTotal = ctk.CTkLabel(
            barraSup, text="Caja total: $0", font=estilos.F_BOLD,
            fg_color=estilos.BADGE_STOCK, text_color=estilos.TEXTO_CLARO,
            corner_radius=estilos.RADIO_PILL, width=150,
        )
        self.lblCajaTotal.pack(side="left", padx=(10, 0))

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
        """Consulta el catálogo al controlador y vuelve a renderizar la lista.

        COR2: usa verProductosVenta() para que el stock mostrado sea el
        DISPONIBLE (stock real menos lo reservado en el carrito), logrando el
        descuento de stock "en vivo" en la pantalla de venta.
        """
        resultado = self.controlador.verProductosVenta()
        if resultado["ok"]:
            self.productos = resultado["datos"] or []
        else:
            self.productos = []
            self._alerta(resultado["mensaje"])
        self._renderProductos()
        # MJ7: mantiene el total de caja al día (ventas y gastos lo modifican).
        self._refrescarCaja()

    def _refrescarCaja(self):
        """Actualiza el total de caja visible (MJ7, verTotalCajas)."""
        sesion = self.controlador.sesionActiva
        if sesion is None:
            self.lblCajaTotal.configure(text="Caja total: $0")
            return
        resultado = self.controlador.verTotalCajas(sesion.idSesion)
        if resultado["ok"]:
            self.lblCajaTotal.configure(
                text="Caja total: " + _formatoMonto(resultado["datos"])
            )

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

        # Cantidad y subtotal en el carrito (MJ8).
        cantidadCarrito = self.controlador.carrito.get(producto.idProducto, 0)
        if cantidadCarrito:
            subtotal = round(cantidadCarrito * producto.precio, 2)
            ctk.CTkLabel(
                fila, text=f"x{cantidadCarrito} · {_formatoMonto(subtotal)}",
                font=estilos.F_PEQUENA, fg_color=estilos.BADGE_STOCK,
                text_color=estilos.TEXTO_CLARO, corner_radius=8,
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
        """Suma una unidad del producto (CU9) y refresca el stock en vivo (COR2)."""
        resultado = self.controlador.agregarProd(producto.idProducto)
        if not resultado["ok"]:
            self._alerta(resultado["mensaje"])
        # COR2: el stock DISPONIBLE del listado baja en el acto.
        self.refrescarProductos()

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

        # Asignar la caja de la venta (MJ1): el monto se suma a esa caja.
        self.cajasVenta = self._obtenerCajas()
        if self.cajasVenta:
            filaCaja = ctk.CTkFrame(
                self.popupCarrito, fg_color=estilos.FONDO_PANEL,
                corner_radius=estilos.RADIO,
            )
            filaCaja.pack(fill="x", padx=16, pady=8)
            ctk.CTkLabel(
                filaCaja, text="Caja", font=estilos.F_BOLD,
                text_color=estilos.TEXTO_CLARO, anchor="w",
            ).pack(side="left", padx=(14, 8), pady=10)
            nombresCajas = [c.nombre for c in self.cajasVenta]
            self.selectorCaja = ctk.CTkOptionMenu(
                filaCaja, values=nombresCajas, font=estilos.F_NORMAL,
                fg_color=estilos.BOTON_BARRA,
                button_color=estilos.BOTON_BARRA_ACTIVO,
                button_hover_color=estilos.BOTON_BARRA_HOVER,
                dropdown_fg_color=estilos.FONDO_PANEL,
                dropdown_hover_color=estilos.BOTON_BARRA_HOVER,
                dropdown_text_color=estilos.TEXTO_CLARO,
                text_color=estilos.TEXTO_CLARO, width=220,
            )
            self.selectorCaja.set(nombresCajas[0])
            self.selectorCaja.pack(side="right", padx=(8, 14), pady=6)

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

        # Botón "x": elimina la línea completa del carrito.
        ctk.CTkButton(
            fila, text="", image=self.iconos["cerrar"], width=32, height=32,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=8,
            command=lambda p=producto: self._carritoEliminar(p),
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
        """Suma una unidad desde el popup (CU9) y refresca carrito y stock."""
        resultado = self.controlador.agregarProd(producto.idProducto)
        if not resultado["ok"]:
            self._alerta(resultado["mensaje"])
        # COR2: el stock DISPONIBLE del listado baja en el acto.
        self.refrescarProductos()
        self._refrescarCarrito()

    def _carritoQuitar(self, producto):
        """Resta una unidad desde el popup (CU9); cierra si queda vacío."""
        self.controlador.quitarProd(producto.idProducto)
        if not self.controlador.carrito:
            self.refrescarProductos()
            self._cerrarCarrito()
            return
        # COR2: al liberar unidades, el stock DISPONIBLE vuelve a subir.
        self.refrescarProductos()
        self._refrescarCarrito()

    def _carritoEliminar(self, producto):
        """Elimina la línea completa del carrito (bloqueo resuelto del
        Agente 2) y cierra el popup si el carrito queda vacío."""
        self.controlador.quitarProdCompleto(producto.idProducto)
        if not self.controlador.carrito:
            self.refrescarProductos()
            self._cerrarCarrito()
            return
        # COR2: al liberar unidades, el stock DISPONIBLE vuelve a subir.
        self.refrescarProductos()
        self._refrescarCarrito()

    # ------------------------------------------------------------------
    # Carrito: confirmar / cancelar
    # ------------------------------------------------------------------
    def _confirmarVenta(self):
        """Confirma la venta (CU10) en la caja elegida (MJ1), cierra el
        popup y refresca el catálogo."""
        resultado = self.controlador.confirmarVenta(self._cajaSeleccionada())
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
    # Popup Registrar Gasto (CU11)
    # ------------------------------------------------------------------
    def _abrirGasto(self):
        """Abre el popup para registrar un gasto secundario (CU11)."""
        if self.popupGasto is not None and self.popupGasto.winfo_exists():
            self.popupGasto.lift()
            return

        self.popupGasto = ctk.CTkToplevel(self)
        self.popupGasto.title("Registrar Gasto")
        self.popupGasto.configure(fg_color=estilos.FONDO)
        # COR9: alto ampliado para que los botones Registrar/Cancelar se
        # muestren completos (el formulario con el selector de caja MJ1 los
        # recortaba en el popup original de 430px de alto).
        self.popupGasto.geometry("460x560")
        self.popupGasto.resizable(False, False)
        self.popupGasto.transient(self.winfo_toplevel())

        # Encabezado.
        encabezado = ctk.CTkFrame(
            self.popupGasto, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        encabezado.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            encabezado, text="Registrar Gasto", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(pady=10)

        # Formulario: nombre, descripción y monto.
        formulario = ctk.CTkFrame(
            self.popupGasto, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        formulario.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            formulario, text="Nombre", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.gastoNombre = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
            placeholder_text="Ej.: Compra de insumos",
        )
        self.gastoNombre.pack(fill="x", padx=20, pady=(4, 10))
        self.gastoNombre.bind("<Return>", lambda _e: self._registrarGasto())

        ctk.CTkLabel(
            formulario, text="Descripción", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.gastoDesc = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
            placeholder_text="Ej.: Platos y vasos",
        )
        self.gastoDesc.pack(fill="x", padx=20, pady=(4, 10))
        self.gastoDesc.bind("<Return>", lambda _e: self._registrarGasto())

        ctk.CTkLabel(
            formulario, text="Monto", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.gastoMonto = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Ej.: 2.500",
        )
        self.gastoMonto.pack(fill="x", padx=20, pady=(4, 0))
        self.gastoMonto.bind("<Return>", lambda _e: self._registrarGasto())

        # Asignar la caja del gasto (MJ1): el egreso se descuenta de esa caja.
        self._gastoCajas = self._obtenerCajas()
        if self._gastoCajas:
            ctk.CTkLabel(
                formulario, text="Caja", font=estilos.F_BOLD,
                text_color=estilos.TEXTO_CLARO, anchor="w",
            ).pack(fill="x", padx=20, pady=(10, 0))
            self.gastoSelectorCaja = ctk.CTkOptionMenu(
                formulario,
                values=[c.nombre for c in self._gastoCajas],
                font=estilos.F_NORMAL,
                fg_color=estilos.BOTON_BARRA,
                button_color=estilos.BOTON_BARRA_ACTIVO,
                button_hover_color=estilos.BOTON_BARRA_HOVER,
                dropdown_fg_color=estilos.FONDO_PANEL,
                dropdown_hover_color=estilos.BOTON_BARRA_HOVER,
                dropdown_text_color=estilos.TEXTO_CLARO,
                text_color=estilos.TEXTO_CLARO,
            )
            self.gastoSelectorCaja.set(self._gastoCajas[0].nombre)
            self.gastoSelectorCaja.pack(fill="x", padx=20, pady=(4, 0))
        acciones = ctk.CTkFrame(self.popupGasto, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Registrar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._registrarGasto,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._cerrarGasto,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self.gastoNombre.focus_set()

    def _registrarGasto(self):
        """Registra el gasto (CU11) y cierra el popup si se persiste.

        Ante un error (monto inválido o saldo insuficiente) se avisa y el
        popup queda abierto para corregir los datos.
        """
        nombre = self.gastoNombre.get()
        descripcion = self.gastoDesc.get()
        monto = self._parsearMonto(self.gastoMonto.get())
        if not nombre.strip():
            self._alerta("El nombre no puede ser vacío.")
            return
        if monto is None:
            self._alerta("El monto debe ser un número válido.")
            return

        resultado = self.controlador.gasto(
            nombre, descripcion, monto, self._gastoCajaSeleccionada()
        )
        if resultado["ok"]:
            self._cerrarGasto()
            self._refrescarCaja()
            self._informar(resultado["mensaje"])
        else:
            self._alerta(resultado["mensaje"])

    # ------------------------------------------------------------------
    # Cajas (MJ1/MJ7): utilidades compartidas por carrito y gasto
    # ------------------------------------------------------------------
    def _obtenerCajas(self):
        """Devuelve las cajas de la sesión activa (MJ1/MJ7)."""
        sesion = self.controlador.sesionActiva
        if sesion is None:
            return []
        resultado = self.controlador.verCajas(sesion.idSesion)
        if resultado["ok"]:
            return resultado["datos"] or []
        return []

    def _cajaSeleccionada(self):
        """Devuelve el idCaja del selector del carrito (o None)."""
        selector = getattr(self, "selectorCaja", None)
        if selector is None:
            return None
        for caja in self.cajasVenta:
            if caja.nombre == selector.get():
                return caja.idCaja
        return None

    def _gastoCajaSeleccionada(self):
        """Devuelve el idCaja del selector del gasto (o None)."""
        selector = getattr(self, "gastoSelectorCaja", None)
        if selector is None:
            return None
        for caja in self._gastoCajas:
            if caja.nombre == selector.get():
                return caja.idCaja
        return None

    def _cerrarGasto(self):
        """Cierra el popup de gasto dejando la caja y el carrito intactos."""
        if self.popupGasto is not None and self.popupGasto.winfo_exists():
            self.popupGasto.destroy()
        self.popupGasto = None

    # ------------------------------------------------------------------
    # Conversión de entradas (mismas convenciones que config.py y login.py)
    # ------------------------------------------------------------------
    @staticmethod
    def _parsearMonto(texto):
        """Convierte el texto a float; None si no es un número válido.

        Acepta separador de miles '.' y decimal ',' (ej.: '2.500' -> 2500,
        '12,50' -> 12.5). Misma convención que el fondo inicial del login.
        """
        texto = (texto or "").strip()
        if texto == "":
            return None
        try:
            return float(texto.replace(".", "").replace(",", "."))
        except ValueError:
            return None

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