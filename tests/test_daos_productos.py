# Módulo test_daos_productos.py
# Tests de integración de los DAOs reales del Agente 1 para los casos de uso
# CU4 (crear producto), CU5 (ver productos), CU7 (editar producto/stock) y
# CU8 (eliminar producto). CU6 es una tarea exclusivamente visual (Agente 2).
#
# Se ejecutan contra una base SQLite temporal (no tocan bd.db real): un
# fixture redirige mainDAO.RUTA_BD con monkeypatch y resetea el singleton de
# conexión (conn/cursor) para que mainDAO.conectar() la reabra sobre el
# archivo temporal.

import sys
from pathlib import Path

import pytest

# Permite importar los paquetes del proyecto desde la raíz del repo.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from acceso import mainDAO as mainDAO_mod
from acceso.mainDAO import mainDAO
from acceso.prodDAO import prodDAO
from acceso.stockDAO import stockDAO
from control.excepciones import PersistenceError


@pytest.fixture
def bdTemporal(tmp_path, monkeypatch):
    """Redirige la base a un archivo temporal y reabre la conexión compartida."""
    rutaBd = tmp_path / "bd_daos_test.db"
    monkeypatch.setattr(mainDAO_mod, "RUTA_BD", rutaBd)
    mainDAO.conn = None
    mainDAO.cursor = None
    mainDAO.conectar()
    yield rutaBd
    # Restaura el singleton para no contaminar otros tests de la suite.
    mainDAO.conn = None
    mainDAO.cursor = None


@pytest.fixture
def sesionId(bdTemporal):
    """Crea la sesión única en la BD temporal (CU1) y devuelve su ID_sesion."""
    return mainDAO.crearSesion(
        "hash-de-prueba", 500.0, 500.0, "2026-09-13 10:00:00"
    )


# ---------------------------------------------------------------------------
# CU4: crearProducto(nombre, stock, precio, idSesion)
# ---------------------------------------------------------------------------

def test_cu4_crearProductoPersisteDatos(bdTemporal, sesionId):
    """CU4: agrega el ítem al catálogo con nombre, precio y stock inicial."""
    idProducto = prodDAO().crearProducto("Milanesa", 10, 2500.0, sesionId)

    assert isinstance(idProducto, int) and idProducto > 0
    assert stockDAO().verStock(idProducto) == 10
    assert prodDAO().verProductos(sesionId) == [(idProducto, "Milanesa", 2500.0)]


def test_cu4_aceptaStockCero(bdTemporal, sesionId):
    """CU4: un stock inicial de 0 queda persistido y consultable."""
    idProducto = prodDAO().crearProducto("Pan", 0, 500.0, sesionId)

    assert stockDAO().verStock(idProducto) == 0


def test_cu4_violacionDeFkElevaPersistenceError(bdTemporal):
    """Regla clave: sqlite3.Error se encapsula en PersistenceError (con ROLLBACK)."""
    with pytest.raises(PersistenceError):
        # ID de sesión inexistente -> violación de FK por PRAGMA foreign_keys.
        prodDAO().crearProducto("Fantasma", 1, 100.0, 9999)


# ---------------------------------------------------------------------------
# CU5: verProductos(idSesion)
# ---------------------------------------------------------------------------

def test_cu5_listaOrdenadaPorNombre(bdTemporal, sesionId):
    """CU5: despliega el listado completo ordenado alfabéticamente por nombre."""
    idMila = prodDAO().crearProducto("Milanesa", 3, 2500.0, sesionId)
    idPan = prodDAO().crearProducto("Pan", 7, 500.0, sesionId)
    idEmpa = prodDAO().crearProducto("Empanada", 5, 800.0, sesionId)

    resultado = prodDAO().verProductos(sesionId)

    assert resultado == [
        (idEmpa, "Empanada", 800.0),
        (idMila, "Milanesa", 2500.0),
        (idPan, "Pan", 500.0),
    ]


