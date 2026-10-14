# Módulo ventaDAO.py (Agente 1 - Modelo)
# Responsable único del archivo .db, el esquema y las consultas SQL.
# Este módulo implementa el acceso a datos de ventas, caja y gastos
# (CU10/CU11/CU12/CU14) sobre la conexión compartida de mainDAO.
#
# Contrato acordado (definido por el Agente 3):
#   * registrarVenta(idSesion, fechaHora, detalles, montoNeto, cajaNueva) -> int
#       Persiste Venta + sus DetalleVenta (idProducto, cantidad,
#       precio_unitario) y ACTUALIZA la columna Sesion.Caja a cajaNueva
#       dentro de la misma transacción. Devuelve ID_venta.
#       montoNeto NO se persiste: Venta no tiene columna de monto en el MER
#       y el total es derivable de los detalles (servVenta lo recalcula).
#   * registrarGasto(idSesion, nombre, monto, descripcion, fechaHora,
#                    cajaNueva) -> int
#       Persiste GastoSecundario y ACTUALIZA Sesion.Caja a cajaNueva en la
#       misma transacción. El monto va FIRMADO: negativo = gasto, positivo
#       = reinserción. Devuelve ID_gasto.
#   * verVentas(idSesion) -> list[(ID_venta, Fecha_hora,
#        list[(ID_producto, Cantidad, Precio_unitario)])]
#   * verGastos(idSesion) -> list[(ID_gasto, Nombre, Monto, Descripcion,
#        Fecha_hora)]
#   * borrarHistorial(idSesion) -> int
#       Elimina las ventas (con sus detalles por FK ON DELETE CASCADE) y
#       los gastos de la sesión. NO altera Sesion.Caja ni Producto.Stock
#       (CU14). Devuelve la cantidad de ventas borradas.
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import sqlite3

from acceso.mainDAO import mainDAO


