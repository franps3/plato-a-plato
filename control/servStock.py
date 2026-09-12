# Módulo servStock.py (Agente 3)
# Servicio de stock: aplica las validaciones de dominio sobre las existencias
# y orquesta las consultas/escrituras hacia stockDAO. Devuelve int (stock) o
# eleva DomainError ante inconsistencias operativas.

from .excepciones import ProductoNoEncontrado, StockInvalido


def validarStock(stock) -> int:
    """Valida que el stock sea entero >= 0 y devuelve el valor limpio."""
    if isinstance(stock, bool):
        raise StockInvalido(
            "El stock debe ser un número entero mayor o igual a cero."
        )
    if isinstance(stock, int):
        if stock < 0:
            raise StockInvalido("El stock debe ser mayor o igual a cero.")
        return stock
    if isinstance(stock, float) and stock >= 0 and stock.is_integer():
        return int(stock)
    raise StockInvalido(
        "El stock debe ser un número entero mayor o igual a cero."
    )


class ServStock:
    """Capa de servicios de stock del sistema (Agente 3)."""

    def __init__(self, stockDAO):
        self.stockDAO = stockDAO

    def verStock(self, idProducto) -> int:
        """Devuelve el stock actual de un producto (CU5)."""
        stock = self.stockDAO.verStock(idProducto)
        if stock is None:
            raise ProductoNoEncontrado(
                "No se encontró el producto solicitado."
            )
        return int(stock)

    def editarStock(self, idProducto, stock) -> int:
        """Actualiza el stock de un producto (CU7) y devuelve el nuevo valor."""
        stockLimpio = validarStock(stock)
        resultado = self.stockDAO.editarStock(idProducto, stockLimpio)
        if resultado is None:
            raise ProductoNoEncontrado(
                "No se encontró el producto a editar."
            )
        return int(resultado)

    def descontar(self, idProducto, cantidad) -> int:
        """Resta una cantidad del stock (CU10) y devuelve el stock restante.

        Decisión acordada: este servicio NO valida stock suficiente; esa
        validación la realiza servVenta antes de registrar la venta.
        """
        resultado = self.stockDAO.descontar(idProducto, cantidad)
        if resultado is None:
            raise ProductoNoEncontrado(
                "No se encontró el producto a descontar."
            )
        return int(resultado)