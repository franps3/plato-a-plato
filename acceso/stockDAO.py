# Módulo stockDAO.py (Agente 1 - Modelo)
# Responsable único del archivo .db, el esquema y las consultas SQL.
# Este módulo implementa el acceso a datos de existencias (Stock) sobre la
# misma tabla Producto del esquema (CU5/CU7/CU10) y usa la conexión
# compartida de mainDAO.
#
# Contrato acordado (definido por el Agente 3):
#   * verStock(idProducto) -> int | None
#       Devuelve el stock actual del producto o None si no existe. Si el
#       ítem es un combo (Es_combo=1, COR8) devuelve cuántos combos se
#       pueden armar con el stock de sus componentes
#       (MIN(Stock / Cantidad) sobre DetalleCombo).
#   * editarStock(idProducto, stock) -> int | None
#       Actualiza el stock de un producto común y devuelve el nuevo valor,
#       o None si no existe o si es un combo (los combos no tienen stock
#       propio, COR8).
#   * descontar(idProducto, cantidad) -> int | None
#       Resta cantidad del stock y devuelve el stock restante, o None si
#       el producto no existe. Si es un combo descuenta de cada componente
#       (cantidad * requerido en DetalleCombo) en una misma transacción y
#       devuelve la disponibilidad restante del combo. NO valida
#       suficiencia (eso lo hace servVenta).
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import sqlite3

from acceso.mainDAO import mainDAO


class stockDAO:
    """Acceso a datos de stock sobre la tabla Producto (Agente 1)."""

    @staticmethod
    def verStock(idProducto: int):
        """Devuelve el stock del producto o None si no existe (CU5).

        COR8: si el ítem es un combo (Es_combo=1), devuelve la cantidad de
        combos armables con el stock actual de sus componentes
        (MIN(Stock / Cantidad) sobre DetalleCombo). Si el combo no tiene
        componentes, la disponibilidad es 0.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT Stock, Es_combo FROM Producto WHERE ID_producto = ?",
                (idProducto,),
            )
            fila = mainDAO.cursor.fetchone()
            if fila is None:
                return None
            stock, esCombo = fila
            if not esCombo:
                return stock
            # COR8: stock de un combo = mínimos combos armables por componente.
            # SQLite trunca la división entre enteros (5 / 2 = 2).
            mainDAO.cursor.execute(
                "SELECT MIN(Stock / Cantidad) FROM DetalleCombo "
                "JOIN Producto ON Producto.ID_producto = "
                "DetalleCombo.ID_producto WHERE DetalleCombo.ID_combo = ?",
                (idProducto,),
            )
            minimo = mainDAO.cursor.fetchone()[0]
            return int(minimo) if minimo is not None else 0
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def editarStock(idProducto: int, stock: int):
        """Actualiza el stock de un producto común y devuelve el valor (CU7).

        COR8: los combos no tienen stock propio, por lo que editarStock
        sobre un combo (Es_combo=1) devuelve None sin tocar la base.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "UPDATE Producto SET Stock = ? "
                "WHERE ID_producto = ? AND Es_combo = 0",
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

        COR8: si el ítem es un combo (Es_combo=1), el descuento se aplica
        a cada producto componente dentro de DetalleCombo (cantidad *
        cantidadRequerida en el combo) en la misma transacción, y se
        devuelve la disponibilidad restante del combo.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT Es_combo FROM Producto WHERE ID_producto = ?",
                (idProducto,),
            )
            fila = mainDAO.cursor.fetchone()
            if fila is None:
                return None
            if fila[0]:
                # COR8: combo => descontar de cada componente.
                mainDAO.cursor.execute(
                    "SELECT ID_producto, Cantidad FROM DetalleCombo "
                    "WHERE ID_combo = ?",
                    (idProducto,),
                )
                componentes = mainDAO.cursor.fetchall()
                for idProductoComp, cantidadPorCombo in componentes:
                    mainDAO.cursor.execute(
                        "UPDATE Producto SET Stock = Stock - ? "
                        "WHERE ID_producto = ?",
                        (cantidad * cantidadPorCombo, idProductoComp),
                    )
                mainDAO.conn.commit()
                return stockDAO.verStock(idProducto)
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