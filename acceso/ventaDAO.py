# Módulo ventaDAO.py (Agente 1 - Modelo)
# Responsable único del archivo .db, el esquema y las consultas SQL.
# Este módulo implementa el acceso a datos de ventas, caja y gastos
# (CU10/CU11/CU12/CU14) sobre la conexión compartida de mainDAO.
#
# Contrato acordado (definido por el Agente 3):
#   * registrarVenta(idSesion, fechaHora, detalles, montoNeto, cajaNueva,
#                    idCaja=None) -> int
#       Persiste Venta + sus DetalleVenta (idProducto, cantidad,
#       precio_unitario) y ACTUALIZA la columna Sesion.Caja a cajaNueva
#       dentro de la misma transacción. Devuelve ID_venta.
#       montoNeto NO se persiste: Venta no tiene columna de monto en el MER
#       y el total es derivable de los detalles (servVenta lo recalcula).
#   * registrarGasto(idSesion, nombre, monto, descripcion, fechaHora,
#                    cajaNueva, idCaja=None) -> int
#       Persiste GastoSecundario y ACTUALIZA Sesion.Caja a cajaNueva en la
#       misma transacción. El monto va FIRMADO: negativo = gasto, positivo
#       = reinserción. Devuelve ID_gasto.
#   * MJ1 (N cajas): si idCaja llega con un ID válido, la venta/gasto se
#       asigna a esa caja (se inserta su ID_caja) y se modifica el Monto de
#       esa caja con el monto de la operación (delta). Sesion.Caja sigue
#       guardando la caja total (cajaNueva, calculada por el Agente 3).
#   * verVentas(idSesion) -> list[(ID_venta, Fecha_hora,
#        list[(ID_producto, Cantidad, Precio_unitario)])]
#   * verGastos(idSesion) -> list[(ID_gasto, Nombre, Monto, Descripcion,
#        Fecha_hora)]
#   * borrarHistorial(idSesion) -> int
#       Elimina las ventas (con sus detalles por FK ON DELETE CASCADE) y
#       los gastos de la sesión. NO altera Sesion.Caja ni Producto.Stock
#       (CU14). Devuelve la cantidad de ventas borradas.
#   * obtenerEstadisticas(idSesion) -> dict
#       MJ2: calcula las estadísticas básicas de la sesión (totales en $,
#       cantidades vendidas, gastos y el más vendido). Deja la agregación
#       SQL en el DAO; la presentación (UI/Excel) la arman las demás capas.
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import sqlite3

from acceso.mainDAO import mainDAO


