# Módulo prodDAO.py (Agente 1 - Modelo)
# Responsable único del archivo .db, el esquema y las consultas SQL.
# Este módulo implementa el acceso a datos del catálogo de productos
# (CU4/CU5/CU7/CU8) sobre la conexión compartida de mainDAO.
#
# Contrato acordado (definido por el Agente 3):
#   * crearProducto(nombre, stock, precio, idSesion) -> int
#       Persiste el producto en la sesión y devuelve su ID_producto.
#   * verProductos(idSesion) -> list[(ID_producto, Nombre, Precio)]
#       Devuelve los productos de la sesión SIN stock; el stock se resuelve
#       llamando a stockDAO.verStock por producto (decisión de diseño).
#       Orden alfabético por nombre sin distinguir mayúsculas.
#   * editarProducto(idProducto, nombre, precio) -> (ID, Nombre, Precio)|None
#       Actualiza nombre y precio; None si el producto no existe.
#   * eliminarProducto(idProducto) -> int
#       Elimina el producto y devuelve filas afectadas (1 si existía).
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import sqlite3

from acceso.mainDAO import mainDAO


class prodDAO:
    """Acceso a datos de productos del catálogo (Agente 1)."""

    @staticmethod
    def crearProducto(nombre: str, stock: int, precio: float, idSesion: int) -> int:
        """Persiste el producto y devuelve su ID_producto (CU4)."""
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "INSERT INTO Producto (ID_sesion, Nombre, Stock, Precio) "
                "VALUES (?, ?, ?, ?)",
                (idSesion, nombre, stock, precio),
            )
            mainDAO.conn.commit()
            return mainDAO.cursor.lastrowid
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def verProductos(idSesion: int):
        """Devuelve list[(ID_producto, Nombre, Precio)] de la sesión (CU5).

        El listado se ordena alfabéticamente por nombre sin distinguir
        mayúsculas (decisión acordada). El stock se resuelve aparte vía
        stockDAO.verStock por producto.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_producto, Nombre, Precio FROM Producto "
                "WHERE ID_sesion = ? "
                "ORDER BY Nombre COLLATE NOCASE",
                (idSesion,),
            )
            return [tuple(fila) for fila in mainDAO.cursor.fetchall()]
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def editarProducto(idProducto: int, nombre: str, precio: float):
        """Actualiza nombre y precio; devuelve (ID, Nombre, Precio) o None (CU7)."""
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "UPDATE Producto SET Nombre = ?, Precio = ? "
                "WHERE ID_producto = ?",
                (nombre, precio, idProducto),
            )
            if mainDAO.cursor.rowcount == 0:
                return None
            mainDAO.conn.commit()
            mainDAO.cursor.execute(
                "SELECT ID_producto, Nombre, Precio FROM Producto "
                "WHERE ID_producto = ?",
                (idProducto,),
            )
            fila = mainDAO.cursor.fetchone()
            return tuple(fila) if fila is not None else None
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def eliminarProducto(idProducto: int) -> int:
        """Elimina el producto y devuelve filas afectadas (1 si existía) (CU8)."""
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "DELETE FROM Producto WHERE ID_producto = ?",
                (idProducto,),
            )
            mainDAO.conn.commit()
            return mainDAO.cursor.rowcount
        except sqlite3.Error as err:
            mainDAO._manejarError(err)