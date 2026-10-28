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
#   * MJ4 (combos): un combo se persiste como un Producto con Es_combo=1
#     más sus componentes en DetalleCombo (ID_combo, ID_producto,
#     Cantidad). Métodos: crearCombo, verCombos, verComponentesCombo,
#     editarCombo y eliminarCombo. DetalleVenta no cambia: el combo se
#     vende como un producto más ("agregar a una venta como un producto
#     más"). verProductos() los incluye junto con los productos comunes.
#     COR8: el combo NO tiene stock propio (crearCombo ya no recibe
#     stock); su disponibilidad se deriva del stock de sus componentes.
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

    @staticmethod
    def crearCombo(idSesion: int, nombre: str, precio: float,
                   componentes: list) -> int:
        """Persiste un combo (Producto Es_combo=1) + sus componentes (MJ4).

        Parámetros:
            componentes: lista de tuplas (ID_producto, Cantidad) con los
                productos y cantidades que componen UNA unidad del combo.

        COR8: el combo NO tiene stock propio; su fila Producto se persiste
        con Stock=0 siempre. La disponibilidad se deriva del stock de sus
        componentes (stockDAO.verStock lo calcula vía DetalleCombo).

        Toda la escritura ocurre en UNA transacción: si algo falla,
        mainDAO._manejarError ejecuta ROLLBACK y eleva PersistenceError.
        Devuelve el ID_producto del combo creado.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "INSERT INTO Producto "
                "(ID_sesion, Nombre, Stock, Precio, Es_combo) "
                "VALUES (?, ?, 0, ?, 1)",
                (idSesion, nombre, precio),
            )
            idCombo = mainDAO.cursor.lastrowid
            filas = [
                (idCombo, idProducto, cantidad)
                for (idProducto, cantidad) in componentes
            ]
            mainDAO.cursor.executemany(
                "INSERT INTO DetalleCombo "
                "(ID_combo, ID_producto, Cantidad) VALUES (?, ?, ?)",
                filas,
            )
            mainDAO.conn.commit()
            return idCombo
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def verCombos(idSesion: int):
        """Devuelve los combos de la sesión: list[(ID_combo, Nombre, Precio)].

        Un combo es un Producto con Es_combo=1 (MJ4). Orden alfabético por
        nombre sin distinguir mayúsculas, igual que verProductos.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_producto, Nombre, Precio FROM Producto "
                "WHERE ID_sesion = ? AND Es_combo = 1 "
                "ORDER BY Nombre COLLATE NOCASE",
                (idSesion,),
            )
            return [tuple(fila) for fila in mainDAO.cursor.fetchall()]
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def verComponentesCombo(idCombo: int):
        """Devuelve los componentes de un combo: list[(ID_producto, Cantidad)].

        Consulta sobre DetalleCombo (MJ4): cada fila indica qué producto y
        cuántas unidades componen UNA unidad del combo.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_producto, Cantidad FROM DetalleCombo "
                "WHERE ID_combo = ? ORDER BY ID_producto",
                (idCombo,),
            )
            return [tuple(fila) for fila in mainDAO.cursor.fetchall()]
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def editarCombo(idCombo: int, nombre: str, precio: float,
                    componentes: list):
        """Actualiza nombre, precio y componentes de un combo (MJ4).

        Reemplaza los componentes (DELETE + INSERT) en la MISMA transacción
        para no dejar el combo a medias. Devuelve (ID_combo, Nombre, Precio)
        o None si el ID no corresponde a un combo (Es_combo=1).
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "UPDATE Producto SET Nombre = ?, Precio = ? "
                "WHERE ID_producto = ? AND Es_combo = 1",
                (nombre, precio, idCombo),
            )
            if mainDAO.cursor.rowcount == 0:
                return None
            mainDAO.cursor.execute(
                "DELETE FROM DetalleCombo WHERE ID_combo = ?",
                (idCombo,),
            )
            filas = [
                (idCombo, idProducto, cantidad)
                for (idProducto, cantidad) in componentes
            ]
            mainDAO.cursor.executemany(
                "INSERT INTO DetalleCombo "
                "(ID_combo, ID_producto, Cantidad) VALUES (?, ?, ?)",
                filas,
            )
            mainDAO.conn.commit()
            return (idCombo, nombre, precio)
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def eliminarCombo(idCombo: int) -> int:
        """Elimina un combo (Producto Es_combo=1) y sus componentes (MJ4).

        La FK ON DELETE CASCADE de DetalleCombo limpia los componentes.
        Devuelve filas afectadas (1 si era un combo; 0 si no existía o era
        un producto común). Los combos ya vendidos también se limpian por la
        FK CASCADE de DetalleVenta.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "DELETE FROM Producto WHERE ID_producto = ? AND Es_combo = 1",
                (idCombo,),
            )
            mainDAO.conn.commit()
            return mainDAO.cursor.rowcount
        except sqlite3.Error as err:
            mainDAO._manejarError(err)