# Módulo config.py (Agente 2 - Vista)
# Pantalla de Configuración de Productos del sistema "Plato a Plato".
#
# Renderiza (diseño aprobado por el usuario, basado en el PNG y en el patrón
# de la vista Venta):
#   * Barra de búsqueda (filtra localmente el listado, sin tocar el controlador)
#     + botón "+" a la derecha que abre el popup "Añadir Producto".
#   * Listado de productos (nombre, stock y precio) donde cada tarjeta tiene
#     un botón de configuración (engranaje) que abre el popup "Modificar
#     Producto"; desde ahí también se puede eliminar el producto.
#   * Popup "Añadir Producto" (CU4): campos nombre, precio y stock inicial.
#   * Popup "Modificar Producto" (CU7): edita nombre, precio y stock, y
#     ofrece el botón "Eliminar producto".
#   * Popup "Eliminar Producto" (CU8): confirma la baja del producto.
#
# Regla de rol: cero lógica operativa. Sólo lee entradas, invoca métodos del
# controlador y refresca componentes según el resultado.
#
# Notas de decisiones acordadas con el usuario:
#   * El botón "+" de la barra superior reemplaza al carrito de la vista Venta
#     y abre el popup de alta de producto.
#   * El botón de configuración (engranaje) reemplaza al botón "+" de cada
#     tarjeta y abre el popup de modificación.
#   * En "Modificar Producto" se persiste primero nombre/precio (editarProducto)
#     y luego stock (editarStock); si el stock es rechazado, se avisa y el
#     popup queda abierto para corregir el valor.
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