class ventaDAO:
    """Acceso a datos de ventas, caja y gastos (Agente 1)."""

    @staticmethod
    def registrarVenta(idSesion: int, fechaHora: str, detalles: list,
                       montoNeto: float, cajaNueva: float) -> int:
        """Persiste la venta, sus detalles y la caja; devuelve ID_venta (CU10).

        Todas las escrituras ocurren en UNA transacción: si algo falla,
        mainDAO._manejarError ejecuta ROLLBACK y eleva PersistenceError.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "INSERT INTO Venta (ID_sesion, Fecha_hora) VALUES (?, ?)",
                (idSesion, fechaHora),
            )
            idVenta = mainDAO.cursor.lastrowid
            filas = [
                (idVenta, idProducto, cantidad, precioUnitario)
                for (idProducto, cantidad, precioUnitario) in detalles
            ]
            mainDAO.cursor.executemany(
                "INSERT INTO DetalleVenta "
                "(ID_venta, ID_Producto, Cantidad, Precio_unitario) "
                "VALUES (?, ?, ?, ?)",
                filas,
            )
            mainDAO.cursor.execute(
                "UPDATE Sesion SET Caja = ? WHERE ID_sesion = ?",
                (cajaNueva, idSesion),
            )
            # COR3 / preparación MJ1 (N cajas): la venta modifica el monto
            # actual de la caja principal (Monto) en la misma transacción.
            mainDAO.cursor.execute(
                "UPDATE Caja SET Monto = ? WHERE ID_sesion = ? "
                "AND Nombre = 'Caja principal'",
                (cajaNueva, idSesion),
            )
            mainDAO.conn.commit()
            return idVenta
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def registrarGasto(idSesion: int, nombre: str, monto: float,
                       descripcion: str, fechaHora: str,
                       cajaNueva: float) -> int:
        """Persiste gasto/reinserción y caja; devuelve ID_gasto (CU11).

        El monto llega FIRMADO desde el servicio (negativo = gasto,
        positivo = reinserción); se guarda tal cual en GastoSecundario
        y Sesion.Caja se actualiza a cajaNueva en la misma transacción.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "INSERT INTO GastoSecundario "
                "(ID_sesion, Nombre, Monto, Descripcion, Fecha_hora) "
                "VALUES (?, ?, ?, ?, ?)",
                (idSesion, nombre, monto, descripcion, fechaHora),
            )
            idGasto = mainDAO.cursor.lastrowid
            mainDAO.cursor.execute(
                "UPDATE Sesion SET Caja = ? WHERE ID_sesion = ?",
                (cajaNueva, idSesion),
            )
            # COR3 / preparación MJ1 (N cajas): el gasto/reinserción modifica
            # el monto actual de la caja principal (Monto) en la misma transacción.
            mainDAO.cursor.execute(
                "UPDATE Caja SET Monto = ? WHERE ID_sesion = ? "
                "AND Nombre = 'Caja principal'",
                (cajaNueva, idSesion),
            )
            mainDAO.conn.commit()
            return idGasto
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def verVentas(idSesion: int):
        """Devuelve las ventas de la sesión con sus detalles (CU12).

        Formato de cada tupla:
        (ID_venta, Fecha_hora, list[(ID_producto, Cantidad, Precio_unitario)])
        Los detalles se traen con UNA sola consulta JOIN para la sesión
        (evita el problema N+1) y se agrupan en Python por ID_venta.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_venta, Fecha_hora FROM Venta "
                "WHERE ID_sesion = ? "
                "ORDER BY Fecha_hora, ID_venta",
                (idSesion,),
            )
            ventas = [tuple(fila) for fila in mainDAO.cursor.fetchall()]
            if not ventas:
                return []

            mainDAO.cursor.execute(
                "SELECT d.ID_venta, d.ID_Producto, d.Cantidad, "
                "d.Precio_unitario "
                "FROM DetalleVenta d "
                "JOIN Venta v ON v.ID_venta = d.ID_venta "
                "WHERE v.ID_sesion = ? "
                "ORDER BY d.ID_venta, d.ID_Producto",
                (idSesion,),
            )
            agrupado = {}
            for idVenta, idProducto, cantidad, precio in \
                    mainDAO.cursor.fetchall():
                agrupado.setdefault(idVenta, []).append(
                    (idProducto, cantidad, precio)
                )

            return [
                (idVenta, fechaHora, agrupado.get(idVenta, []))
                for idVenta, fechaHora in ventas
            ]
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def verGastos(idSesion: int):
        """Devuelve los gastos/reinserciones de la sesión (CU12).

        Formato: (ID_gasto, Nombre, Monto, Descripcion, Fecha_hora).
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_gasto, Nombre, Monto, Descripcion, Fecha_hora "
                "FROM GastoSecundario "
                "WHERE ID_sesion = ? "
                "ORDER BY Fecha_hora, ID_gasto",
                (idSesion,),
            )
            return [tuple(fila) for fila in mainDAO.cursor.fetchall()]
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def borrarHistorial(idSesion: int) -> int:
        """Limpia los movimientos de la sesión sin alterar stock ni caja (CU14).

        Postcondición (docs/CUs.md): elimina el registro de ventas (y sus
        detalles por FK ON DELETE CASCADE) y de gastos de la sesión,
        PRESERVANDO Producto.Stock y Sesion.Caja. Devuelve la cantidad de
        ventas borradas (contrato acordado con el Agente 3).
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT COUNT(*) FROM Venta WHERE ID_sesion = ?",
                (idSesion,),
            )
            cantVentas = mainDAO.cursor.fetchone()[0]

            mainDAO.cursor.execute(
                "DELETE FROM Venta WHERE ID_sesion = ?",
                (idSesion,),
            )
            mainDAO.cursor.execute(
                "DELETE FROM GastoSecundario WHERE ID_sesion = ?",
                (idSesion,),
            )
            mainDAO.conn.commit()
            return int(cantVentas)
        except sqlite3.Error as err:
            mainDAO._manejarError(err)
