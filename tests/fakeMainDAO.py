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
        self.cajas = {}      # idCaja -> [id, idSesion, nombre, fondo_inicial, monto] (MJ1)
        self._proximoIdCaja = 1
        self.combos = set()  # IDs de producto que son combos (Es_combo=1) (MJ4)
        self.detalleCombo = {}  # idCombo -> [[idProducto, cantidad], ...] (MJ4)


class FakeMainDAO:
    """Falso DAO de sesiones: simula la persistencia en memoria."""

    def __init__(self, bd=None):
        self._bd = bd if bd is not None else FakeBD()

    def crearSesion(self, passHash, fechaInicio, cajas=None,
                    preguntaSeguridad="", respuestaHash="") -> int:
        """Persiste (sobreescribe) la sesión simulada y devuelve su ID.

        COR7: el fondo inicial ya no se recibe como parámetro; se calcula
        como la suma de los montos de las cajas (lista de (nombre, monto)).
        Si no se pasan cajas, se crea la "Caja principal" con monto 0.
        MJ3: preguntaSeguridad/respuestaHash se guardan en la sesión
        simulada (la respuesta viaja HASHEADA desde el Agente 3).
        """
        totalInicial = round(
            sum(monto for _, monto in (cajas or [])), 2
        )
        idSesion = self._bd._proximoIdSesion
        self._bd._proximoIdSesion += 1
        self._bd.sesion = (
            idSesion, fechaInicio, totalInicial, totalInicial, passHash,
            preguntaSeguridad, respuestaHash,
        )
        cajasCrear = cajas if cajas else [("Caja principal", 0.0)]
        for nombreCaja, montoCaja in cajasCrear:
            idCaja = self._bd._proximoIdCaja
            self._bd._proximoIdCaja += 1
            self._bd.cajas[idCaja] = [
                idCaja, idSesion, nombreCaja, float(montoCaja), float(montoCaja)
            ]
        return idSesion

    def obtenerSesion(self):
        """Devuelve la tupla de la sesión simulada o None si no existe."""
        return self._bd.sesion

    def verCajas(self, idSesion):
        """Devuelve las cajas de la sesión: list[(ID_caja, Nombre, Fondo_inicial, Monto)]. (MJ1)"""
        return [
            (c[0], c[2], c[3], c[4])
            for c in self._bd.cajas.values()
            if c[1] == idSesion
        ]

    def verTotalCajas(self, idSesion):
        """Devuelve la suma de los Monto de todas las cajas de la sesión. (MJ1/MJ7)"""
        return float(sum(c[4] for c in self._bd.cajas.values() if c[1] == idSesion))

    def obtenerCaja(self, idCaja):
        """Devuelve una caja por su ID o None si no existe. (MJ1)"""
        c = self._bd.cajas.get(idCaja)
        return tuple(c) if c is not None else None

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
        self._bd.cajas = {}
        self._bd._proximoIdCaja = 1
        self._bd.combos = set()
        self._bd.detalleCombo = {}

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
            idSesion, fecha, fondo, caja, _, pregunta, respuesta = self._bd.sesion
            self._bd.sesion = (
                idSesion, fecha, fondo, caja, passNueva, pregunta, respuesta
            )
        return self._bd.sesion

    def obtenerPreguntaSeguridad(self):
        """Devuelve (ID_sesion, Pregunta, Respuesta) o None (MJ3)."""
        if self._bd.sesion is None:
            return None
        return (self._bd.sesion[0], self._bd.sesion[5], self._bd.sesion[6])

    def actualizarPass(self, passNuevaHash) -> bool:
        """Reemplaza la Pass de la sesión; True si actualizó (MJ3)."""
        if self._bd.sesion is None:
            return False
        idSesion, fecha, fondo, caja, _, pregunta, respuesta = self._bd.sesion
        self._bd.sesion = (
            idSesion, fecha, fondo, caja, passNuevaHash, pregunta, respuesta
        )
        return True


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
    # MJ4: combos (falso)
    def crearCombo(self, idSesion, nombre, precio, componentes) -> int:
        """Persiste un combo (Producto Es_combo=1) + DetalleCombo. Devuelve ID_combo."""
        for idProducto, cantidad in componentes:
            if idProducto not in self._bd.productos:
                raise PersistenceError(
                    f"El componente {idProducto} no existe; se deshace el combo."
                )
        idCombo = self._bd._proximoIdProducto
        self._bd._proximoIdProducto += 1
        self._bd.productos[idCombo] = [
            idCombo, idSesion, nombre, float(precio), 0
        ]
        self._bd.combos.add(idCombo)
        self._bd.detalleCombo[idCombo] = [[idProd, cant] for idProd, cant in componentes]
        return idCombo

    def verCombos(self, idSesion):
        """Lista combos de la sesión: list[(ID_combo, Nombre, Precio)]."""
        return [
            (p[0], p[2], p[3])
            for p in self._bd.productos.values()
            if p[1] == idSesion and p[0] in self._bd.combos
        ]

    def verComponentesCombo(self, idCombo):
        """Devuelve componentes: list[(ID_producto, Cantidad)]."""
        return [tuple(c) for c in self._bd.detalleCombo.get(idCombo, [])]

    def editarCombo(self, idCombo, nombre, precio, componentes):
        """Actualiza nombre, precio y componentes. Devuelve (id, nombre, precio) o None."""
        if idCombo not in self._bd.combos:
            return None
        for idProducto, cantidad in componentes:
            if idProducto not in self._bd.productos:
                raise PersistenceError(
                    f"El componente {idProducto} no existe; se deshace la edición."
                )
        p = self._bd.productos[idCombo]
        p[2] = nombre
        p[3] = float(precio)
        self._bd.detalleCombo[idCombo] = [[idProd, cant] for idProd, cant in componentes]
        return (idCombo, nombre, float(precio))

    def eliminarCombo(self, idCombo) -> int:
        """Elimina un combo y sus componentes. Devuelve 1 si era combo, 0 si no."""
        if idCombo not in self._bd.combos:
            return 0
        del self._bd.productos[idCombo]
        self._bd.combos.discard(idCombo)
        self._bd.detalleCombo.pop(idCombo, None)
        return 1


