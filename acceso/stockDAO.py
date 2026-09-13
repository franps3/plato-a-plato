# Módulo stockDAO.py (Agente 1 - Modelo)
# Responsable único del archivo .db, el esquema y las consultas SQL.
# Este módulo implementa el acceso a datos de existencias (Stock) sobre la
# misma tabla Producto del esquema (CU5/CU7/CU10) y usa la conexión
# compartida de mainDAO.
#
# Contrato acordado (definido por el Agente 3):
#   * verStock(idProducto) -> int | None
#       Devuelve el stock actual del producto o None si no existe.
#   * editarStock(idProducto, stock) -> int | None
#       Actualiza el stock y devuelve el nuevo valor, o None si no existe.
#   * descontar(idProducto, cantidad) -> int | None
#       Resta cantidad del stock y devuelve el stock restante, o None si
#       el producto no existe. NO valida suficiencia (eso lo hace servVenta).
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import sqlite3

from acceso.mainDAO import mainDAO


class stockDAO:
    """Acceso a datos de stock sobre la tabla Producto (Agente 1)."""

    @staticmethod
    def verStock(idProducto: int):
        """Devuelve el stock del producto o None si no existe (CU5)."""
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT Stock FROM Producto WHERE ID_producto = ?",
                (idProducto,),
            )
            fila = mainDAO.cursor.fetchone()
            return fila[0] if fila is not None else None
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def editarStock(idProducto: int, stock: int):
        """Actualiza el stock y devuelve el nuevo valor, o None si no existe (CU7)."""
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "UPDATE Producto SET Stock = ? WHERE ID_producto = ?",
                (stock, idProducto),
            )
            if mainDAO.cursor.rowcount == 0:
                return None
            mainDAO.conn.commit()
            return stock
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def descontar(idProducto: int, cantidad: int):
        """Resta cantidad al stock; devuelve el resto o None si no existe (CU10).

        Decisión acordada: este DAO NO valida stock suficiente; esa
        validación la realiza servVenta antes de registrar la venta.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "UPDATE Producto SET Stock = Stock - ? WHERE ID_producto = ?",
                (cantidad, idProducto),
            )
            if mainDAO.cursor.rowcount == 0:
                return None
            mainDAO.conn.commit()
            mainDAO.cursor.execute(
                "SELECT Stock FROM Producto WHERE ID_producto = ?",
                (idProducto,),
            )
            fila = mainDAO.cursor.fetchone()
            return fila[0] if fila is not None else None
        except sqlite3.Error as err:
            mainDAO._manejarError(err)