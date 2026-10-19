# Módulo servProd.py (Agente 3)
# Servicio de productos: aplica las validaciones de dominio (nombre, precio,
# stock inicial), orquesta las operaciones con prodDAO y devuelve productos
# como objetos instanciados de control.modelos.Producto.

from .excepciones import NombreInvalido, PrecioInvalido, ProductoNoEncontrado
from .modelos import Producto
from .servStock import validarStock


class ServProd:
    """Capa de servicios de catálogo del sistema (Agente 3)."""

    def __init__(self, prodDAO):
        self.prodDAO = prodDAO

    @staticmethod
    def _validarNombre(nombre) -> str:
        """Valida que el nombre no esté vacío y lo devuelve recortado."""
        if not isinstance(nombre, str) or not nombre.strip():
            raise NombreInvalido("El nombre del producto no puede estar vacío.")
        return nombre.strip()

    @staticmethod
    def _validarPrecio(precio) -> float:
        """Valida que el precio sea numérico >= 0 y lo devuelve como float."""
        if isinstance(precio, bool) or not isinstance(precio, (int, float)):
            raise PrecioInvalido(
                "El precio debe ser un número mayor o igual a cero."
            )
        if precio < 0:
            raise PrecioInvalido("El precio debe ser mayor o igual a cero.")
        return float(precio)

    def crearProducto(self, nombre, stockInicial, precio, idSesion) -> Producto:
        """Crea un producto en el catálogo de la sesión (CU4)."""
        nombreLimpio = self._validarNombre(nombre)
        precioLimpio = self._validarPrecio(precio)
        stockLimpio = validarStock(stockInicial)
        idProducto = self.prodDAO.crearProducto(
            nombreLimpio, stockLimpio, precioLimpio, idSesion
        )
        return Producto(idProducto, nombreLimpio, precioLimpio, stockLimpio)

    def verProductos(self, idSesion) -> list:
        """Lista los productos de la sesión SIN stock (CU5).

        El stock se completa en el controlador llamando a
        servStock.verStock por producto (decisión de diseño acordada).
        """
        filas = self.prodDAO.verProductos(idSesion)
        return [Producto(fila[0], fila[1], fila[2]) for fila in filas]

    def editarProducto(self, idProducto, nombre, precio) -> Producto:
        """Modifica nombre y precio de un producto existente (CU7)."""
        nombreLimpio = self._validarNombre(nombre)
        precioLimpio = self._validarPrecio(precio)
        fila = self.prodDAO.editarProducto(
            idProducto, nombreLimpio, precioLimpio
        )
        if fila is None:
            raise ProductoNoEncontrado(
                "No se encontró el producto a editar."
            )
        return Producto(fila[0], fila[1], fila[2])

    def eliminarProducto(self, idProducto) -> None:
        """Elimina un producto del catálogo de la sesión (CU8)."""
        filasAfectadas = self.prodDAO.eliminarProducto(idProducto)
        if filasAfectadas == 0:
            raise ProductoNoEncontrado(
                "No se encontró el producto a eliminar."
            )

    # ------------------------------------------------------------------
    # MJ4: combos
    # ------------------------------------------------------------------
    def crearCombo(self, idSesion, nombre, precio, componentes) -> int:
        """Crea un combo (producto con Es_combo=1) y sus componentes (MJ4).

        Parámetros:
            idSesion: Sesión activa.
            nombre: Nombre del combo.
            precio: Precio unitario del combo.
            componentes: lista de (idProducto, cantidad) que componen una
                unidad del combo.

        Retorna el ID_combo del combo creado.
        """
        nombreLimpio = self._validarNombre(nombre)
        precioLimpio = self._validarPrecio(precio)
        if not isinstance(componentes, (list, tuple)):
            raise ValueError("Los componentes deben ser una lista de (idProducto, cantidad).")
        for idProducto, cantidad in componentes:
            if not isinstance(cantidad, (int, float)) or cantidad <= 0:
                raise ValueError(
                    f"La cantidad del componente {idProducto} debe ser mayor a cero."
                )
        idCombo = self.prodDAO.crearCombo(
            idSesion, nombreLimpio, precioLimpio, list(componentes)
        )
        return idCombo

    def verCombos(self, idSesion) -> list:
        """Lista los combos de la sesión (MJ4).

        Retorna list[(ID_combo, Nombre, Precio)] ordenado alfabéticamente.
        """
        return self.prodDAO.verCombos(idSesion)

    def verComponentesCombo(self, idCombo) -> list:
        """Devuelve los componentes de un combo: list[(ID_producto, Cantidad)] (MJ4)."""
        return self.prodDAO.verComponentesCombo(idCombo)

    def editarCombo(self, idCombo, nombre, precio, componentes):
        """Actualiza nombre, precio y componentes de un combo (MJ4).

        Retorna (ID_combo, Nombre, Precio) o None si no es un combo existente.
        """
        nombreLimpio = self._validarNombre(nombre)
        precioLimpio = self._validarPrecio(precio)
        if not isinstance(componentes, (list, tuple)):
            raise ValueError("Los componentes deben ser una lista de (idProducto, cantidad).")
        return self.prodDAO.editarCombo(
            idCombo, nombreLimpio, precioLimpio, list(componentes)
        )

    def eliminarCombo(self, idCombo) -> int:
        """Elimina un combo y sus componentes (MJ4).

        Retorna filas afectadas (1 si era un combo, 0 si no).
        """
        return self.prodDAO.eliminarCombo(idCombo)