class FakeStockDAO:
    """Falso DAO de stock (misma tabla Producto del estado compartido).

    Replica COR8: los combos no tienen stock propio; su disponibilidad se
    deriva del stock de sus componentes (MIN(Stock // Cantidad)) y el
    descuento de un combo se aplica sobre los productos asociados.
    """

    def __init__(self, bd=None):
        self._bd = bd if bd is not None else FakeBD()

    def _es_combo(self, idProducto):
        return idProducto in self._bd.combos

    def verStock(self, idProducto):
        """Devuelve el stock del producto o None si no existe.

        COR8: si es un combo, devuelve cuantos combos se pueden armar con
        el stock actual de sus componentes.
        """
        p = self._bd.productos.get(idProducto)
        if p is None:
            return None
        if idProducto not in self._bd.combos:
            return p[4]
        componentes = self._bd.detalleCombo.get(idProducto, [])
        if not componentes:
            return 0
        minimos = []
        for idComp, cantidad in componentes:
            comp = self._bd.productos.get(idComp)
            if comp is None:
                return 0
            minimos.append(comp[4] // cantidad)
        return min(minimos) if minimos else 0

    def editarStock(self, idProducto, stock):
        """Actualiza el stock; devuelve el nuevo valor o None si no existe.

        COR8: los combos no tienen stock propio, por lo que editarStock sobre
        un combo devuelve None sin tocar el estado.
        """
        if idProducto in self._bd.combos:
            return None
        p = self._bd.productos.get(idProducto)
        if p is None:
            return None
        p[4] = stock
        return stock

    def descontar(self, idProducto, cantidad):
        """Resta cantidad al stock (sin validar); devuelve el resto o None.

        COR8: si es un combo, descuenta de cada componente asociado
        (cantidad * requerido en DetalleCombo) y devuelve la disponibilidad
        restante del combo.
        """
        if idProducto not in self._bd.productos:
            return None
        if idProducto in self._bd.combos:
            for idComp, cantComp in self._bd.detalleCombo.get(idProducto, []):
                comp = self._bd.productos.get(idComp)
                if comp is not None:
                    comp[4] -= cantidad * cantComp
            return self.verStock(idProducto)
        p = self._bd.productos[idProducto]
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
        idSesion, fechaInicio, fondoInicial, caja, passHash, \
            pregunta, respuesta = self._bd.sesion
        self._bd.sesion = (
            idSesion, fechaInicio, fondoInicial, cajaNueva, passHash,
            pregunta, respuesta,
        )

    def _ajustarMontoCaja(self, idCaja, delta):
        """Suma delta al Monto de una caja específica (MJ1). Retorna False si no existe."""
        c = self._bd.cajas.get(idCaja)
        if c is None:
            return False
        c[4] = round(c[4] + delta, 2)
        return True

    def registrarVenta(self, idSesion, fechaHora, detalles, montoNeto,
                       cajaNueva, idCaja=None) -> int:
        """Persiste venta + detalles + caja; devuelve ID_venta.

        MJ1: si idCaja es válido, se suma montoNeto al Monto de esa caja.
        Si no existe, se eleva PersistenceError.
        """
        if idCaja is not None and not self._ajustarMontoCaja(idCaja, montoNeto):
            raise PersistenceError(f"La caja {idCaja} no existe.")
        idVenta = self._bd._proximoIdVenta
        self._bd._proximoIdVenta += 1
        self._bd.ventas[idVenta] = [
            idVenta, idSesion, fechaHora, montoNeto, list(detalles)
        ]
        self._actualizarCaja(cajaNueva)
        return idVenta

    def registrarGasto(self, idSesion, nombre, monto, descripcion,
                       fechaHora, cajaNueva, idCaja=None) -> int:
        """Persiste gasto/reinserción + caja; devuelve ID_gasto.

        MJ1: si idCaja es válido, se suma monto (firmado) al Monto de esa caja.
        Si no existe, se eleva PersistenceError.
        """
        if idCaja is not None and not self._ajustarMontoCaja(idCaja, monto):
            raise PersistenceError(f"La caja {idCaja} no existe.")
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

    def obtenerEstadisticas(self, idSesion) -> dict:
        """Falso: calcula las estadísticas MJ2 sobre el estado en memoria.

        Replica el contrato del ventaDAO real con los mismos nombres de
        claves y el mismo formato de los 'más vendido' (tuplas o None).
        """
        detalles = [
            tuple(detalle)
            for v in self._bd.ventas.values()
            if v[1] == idSesion
            for detalle in v[4]
        ]
        gastos = [
            g for g in self._bd.gastos.values() if g[1] == idSesion
        ]
        totalEntradas = round(
            sum(cantidad * precio for _, cantidad, precio in detalles)
            + sum(g[3] for g in gastos if g[3] > 0), 2
        )
        totalSalidas = round(
            abs(sum(g[3] for g in gastos if g[3] < 0)), 2
        )

        cantidadProductos = 0
        cantidadCombos = 0
        porProducto = {}
        porCombo = {}
        for idProducto, cantidad, _ in detalles:
            if idProducto in self._bd.combos:
                cantidadCombos += cantidad
                porCombo[idProducto] = porCombo.get(idProducto, 0) + cantidad
                for idComponente, cantComponente in (
                        self._bd.detalleCombo.get(idProducto, [])):
                    unidades = cantidad * cantComponente
                    cantidadProductos += unidades
                    porProducto[idComponente] = (
                        porProducto.get(idComponente, 0) + unidades
                    )
            else:
                cantidadProductos += cantidad
                porProducto[idProducto] = \
                    porProducto.get(idProducto, 0) + cantidad

        productoMasVendido = None
        if porProducto:
            idTop = max(porProducto, key=porProducto.get)
            productoMasVendido = (
                idTop, self._bd.productos[idTop][2], porProducto[idTop],
            )
        comboMasVendido = None
        if porCombo:
            idTop = max(porCombo, key=porCombo.get)
            comboMasVendido = (
                idTop, self._bd.productos[idTop][2], porCombo[idTop],
            )

        return {
            "totalEntradas": totalEntradas,
            "totalSalidas": totalSalidas,
            "cantidadProductosVendidos": cantidadProductos,
            "cantidadCombosVendidos": cantidadCombos,
            "cantidadGastos": len(gastos),
            "productoMasVendido": productoMasVendido,
            "comboMasVendido": comboMasVendido,
        }
