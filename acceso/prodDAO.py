# Módulo prodDAO.py (contrato de interfaz - a implementar por Agente 1)
# Agente 1 es el responsable único del archivo .db, el esquema y las
# consultas SQL. Este módulo define el contrato que el controlador
# (Agente 3) espera de prodDAO para el catálogo (CU4/CU5/CU7/CU8).
#
# Contrato acordado:
#   * crearProducto(nombre, stock, precio, idSesion) -> int
#       Persiste el producto en la sesión y devuelve su ID_producto.
#   * verProductos(idSesion) -> list[(ID_producto, Nombre, Precio)]
#       Devuelve los productos de la sesión SIN stock; el stock se resuelve
#       llamando a stockDAO.verStock por producto (decisión de diseño).
#   * editarProducto(idProducto, nombre, precio) -> (ID, Nombre, Precio)|None
#       Actualiza nombre y precio; None si el producto no existe.
#   * eliminarProducto(idProducto) -> int
#       Elimina el producto y devuelve filas afectadas (1 si existía).
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).


class prodDAO:
    """Contrato de acceso a datos de productos (implementado por Agente 1)."""

    @staticmethod
    def crearProducto(nombre: str, stock: int, precio: float, idSesion: int) -> int:
        """Persiste el producto y devuelve su ID_producto."""
        raise NotImplementedError(
            "prodDAO.crearProducto: implementación pendiente del Agente 1."
        )

    @staticmethod
    def verProductos(idSesion: int):
        """Devuelve list[(ID_producto, Nombre, Precio)] de la sesión."""
        raise NotImplementedError(
            "prodDAO.verProductos: implementación pendiente del Agente 1."
        )

    @staticmethod
    def editarProducto(idProducto: int, nombre: str, precio: float):
        """Devuelve (ID, Nombre, Precio) actualizado o None si no existe."""
        raise NotImplementedError(
            "prodDAO.editarProducto: implementación pendiente del Agente 1."
        )

    @staticmethod
    def eliminarProducto(idProducto: int) -> int:
        """Devuelve la cantidad de filas afectadas (1 si existía)."""
        raise NotImplementedError(
            "prodDAO.eliminarProducto: implementación pendiente del Agente 1."
        )