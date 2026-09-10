# Módulo fakeMainDAO.py (solo para pruebas)
# Implementa en memoria el contrato de los DAOs del Agente 1 para poder
# desarrollar y testear el controlador (Agente 3) sin la base SQLite real.
#
# FakeBD concentra el estado compartido de las "tablas" para que los tres
# DAOs falsos operen sobre los mismos datos, replicando el orden exacto de
# las tuplas:
#   Sesion:  (ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass)
#   Producto:[ID_producto, ID_sesion, Nombre, Precio, Stock]


class FakeBD:
    """Estado en memoria que simula las tablas de la base de datos."""

    def __init__(self):
        self.sesion = None
        self._proximoIdSesion = 1
        self.productos = {}  # idProducto -> [id, idSesion, nombre, precio, stock]
        self._proximoIdProducto = 1


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