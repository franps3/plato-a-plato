# Módulo fakeMainDAO.py (solo para pruebas)
# Implementa en memoria el contrato de los DAOs del Agente 1 para poder
# desarrollar y testear el controlador (Agente 3) sin la base SQLite real.
#
# FakeBD concentra el estado compartido de las "tablas" para que los tres
# DAOs falsos operen sobre los mismos datos, replicando el orden exacto de
# las tuplas:
#   Sesion:  (ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass)
#   Producto:[ID_producto, ID_sesion, Nombre, Precio, Stock]

from pathlib import Path

from control.excepciones import PersistenceError


class FakeBD:
    """Estado en memoria que simula las tablas de la base de datos."""

    def __init__(self):
        self.sesion = None
        self._proximoIdSesion = 1
        self.productos = {}  # idProducto -> [id, idSesion, nombre, precio, stock]
        self._proximoIdProducto = 1
        self.ventas = {}     # idVenta -> [id, idSesion, fechaHora, montoNeto, detalles]
        self._proximoIdVenta = 1
        self.gastos = {}     # idGasto -> [id, idSesion, nombre, monto, descripcion, fechaHora]
        self._proximoIdGasto = 1


class FakeMainDAO:
    """Falso DAO de sesiones: simula la persistencia en memoria."""

    def __init__(self, bd=None):
        self._bd = bd if bd is not None else FakeBD()

    def crearSesion(self, passHash, fondoInicial, caja, fechaInicio) -> int:
        """Persiste (sobreescribe) la sesión simulada y devuelve su ID."""
        idSesion = self._bd._proximoIdSesion
        self._bd._proximoIdSesion += 1
        self._bd.sesion = (idSesion, fechaInicio, fondoInicial, caja, passHash)
        return idSesion

    def obtenerSesion(self):
        """Devuelve la tupla de la sesión simulada o None si no existe."""
        return self._bd.sesion

    def nuke(self):
        """Borra la sesión, productos, ventas y gastos (CU15 reiniciar)."""
        self._bd.sesion = None
        self._bd._proximoIdSesion = 1
        self._bd.productos = {}
        self._bd._proximoIdProducto = 1
        self._bd.ventas = {}
        self._bd._proximoIdVenta = 1
        self._bd.gastos = {}
        self._bd._proximoIdGasto = 1

    def exportar(self, tipo, rutaDestino) -> str:
        """Falso: simula la exportación generando un archivo vacío (CU13/CU16).

        Devuelve la ruta con la extensión correcta (.xlsx para historial,
        .zip para sesión), mismo contrato que el mainDAO real.
        """
        extension = ".xlsx" if tipo == "historial" else ".zip"
        ruta = Path(rutaDestino)
        if ruta.is_dir():
            ruta = ruta / f"respaldo_fake{extension}"
        elif ruta.suffix.lower() != extension:
            ruta = ruta.with_suffix(extension)
        ruta.touch()
        return str(ruta)

    def importar(self, rutaZip, passNueva=None) -> tuple:
        """Falso: aplica la nueva clave y devuelve la sesión simulada (CU17).

        Eleva PersistenceError si el archivo no existe (contrato con el
        mainDAO real). Al no manejar archivos reales, no sobrescribe
        estados: el Agente 3 debe usar el mainDAO real para probar la
        sobrescritura de la BD.
        """
        if not Path(rutaZip).exists():
            raise PersistenceError("El archivo de sesión no existe.")
        if passNueva:
            idSesion, fecha, fondo, caja, _ = self._bd.sesion
            self._bd.sesion = (idSesion, fecha, fondo, caja, passNueva)
        return self._bd.sesion


class FakeProdDAO:
    """Falso DAO de productos (contrato: sin stock en verProductos)."""

    def __init__(self, bd=None):
        self._bd = bd if bd is not None else FakeBD()

    def crearProducto(self, nombre, stock, precio, idSesion) -> int:
        """Persiste el producto y devuelve su ID_producto."""
        idProducto = self._bd._proximoIdProducto
        self._bd._proximoIdProducto += 1
        self._bd.productos[idProducto] = [
            idProducto, idSesion, nombre, precio, stock
        ]
        return idProducto

    def verProductos(self, idSesion):
        """Devuelve list[(ID_producto, Nombre, Precio)] sin stock."""
        return [
            (p[0], p[2], p[3])
            for p in self._bd.productos.values()
            if p[1] == idSesion
        ]

    def editarProducto(self, idProducto, nombre, precio):
        """Actualiza nombre/precio; devuelve (ID, Nombre, Precio) o None."""
        if idProducto not in self._bd.productos:
            return None
        p = self._bd.productos[idProducto]
        p[2] = nombre
        p[3] = precio
        return (p[0], p[2], p[3])

    def eliminarProducto(self, idProducto) -> int:
        """Elimina el producto y devuelve filas afectadas (0 o 1)."""
        if idProducto not in self._bd.productos:
            return 0
        del self._bd.productos[idProducto]
        return 1


