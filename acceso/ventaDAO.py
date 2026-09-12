# Módulo ventaDAO.py (contrato de interfaz - a implementar por Agente 1)
# Agente 1 es el responsable único del archivo .db, el esquema y las
# consultas SQL. Este módulo define el contrato que el controlador
# (Agente 3) espera de ventaDAO para ventas, caja y gastos (CU10/CU11/CU12).
#
# Contrato acordado:
#   * registrarVenta(idSesion, fechaHora, detalles, montoNeto, cajaNueva) -> int
#       Persiste Venta + sus DetalleVenta (idProducto, cantidad,
#       precio_unitario) y ACTUALIZA la columna Sesion.Caja a cajaNueva
#       dentro de la misma transacción. Devuelve ID_venta.
#   * registrarGasto(idSesion, nombre, monto, descripcion, fechaHora,
#                    cajaNueva) -> int
#       Persiste GastoSecundario y ACTUALIZA Sesion.Caja a cajaNueva en la
#       misma transacción. El monto va FIRMADO: negativo = gasto, positivo
#       = reinserción. Devuelve ID_gasto.
#   * verVentas(idSesion) -> list[(ID_venta, Fecha_hora,
#        list[(ID_producto, Cantidad, Precio_unitario)])]
#   * verGastos(idSesion) -> list[(ID_gasto, Nombre, Monto, Descripcion,
#        Fecha_hora)]
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).


class ventaDAO:
    """Contrato de acceso a datos de ventas y caja (implementado por Agente 1)."""

    @staticmethod
    def registrarVenta(idSesion: int, fechaHora: str, detalles: list,
                       montoNeto: float, cajaNueva: float) -> int:
        """Persiste la venta, sus detalles y la caja; devuelve ID_venta."""
        raise NotImplementedError(
            "ventaDAO.registrarVenta: implementación pendiente del Agente 1."
        )

    @staticmethod
    def registrarGasto(idSesion: int, nombre: str, monto: float,
                       descripcion: str, fechaHora: str,
                       cajaNueva: float) -> int:
        """Persiste gasto/reinserción y caja; devuelve ID_gasto."""
        raise NotImplementedError(
            "ventaDAO.registrarGasto: implementación pendiente del Agente 1."
        )

    @staticmethod
    def verVentas(idSesion: int):
        """Devuelve las ventas de la sesión con sus detalles."""
        raise NotImplementedError(
            "ventaDAO.verVentas: implementación pendiente del Agente 1."
        )

    @staticmethod
    def verGastos(idSesion: int):
        """Devuelve los gastos/reinserciones de la sesión."""
        raise NotImplementedError(
            "ventaDAO.verGastos: implementación pendiente del Agente 1."
        )