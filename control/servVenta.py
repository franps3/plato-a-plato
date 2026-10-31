# Módulo servVenta.py (Agente 3)
# Servicio de ventas, caja y gastos: valida las reglas de dominio antes de
# registrar (stock suficiente al vender, saldo suficiente al gastar),
# orquesta las operaciones con ventaDAO y devuelve objetos de dominio.
#
# Decisión acordada: ventaDAO persiste la Caja de la sesión dentro de la
# MISMA transacción que registra la venta o el gasto/reinserción.

from datetime import datetime, timedelta

from .excepciones import ProductoNoEncontrado, StockInsuficiente
from .modelos import DetalleVenta, GastoSecundario, Venta


class ServVenta:
    """Capa de servicios de ventas y caja del sistema (Agente 3)."""

    def __init__(self, ventaDAO, stockDAO, prodDAO=None):
        self.ventaDAO = ventaDAO
        self.stockDAO = stockDAO
        self.prodDAO = prodDAO
        # Marca de tiempo del último movimiento: garantiza el orden
        # cronológico del historial (CU12).
        self._ultimaFechaHora = None

    def _nuevaFechaHora(self) -> str:
        """Genera un timestamp estrictamente creciente (CU12).

        Si dos operaciones ocurren dentro del mismo microsegundo, se
        avanza un microsegundo sobre la marca anterior para preservar
        el orden cronológico del historial.
        """
        fechaHora = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if (self._ultimaFechaHora is not None
                and fechaHora <= self._ultimaFechaHora):
            base = datetime.strptime(
                self._ultimaFechaHora, "%Y-%m-%d %H:%M:%S.%f"
            )
            fechaHora = (base + timedelta(microseconds=1)).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )
        self._ultimaFechaHora = fechaHora
        return fechaHora

    # ------------------------------------------------------------------
    # CU10: registrarVenta
    # ------------------------------------------------------------------
    def registrarVenta(self, idSesion, detalles, cajaNueva, idCaja=None) -> Venta:
        """Registra una venta multiproducto (CU10).

        La validación de stock suficiente ocurre ANTES de persistir:
        si alguna línea supera el stock disponible se eleva
        StockInsuficiente y no se escribe nada. ventaDAO persiste la
        venta, sus detalles y el nuevo saldo de caja en una transacción.

        Parámetros:
            idSesion: Sesión activa.
            detalles: Lista de DetalleVenta ya armados por el controlador
                (con precio unitario actual).
            cajaNueva: Nuevo saldo de caja tras sumar el total de la venta.
            idCaja: (MJ1) ID opcional de la caja a la que se asigna la venta;
                si se pasa, el monto se suma a esa caja y se registra la
                asignación en la venta.
        """
        # Marca de tiempo estrictamente creciente (CU12).
        fechaHora = self._nuevaFechaHora()
        # COR8: IDs de combo para validar stock de componentes.
        idsCombos = set()
        if self.prodDAO is not None:
            idsCombos = {c[0] for c in self.prodDAO.verCombos(idSesion)}

        # COR8: se agrega la demanda de todos los ítems (combos expandidos a
        # sus componentes) para validar el stock combinado antes de persistir.
        # Así no se permite vender más unidades de las disponibles aunque haya
        # varios combos o productos que compartan componentes.
        demanda = {}
        for detalle in detalles:
            if detalle.idProducto in idsCombos and self.prodDAO is not None:
                componentes = self.prodDAO.verComponentesCombo(
                    detalle.idProducto
                )
                for idComp, cantComp in componentes:
                    demanda[idComp] = (
                        demanda.get(idComp, 0)
                        + detalle.cantidad * cantComp
                    )
            else:
                demanda[detalle.idProducto] = (
                    demanda.get(detalle.idProducto, 0) + detalle.cantidad
                )

        for idProducto, cantidad in demanda.items():
            stock = self.stockDAO.verStock(idProducto)
            if stock is None:
                raise ProductoNoEncontrado(
                    "No se encontró el producto solicitado."
                )
            if stock < cantidad:
                raise StockInsuficiente(
                    f"Stock insuficiente para el producto {idProducto}."
                )

        montoNeto = round(
            sum(detalle.monto for detalle in detalles), 2
        )
        filas = [
            (d.idProducto, d.cantidad, d.precioUnitario)
            for d in detalles
        ]
        idVenta = self.ventaDAO.registrarVenta(
            idSesion, fechaHora, filas, montoNeto, cajaNueva, idCaja
        )
        return Venta(
            idVenta=idVenta,
            fechaHora=fechaHora,
            detalles=detalles,
            montoNeto=montoNeto,
        )

    # ------------------------------------------------------------------
    # CU11: registrarGasto / registrarReinsercion
    # ------------------------------------------------------------------
    def registrarGasto(self, idSesion, nombre, monto, descripcion,
                       cajaNueva, idCaja=None) -> GastoSecundario:
        """Registra un egreso de caja (CU11, tipo 'gasto').

        El monto FIRMADO se guarda en negativo (gasto): el tipo sale del
        signo al leer el historial. ventaDAO persiste el gasto y el nuevo
        saldo de caja en la misma transacción.

        Parámetro idCaja (MJ1): si se pasa, el gasto se asigna a esa caja
        (se descuenta su monto) y se registra la asignación.
        """
        return self._registrarMovimientoCaja(
            idSesion, nombre, -abs(monto), descripcion, cajaNueva, idCaja
        )

    def registrarReinsercion(self, idSesion, nombre, monto, descripcion,
                             cajaNueva, idCaja=None) -> GastoSecundario:
        """Registra una reinserción de dinero a caja (CU11, 'reinsertar').

        El monto FIRMADO se guarda en positivo (reinserción): el tipo sale
        del signo al leer el historial.

        Parámetro idCaja (MJ1): si se pasa, la reinserción se asigna a esa
        caja (se suma su monto) y se registra la asignación.
        """
        return self._registrarMovimientoCaja(
            idSesion, nombre, abs(monto), descripcion, cajaNueva, idCaja
        )

    def _registrarMovimientoCaja(self, idSesion, nombre, montoFirmado,
                                 descripcion, cajaNueva, idCaja=None
                                 ) -> GastoSecundario:
        """Registra un gasto o reinserción en la caja (CU11)."""
        # Marca de tiempo estrictamente creciente (CU12).
        fechaHora = self._nuevaFechaHora()
        idGasto = self.ventaDAO.registrarGasto(
            idSesion, nombre, montoFirmado, descripcion, fechaHora,
            cajaNueva, idCaja
        )
        return GastoSecundario(
            idGasto=idGasto,
            nombre=nombre,
            monto=montoFirmado,
            descripcion=descripcion,
            fechaHora=fechaHora,
        )

    # ------------------------------------------------------------------
    # CU12: consultas de historial
    # ------------------------------------------------------------------
    def verVentas(self, idSesion) -> list:
        """Devuelve las ventas de la sesión como objetos Venta."""
        ventas = []
        for fila in self.ventaDAO.verVentas(idSesion):
            idVenta, fechaHora, filasDetalle = fila
            detalles = [
                DetalleVenta(
                    idProducto=d[0],
                    cantidad=d[1],
                    precioUnitario=d[2],
                    monto=round(d[1] * d[2], 2),
                )
                for d in filasDetalle
            ]
            ventas.append(
                Venta(
                    idVenta=idVenta,
                    fechaHora=fechaHora,
                    detalles=detalles,
                    montoNeto=round(
                        sum(detalle.monto for detalle in detalles), 2
                    ),
                )
            )
        return ventas

    def verGastos(self, idSesion) -> list:
        """Devuelve los gastos/reinserciones de la sesión como objetos."""
        return [
            GastoSecundario(
                idGasto=f[0],
                nombre=f[1],
                monto=f[2],
                descripcion=f[3],
                fechaHora=f[4],
            )
            for f in self.ventaDAO.verGastos(idSesion)
        ]

    def borrarHistorial(self, idSesion) -> None:
        """Borra ventas, detalles y gastos de la sesión (CU14).

        Conserva productos y sesión; el stock queda intacto.
        """
        self.ventaDAO.borrarHistorial(idSesion)

    # ------------------------------------------------------------------
    # MJ2: estadísticas básicas
    # ------------------------------------------------------------------
    def obtenerEstadisticas(self, idSesion: int) -> dict:
        """Devuelve las estadísticas básicas de la sesión (MJ2).

        Delega la agregación SQL en ventaDAO.obtenerEstadisticas.
        Retorna dict con totalEntradas, totalSalidas, cantidades vendidas,
        gastos y producto/combo más vendido.
        """
        return self.ventaDAO.obtenerEstadisticas(idSesion)