def test_cu5_ordenNoDistingueMayusculas(bdTemporal, sesionId):
    """CU5: el orden alfabético no distingue mayúsculas (COLLATE NOCASE)."""
    idPan = prodDAO().crearProducto("pan", 1, 300.0, sesionId)
    idPizza = prodDAO().crearProducto("Pizza", 1, 3000.0, sesionId)

    assert prodDAO().verProductos(sesionId) == [
        (idPan, "pan", 300.0),
        (idPizza, "Pizza", 3000.0),
    ]


def test_cu5_aislaProductosPorSesion(bdTemporal):
    """CU5: cada sesión ve únicamente sus propios productos."""
    idSesionA = mainDAO.crearSesion("hash-a", 100.0, 100.0, "t1")
    idSesionB = mainDAO.crearSesion("hash-b", 200.0, 200.0, "t2")
    idA = prodDAO().crearProducto("Pizza", 2, 3000.0, idSesionA)
    prodDAO().crearProducto("Empanada", 4, 800.0, idSesionB)

    assert prodDAO().verProductos(idSesionA) == [(idA, "Pizza", 3000.0)]


def test_cu5_listaVaciaSinProductos(bdTemporal, sesionId):
    """CU5: sin productos el listado es una lista vacía."""
    assert prodDAO().verProductos(sesionId) == []


# ---------------------------------------------------------------------------
# CU7: editarProducto(idProducto, nombre, precio) / editarStock(idProducto, stock)
# ---------------------------------------------------------------------------

def test_cu7_editaProducto(bdTemporal, sesionId):
    """CU7: modifica nombre y precio y devuelve la fila actualizada."""
    idProducto = prodDAO().crearProducto("A", 3, 100.0, sesionId)

    fila = prodDAO().editarProducto(idProducto, "A2", 150.0)

    assert fila == (idProducto, "A2", 150.0)
    assert prodDAO().verProductos(sesionId) == [(idProducto, "A2", 150.0)]


def test_cu7_editaProductoInexistente(bdTemporal):
    """CU7: editar un producto inexistente devuelve None."""
    assert prodDAO().editarProducto(999, "X", 100.0) is None


def test_cu7_editaStock(bdTemporal, sesionId):
    """CU7: modifica el stock y devuelve el nuevo valor."""
    idProducto = prodDAO().crearProducto("A", 3, 100.0, sesionId)

    assert stockDAO().editarStock(idProducto, 15) == 15
    assert stockDAO().verStock(idProducto) == 15


def test_cu7_editaStockInexistente(bdTemporal):
    """CU7: editar el stock de un producto inexistente devuelve None."""
    assert stockDAO().editarStock(999, 5) is None


# ---------------------------------------------------------------------------
# CU8: eliminarProducto(idProducto)
# ---------------------------------------------------------------------------

def test_cu8_eliminaProducto(bdTemporal, sesionId):
    """CU8: da de baja el producto de la lista activa (1 fila afectada)."""
    idProducto = prodDAO().crearProducto("A", 3, 100.0, sesionId)

    assert prodDAO().eliminarProducto(idProducto) == 1
    assert prodDAO().verProductos(sesionId) == []
    assert stockDAO().verStock(idProducto) is None


def test_cu8_eliminaInexistente(bdTemporal):
    """CU8: eliminar un producto inexistente devuelve 0 filas afectadas."""
    assert prodDAO().eliminarProducto(999) == 0


# ---------------------------------------------------------------------------
# CU10 (mismo esquema): descontar(idProducto, cantidad)
# ---------------------------------------------------------------------------

def test_cu10_descuentaStock(bdTemporal, sesionId):
    """CU10: descontar resta la cantidad y devuelve el stock restante."""
    idProducto = prodDAO().crearProducto("A", 10, 100.0, sesionId)

    assert stockDAO().descontar(idProducto, 4) == 6
    assert stockDAO().verStock(idProducto) == 6


def test_cu10_descuentaInexistente(bdTemporal):
    """CU10: descontar un producto inexistente devuelve None."""
    assert stockDAO().descontar(999, 4) is None