class ventaDAO:
    """Acceso a datos de ventas, caja y gastos (Agente 1)."""

    @staticmethod
    def registrarVenta(idSesion: int, fechaHora: str, detalles: list,
                       montoNeto: float, cajaNueva: float,
                       idCaja=None) -> int:
        """Persiste la venta, sus detalles y la caja; devuelve ID_venta (CU10).

        Todas las escrituras ocurren en UNA transacción: si algo falla,
        mainDAO._manejarError ejecuta ROLLBACK y eleva PersistenceError.

        Parámetro idCaja (MJ1): si llega un ID de caja válido, la venta se
        asigna a esa caja (columna Venta.ID_caja) y se modifica su Monto
        sumándole montoNeto. Si idCaja es None, se conserva el
        comportamiento previo (actualizar Sesion.Caja y la caja
        "Caja principal" al nuevo total cajaNueva).
        """
        mainDAO.conectar()
        try:
            if idCaja is None:
                mainDAO.cursor.execute(
                    "INSERT INTO Venta (ID_sesion, Fecha_hora) VALUES (?, ?)",
                    (idSesion, fechaHora),
                )
            else:
                mainDAO.cursor.execute(
                    "INSERT INTO Venta (ID_sesion, ID_caja, Fecha_hora) "
                    "VALUES (?, ?, ?)",
                    (idSesion, idCaja, fechaHora),
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
            if idCaja is None:
                # Comportamiento previo (COR3): la venta modifica el monto
                # actual de la caja principal en la misma transacción.
                mainDAO.cursor.execute(
                    "UPDATE Caja SET Monto = ? WHERE ID_sesion = ? "
                    "AND Nombre = 'Caja principal'",
                    (cajaNueva, idSesion),
                )
            else:
                # MJ1: la venta modifica el monto de la caja asignada.
                mainDAO.cursor.execute(
                    "UPDATE Caja SET Monto = Monto + ? WHERE ID_caja = ?",
                    (montoNeto, idCaja),
                )
            mainDAO.conn.commit()
            return idVenta
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def registrarGasto(idSesion: int, nombre: str, monto: float,
                       descripcion: str, fechaHora: str,
                       cajaNueva: float, idCaja=None) -> int:
        """Persiste gasto/reinserción y caja; devuelve ID_gasto (CU11).

        El monto llega FIRMADO desde el servicio (negativo = gasto,
        positivo = reinserción); se guarda tal cual en GastoSecundario
        y Sesion.Caja se actualiza a cajaNueva en la misma transacción.

        Parámetro idCaja (MJ1): si llega un ID de caja válido, el gasto/
        reinserción se asigna a esa caja (columna ID_caja) y se modifica
        su Monto con el monto firmado (delta). Si idCaja es None, se
        conserva el comportamiento previo (Caja principal).
        """
        mainDAO.conectar()
        try:
            if idCaja is None:
                mainDAO.cursor.execute(
                    "INSERT INTO GastoSecundario "
                    "(ID_sesion, Nombre, Monto, Descripcion, Fecha_hora) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (idSesion, nombre, monto, descripcion, fechaHora),
                )
            else:
                mainDAO.cursor.execute(
                    "INSERT INTO GastoSecundario "
                    "(ID_sesion, ID_caja, Nombre, Monto, Descripcion, "
                    "Fecha_hora) VALUES (?, ?, ?, ?, ?, ?)",
                    (idSesion, idCaja, nombre, monto, descripcion, fechaHora),
                )
            idGasto = mainDAO.cursor.lastrowid
            mainDAO.cursor.execute(
                "UPDATE Sesion SET Caja = ? WHERE ID_sesion = ?",
                (cajaNueva, idSesion),
            )
            if idCaja is None:
                # Comportamiento previo (COR3): el gasto/reinserción modifica
                # el monto actual de la caja principal en la misma transacción.
                mainDAO.cursor.execute(
                    "UPDATE Caja SET Monto = ? WHERE ID_sesion = ? "
                    "AND Nombre = 'Caja principal'",
                    (cajaNueva, idSesion),
                )
            else:
                # MJ1: el gasto/reinserción modifica la caja asignada.
                mainDAO.cursor.execute(
                    "UPDATE Caja SET Monto = Monto + ? WHERE ID_caja = ?",
                    (monto, idCaja),
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

    @staticmethod
    def obtenerEstadisticas(idSesion: int) -> dict:
        """Devuelve las estadísticas básicas de la sesión (MJ2).

        Estructura del dict retornado:
            totalEntradas: Suma en $ de las ventas + los reingresos
                (GastoSecundario con Monto > 0).
            totalSalidas: Suma en $ de los gastos (Monto < 0), en valor
                absoluto.
            cantidadProductosVendidos: Unidades de productos comunes
                vendidas directamente (Es_combo=0) MÁS las unidades de esos
                productos vendidas como componentes de combos
                (DetalleCombo).
            cantidadCombosVendidos: Unidades de combos (Es_combo=1)
                vendidas.
            cantidadGastos: Cantidad de gastos/reingresos registrados.
            productoMasVendido: (ID_producto, Nombre, Cantidad_total) del
                producto común más vendido (directas + vía combos), o None.
            comboMasVendido: (ID_combo, Nombre, Cantidad_total) del combo
                más vendido, o None.
        """
        mainDAO.conectar()
        try:
            # 1) Total de entradas $ = ventas + reingresos (Monto > 0).
            mainDAO.cursor.execute(
                "SELECT COALESCE(SUM(d.Cantidad * d.Precio_unitario), 0.0) "
                "FROM DetalleVenta d "
                "JOIN Venta v ON v.ID_venta = d.ID_venta "
                "WHERE v.ID_sesion = ?",
                (idSesion,),
            )
            totalVentas = float(mainDAO.cursor.fetchone()[0] or 0.0)
            mainDAO.cursor.execute(
                "SELECT COALESCE(SUM(Monto), 0.0) FROM GastoSecundario "
                "WHERE ID_sesion = ? AND Monto > 0",
                (idSesion,),
            )
            totalReingresos = float(mainDAO.cursor.fetchone()[0] or 0.0)
            totalEntradas = round(totalVentas + totalReingresos, 2)

            # 2) Total de salidas $ = gastos (Monto < 0) en valor absoluto.
            mainDAO.cursor.execute(
                "SELECT COALESCE(SUM(Monto), 0.0) FROM GastoSecundario "
                "WHERE ID_sesion = ? AND Monto < 0",
                (idSesion,),
            )
            totalSalidas = round(abs(float(
                mainDAO.cursor.fetchone()[0] or 0.0)), 2)

            # 3) Cantidad de productos vendidos = directas + vía combos.
            mainDAO.cursor.execute(
                "SELECT COALESCE(SUM(d.Cantidad), 0) "
                "FROM DetalleVenta d "
                "JOIN Venta v ON v.ID_venta = d.ID_venta "
                "JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "WHERE v.ID_sesion = ? AND p.Es_combo = 0",
                (idSesion,),
            )
            cantDirecta = int(mainDAO.cursor.fetchone()[0] or 0)
            mainDAO.cursor.execute(
                "SELECT COALESCE(SUM(d.Cantidad * dc.Cantidad), 0) "
                "FROM DetalleVenta d "
                "JOIN Venta v ON v.ID_venta = d.ID_venta "
                "JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "JOIN DetalleCombo dc ON dc.ID_combo = d.ID_Producto "
                "WHERE v.ID_sesion = ? AND p.Es_combo = 1",
                (idSesion,),
            )
            cantEnCombos = int(mainDAO.cursor.fetchone()[0] or 0)
            cantidadProductosVendidos = cantDirecta + cantEnCombos

            # 4) Cantidad de combos vendidos (Es_combo = 1).
            mainDAO.cursor.execute(
                "SELECT COALESCE(SUM(d.Cantidad), 0) "
                "FROM DetalleVenta d "
                "JOIN Venta v ON v.ID_venta = d.ID_venta "
                "JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "WHERE v.ID_sesion = ? AND p.Es_combo = 1",
                (idSesion,),
            )
            cantidadCombosVendidos = int(
                mainDAO.cursor.fetchone()[0] or 0)

            # 5) Cantidad de gastos/reingresos registrados.
            mainDAO.cursor.execute(
                "SELECT COUNT(*) FROM GastoSecundario WHERE ID_sesion = ?",
                (idSesion,),
            )
            cantidadGastos = int(mainDAO.cursor.fetchone()[0] or 0)

            # 6) Producto más vendido: unidades directas + las vendidas
            #    como componente de combos, agregado por producto común.
            mainDAO.cursor.execute(
                "SELECT t.ID_producto, t.Nombre, SUM(t.Cantidad) AS total "
                "FROM ("
                "    SELECT p.ID_producto, p.Nombre, d.Cantidad AS Cantidad "
                "    FROM DetalleVenta d "
                "    JOIN Venta v ON v.ID_venta = d.ID_venta "
                "    JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "    WHERE v.ID_sesion = ? AND p.Es_combo = 0"
                "    UNION ALL "
                "    SELECT dc.ID_producto, pc.Nombre, "
                "    d.Cantidad * dc.Cantidad AS Cantidad "
                "    FROM DetalleVenta d "
                "    JOIN Venta v ON v.ID_venta = d.ID_venta "
                "    JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "    JOIN DetalleCombo dc ON dc.ID_combo = p.ID_producto "
                "    JOIN Producto pc ON pc.ID_producto = dc.ID_producto "
                "    WHERE v.ID_sesion = ? AND p.Es_combo = 1"
                ") t "
                "GROUP BY t.ID_producto, t.Nombre "
                "ORDER BY total DESC, t.Nombre COLLATE NOCASE ASC "
                "LIMIT 1",
                (idSesion, idSesion),
            )
            filaProducto = mainDAO.cursor.fetchone()
            productoMasVendido = (
                (filaProducto[0], filaProducto[1], int(filaProducto[2]))
                if filaProducto is not None else None
            )

            # 7) Combo más vendido (Es_combo = 1).
            mainDAO.cursor.execute(
                "SELECT p.ID_producto, p.Nombre, SUM(d.Cantidad) AS total "
                "FROM DetalleVenta d "
                "JOIN Venta v ON v.ID_venta = d.ID_venta "
                "JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "WHERE v.ID_sesion = ? AND p.Es_combo = 1 "
                "GROUP BY p.ID_producto, p.Nombre "
                "ORDER BY total DESC, p.Nombre COLLATE NOCASE ASC "
                "LIMIT 1",
                (idSesion,),
            )
            filaCombo = mainDAO.cursor.fetchone()
            comboMasVendido = (
                (filaCombo[0], filaCombo[1], int(filaCombo[2]))
                if filaCombo is not None else None
            )

            return {
                "totalEntradas": totalEntradas,
                "totalSalidas": totalSalidas,
                "cantidadProductosVendidos": cantidadProductosVendidos,
                "cantidadCombosVendidos": cantidadCombosVendidos,
                "cantidadGastos": cantidadGastos,
                "productoMasVendido": productoMasVendido,
                "comboMasVendido": comboMasVendido,
            }
        except sqlite3.Error as err:
            mainDAO._manejarError(err)