class VistaConfigProductos(ctk.CTkFrame):
    """Pantalla de configuración del catálogo (CU4-CU8)."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=estilos.FONDO)
        self.controlador = controlador
        self.productos = []          # lista de Producto vigente
        self.filtro = ""             # texto de búsqueda actual
        self.popupAlta = None        # CTkToplevel "Añadir Producto"
        self.popupModificar = None   # CTkToplevel "Modificar Producto"
        self.popupEliminar = None    # CTkToplevel "Eliminar Producto"
        self.productoSeleccionado = None
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
            "mas": self._icono(rutas["mas"], 24),
            "configuracion": self._icono(rutas["configuracion"], 18),
        }

    @staticmethod
    def _icono(ruta, tam):
        """Construye un CTkImage cuadrado de lado 'tam' desde un PNG."""
        return ctk.CTkImage(light_image=Image.open(ruta), size=(tam, tam))

# ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _construir(self):
        """Arma la barra superior (búsqueda + botón agregar) y el panel."""
        # --- Barra de búsqueda + botón "+" (agregar producto) ---
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

        self.botonAgregar = ctk.CTkButton(
            barraSup, text="", image=self.iconos["mas"],
            width=44, height=44, fg_color=estilos.BOTON_CLARO,
            hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=estilos.RADIO, command=self._abrirAlta,
        )
        self.botonAgregar.pack(side="left", padx=(10, 0))

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
        """Crea la tarjeta de un producto: nombre, stock, precio y engranaje."""
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

        # Botón de configuración (abre el popup de modificación/eliminación).
        ctk.CTkButton(
            fila, text="", image=self.iconos["configuracion"],
            width=32, height=32,
            fg_color=estilos.BOTON_CLARO, hover_color=estilos.BOTON_CLARO_HOVER,
            corner_radius=8,
            command=lambda p=producto: self._abrirModificar(p),
        ).pack(side="left", padx=(6, 12))

    # ------------------------------------------------------------------
    # Búsqueda local (filtro sin controlador)
    # ------------------------------------------------------------------
    def _alCambiarBusqueda(self, _evento=None):
        """Filtra la lista localmente ante cada pulsación en la búsqueda."""
        self.filtro = self.entradaBusqueda.get()
        self._renderProductos()

    # ------------------------------------------------------------------
    # Gestión de popups (sólo uno abierto a la vez)
    # ------------------------------------------------------------------
    def _cerrarPopups(self):
        """Cierra los popups abiertos de la vista, si los hay."""
        for popup in (self.popupAlta, self.popupModificar, self.popupEliminar):
            if popup is not None and popup.winfo_exists():
                popup.destroy()
        self.popupAlta = None
        self.popupModificar = None
        self.popupEliminar = None

# ------------------------------------------------------------------
    # Popup Añadir Producto (CU4)
    # ------------------------------------------------------------------
    def _abrirAlta(self):
        """Abre el popup con el formulario para crear un producto (CU4)."""
        self._cerrarPopups()
        self.popupAlta = ctk.CTkToplevel(self)
        self.popupAlta.title("Añadir Producto")
        self.popupAlta.configure(fg_color=estilos.FONDO)
        self.popupAlta.geometry("460x560")
        self.popupAlta.resizable(False, False)
        self.popupAlta.transient(self.winfo_toplevel())

        # Encabezado.
        encabezado = ctk.CTkFrame(
            self.popupAlta, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        encabezado.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            encabezado, text="Añadir Producto", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(pady=10)

        # Formulario: nombre, precio y stock inicial.
        formulario = ctk.CTkFrame(
            self.popupAlta, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        formulario.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            formulario, text="Nombre", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.altaNombre = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Nombre del producto",
        )
        self.altaNombre.pack(fill="x", padx=20, pady=(4, 10))
        self.altaNombre.bind("<Return>", lambda _e: self._guardarAlta())

        ctk.CTkLabel(
            formulario, text="Precio", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.altaPrecio = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Ej.: 2.500",
        )
        self.altaPrecio.pack(fill="x", padx=20, pady=(4, 10))
        self.altaPrecio.bind("<Return>", lambda _e: self._guardarAlta())

        ctk.CTkLabel(
            formulario, text="Stock inicial", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.altaStock = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO, placeholder_text="Ej.: 10",
        )
        self.altaStock.pack(fill="x", padx=20, pady=(4, 0))
        self.altaStock.bind("<Return>", lambda _e: self._guardarAlta())

        # Botones Agregar / Cancelar.
        acciones = ctk.CTkFrame(self.popupAlta, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Agregar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._guardarAlta,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._cerrarAlta,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self.altaNombre.focus_set()

    def _guardarAlta(self):
        """Crea el producto (CU4) y refresca el catálogo si se persiste."""
        nombre = self.altaNombre.get()
        precio = self._parsearPrecio(self.altaPrecio.get())
        stock = self._parsearStock(self.altaStock.get())
        if not nombre.strip():
            self._alerta("El nombre no puede ser vacío.")
            return
        if precio is None:
            self._alerta("El precio debe ser un número válido.")
            return
        if stock is None:
            self._alerta("El stock debe ser un número entero válido.")
            return

        resultado = self.controlador.crearProducto(nombre, stock, precio)
        if resultado["ok"]:
            self._cerrarAlta()
            self.refrescarProductos()
            self._informar(resultado["mensaje"])
        else:
            self._alerta(resultado["mensaje"])

    def _cerrarAlta(self):
        """Cierra el popup de alta dejando el catálogo intacto."""
        if self.popupAlta is not None and self.popupAlta.winfo_exists():
            self.popupAlta.destroy()
        self.popupAlta = None

# ------------------------------------------------------------------
    # Popup Modificar Producto (CU7) + acceso a Eliminar (CU8)
    # ------------------------------------------------------------------
    def _abrirModificar(self, producto):
        """Abre el popup con los datos del producto para editarlos (CU7)."""
        self._cerrarPopups()
        self.productoSeleccionado = producto
        self.popupModificar = ctk.CTkToplevel(self)
        self.popupModificar.title("Modificar Producto")
        self.popupModificar.configure(fg_color=estilos.FONDO)
        self.popupModificar.geometry("460x560")
        self.popupModificar.resizable(False, False)
        self.popupModificar.transient(self.winfo_toplevel())

        # Encabezado.
        encabezado = ctk.CTkFrame(
            self.popupModificar, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        encabezado.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            encabezado, text="Modificar Producto", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(pady=10)

        # Formulario precargado con los datos actuales.
        formulario = ctk.CTkFrame(
            self.popupModificar, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        formulario.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            formulario, text="Nombre", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.modNombre = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
        )
        self.modNombre.insert(0, producto.nombre)
        self.modNombre.pack(fill="x", padx=20, pady=(4, 10))
        self.modNombre.bind("<Return>", lambda _e: self._guardarModificar())

        ctk.CTkLabel(
            formulario, text="Precio", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.modPrecio = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
        )
        self.modPrecio.insert(0, f"{producto.precio:g}")
        self.modPrecio.pack(fill="x", padx=20, pady=(4, 10))
        self.modPrecio.bind("<Return>", lambda _e: self._guardarModificar())

        ctk.CTkLabel(
            formulario, text="Stock", font=estilos.F_BOLD,
            text_color=estilos.TEXTO_CLARO, anchor="w",
        ).pack(fill="x", padx=20)
        self.modStock = ctk.CTkEntry(
            formulario, font=estilos.F_NORMAL, height=40,
            fg_color=estilos.ENTRADA, text_color=estilos.ENTRADA_TEXTO,
            corner_radius=estilos.RADIO,
        )
        self.modStock.insert(0, str(producto.stock))
        self.modStock.pack(fill="x", padx=20, pady=(4, 0))
        self.modStock.bind("<Return>", lambda _e: self._guardarModificar())

        # Botones: Eliminar producto / Guardar / Cancelar.
        acciones = ctk.CTkFrame(self.popupModificar, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Eliminar producto", font=estilos.F_PEQUENA,
            height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=lambda p=producto: self._abrirEliminar(p),
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Guardar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._guardarModificar,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._cerrarModificar,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        self.modNombre.focus_set()

    def _guardarModificar(self):
        """Guarda los cambios (CU7) y refresca el catálogo si se persiste."""
        producto = self.productoSeleccionado
        nombre = self.modNombre.get()
        precio = self._parsearPrecio(self.modPrecio.get())
        stock = self._parsearStock(self.modStock.get())
        if not nombre.strip():
            self._alerta("El nombre no puede ser vacío.")
            return
        if precio is None:
            self._alerta("El precio debe ser un número válido.")
            return
        if stock is None:
            self._alerta("El stock debe ser un número entero válido.")
            return

        # Primero nombre/precio; si el stock es rechazado, se avisa y el
        # popup queda abierto para corregir el valor.
        resultado = self.controlador.editarProducto(
            producto.idProducto, nombre, precio
        )
        if not resultado["ok"]:
            self._alerta(resultado["mensaje"])
            return

        resultadoStock = self.controlador.editarStock(
            producto.idProducto, stock
        )
        if not resultadoStock["ok"]:
            self._alerta(resultadoStock["mensaje"])
        else:
            self._cerrarModificar()
        self.refrescarProductos()

    def _cerrarModificar(self):
        """Cierra el popup de modificación dejando el catálogo intacto."""
        if self.popupModificar is not None and self.popupModificar.winfo_exists():
            self.popupModificar.destroy()
        self.popupModificar = None

# ------------------------------------------------------------------
    # Popup Eliminar Producto (CU8)
    # ------------------------------------------------------------------
    def _abrirEliminar(self, producto):
        """Abre el popup de confirmación de baja de un producto (CU8)."""
        self._cerrarPopups()
        self.productoSeleccionado = producto
        self.popupEliminar = ctk.CTkToplevel(self)
        self.popupEliminar.title("Eliminar Producto")
        self.popupEliminar.configure(fg_color=estilos.FONDO)
        self.popupEliminar.geometry("440x270")
        self.popupEliminar.resizable(False, False)
        self.popupEliminar.transient(self.winfo_toplevel())

        # Encabezado.
        encabezado = ctk.CTkFrame(
            self.popupEliminar, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        encabezado.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            encabezado, text="Eliminar Producto", font=estilos.F_TITULO,
            text_color=estilos.TEXTO_CLARO,
        ).pack(pady=10)

        # Mensaje de confirmación.
        mensaje = ctk.CTkFrame(
            self.popupEliminar, fg_color=estilos.FONDO_PANEL,
            corner_radius=estilos.RADIO,
        )
        mensaje.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(
            mensaje,
            text=f"¿Seguro que deseas eliminar \"{producto.nombre}\" "
                 "de la lista?\nEsta acción no se puede deshacer.",
            font=estilos.F_NORMAL, text_color=estilos.TEXTO_CLARO,
            wraplength=380, justify="center",
        ).pack(padx=20, pady=16)

        # Botones Eliminar / Cancelar.
        acciones = ctk.CTkFrame(self.popupEliminar, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            acciones, text="Eliminar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._confirmarEliminacion,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        ctk.CTkButton(
            acciones, text="Cancelar", font=estilos.F_BOLD, height=44,
            fg_color=estilos.BOTON_BARRA, hover_color=estilos.BOTON_BARRA_HOVER,
            command=self._cancelarEliminacion,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

    def _confirmarEliminacion(self):
        """Da de baja el producto (CU8), refresca y cierra los popups."""
        producto = self.productoSeleccionado
        resultado = self.controlador.eliminarProducto(producto.idProducto)
        self._cerrarPopups()
        if resultado["ok"]:
            self.refrescarProductos()
            self._informar(resultado["mensaje"])
        else:
            self._alerta(resultado["mensaje"])

    def _cancelarEliminacion(self):
        """Cancela la baja: cierra el popup sin borrar nada (CU8)."""
        self._cerrarPopups()

# ------------------------------------------------------------------
    # Conversión de entradas (mismas convenciones que login.py)
    # ------------------------------------------------------------------
    @staticmethod
    def _parsearPrecio(texto):
        """Convierte el texto a float; None si no es numérico.

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

    @staticmethod
    def _parsearStock(texto):
        """Convierte el texto a int; None si no es un entero válido."""
        texto = (texto or "").strip()
        if texto == "":
            return None
        try:
            return int(texto)
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