class FakeStockDAO:
    """Falso DAO de stock (misma tabla Producto del estado compartido)."""

    def __init__(self, bd=None):
        self._bd = bd if bd is not None else FakeBD()

    def verStock(self, idProducto):
        """Devuelve el stock del producto o None si no existe."""
        p = self._bd.productos.get(idProducto)
        return None if p is None else p[4]

    def editarStock(self, idProducto, stock):
        """Actualiza el stock; devuelve el nuevo valor o None si no existe."""
        p = self._bd.productos.get(idProducto)
        if p is None:
            return None
        p[4] = stock
        return stock

    def descontar(self, idProducto, cantidad):
        """Resta cantidad al stock (sin validar); devuelve el resto o None."""
        p = self._bd.productos.get(idProducto)
        if p is None:
            return None
        p[4] -= cantidad
        return p[4]


class FakeVentaDAO:
    """Falso DAO de ventas, detalles, gastos y caja.

    Replica el contrato acordado: la caja de la sesión se persiste dentro
    de la misma operación que registra la venta o el gasto/reinserción.
    Usa el estado compartido de FakeBD (ventas y gastos) para que
    mainDAO.nuke() pueda limpiarlo todo.
    """

    def __init__(self, bd=None):
        self._bd = bd if bd is not None else FakeBD()

    def _actualizarCaja(self, cajaNueva):
        """Actualiza la columna Caja de la sesión simulada."""
        if self._bd.sesion is None:
            return
        idSesion, fechaInicio, fondoInicial, caja, passHash = self._bd.sesion
        self._bd.sesion = (idSesion, fechaInicio, fondoInicial, cajaNueva, passHash)

    def registrarVenta(self, idSesion, fechaHora, detalles, montoNeto,
                       cajaNueva) -> int:
        """Persiste venta + detalles + caja; devuelve ID_venta."""
        idVenta = self._bd._proximoIdVenta
        self._bd._proximoIdVenta += 1
        self._bd.ventas[idVenta] = [
            idVenta, idSesion, fechaHora, montoNeto, list(detalles)
        ]
        self._actualizarCaja(cajaNueva)
        return idVenta

    def registrarGasto(self, idSesion, nombre, monto, descripcion,
                       fechaHora, cajaNueva) -> int:
        """Persiste gasto/reinserción + caja; devuelve ID_gasto."""
        idGasto = self._bd._proximoIdGasto
        self._bd._proximoIdGasto += 1
        self._bd.gastos[idGasto] = [
            idGasto, idSesion, nombre, monto, descripcion, fechaHora
        ]
        self._actualizarCaja(cajaNueva)
        return idGasto

    def verVentas(self, idSesion):
        """Devuelve las ventas de la sesión:
        (ID_venta, Fecha_hora, list[(ID_producto, Cantidad, Precio_unitario)])
        """
        return [
            (v[0], v[2], v[4])
            for v in self._bd.ventas.values()
            if v[1] == idSesion
        ]

    def verGastos(self, idSesion):
        """Devuelve los gastos/reinserciones de la sesión:
        (ID_gasto, Nombre, Monto, Descripcion, Fecha_hora)
        """
        return [
            (g[0], g[2], g[3], g[4], g[5])
            for g in self._bd.gastos.values()
            if g[1] == idSesion
        ]

    def borrarHistorial(self, idSesion) -> int:
        """Borra ventas y gastos de la sesión; devuelve ventas borradas (CU14).

        Replica el contrato del Agente 1: NO altera el stock (tabla
        productos del FakeBD) ni la caja (sesión simulada).
        """
        ventasABorrar = [
            v for v in self._bd.ventas.values() if v[1] == idSesion
        ]
        for v in ventasABorrar:
            del self._bd.ventas[v[0]]
        self._bd.gastos = {
            idGasto: g
            for idGasto, g in self._bd.gastos.items()
            if g[1] != idSesion
        }
        return len(ventasABorrar)
