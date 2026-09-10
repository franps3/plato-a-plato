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