# Módulo test_daos_combos.py
# Tests de integración de los DAOs reales del Agente 1 para la mejora MJ4
# (soporte para combos): un combo se persiste como Producto con Es_combo=1
# y sus componentes en DetalleCombo; se puede agregar a una venta como un
# producto más (DetalleVenta no cambia).
#
# Se ejecutan contra una base SQLite temporal (no tocan bd.db real): el
# fixture redirige mainDAO.RUTA_BD con monkeypatch y resetea el singleton
# de conexión (conn/cursor), igual que el resto de los test_daos_*.

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
from acceso.ventaDAO import ventaDAO
from control.excepciones import PersistenceError


@pytest.fixture
def bdTemporal(tmp_path, monkeypatch):
    """Redirige la base a un archivo temporal y reabre la conexión compartida."""
    rutaBd = tmp_path / "bd_daos_combos_test.db"
    monkeypatch.setattr(mainDAO_mod, "RUTA_BD", rutaBd)
    mainDAO.conn = None
    mainDAO.cursor = None
    mainDAO.conectar()
    yield rutaBd
    # Restaura el singleton para no contaminar otros tests de la suite.
    mainDAO.conn = None
    mainDAO.cursor = None


@pytest.fixture
def catalogo(bdTemporal):
    """Sesión con dos productos base (Hamburguesa 5x100 y Papas 10x50)."""
    idSesion = mainDAO.crearSesion(
        "hash-de-prueba", 500.0, 500.0, "2026-09-13 10:00:00"
    )
    idBurger = prodDAO().crearProducto("Hamburguesa", 5, 100.0, idSesion)
    idPapas = prodDAO().crearProducto("Papas", 10, 50.0, idSesion)
    return {"idSesion": idSesion, "burger": idBurger, "papas": idPapas}


def test_mj4_crearComboPersisteProductoYComponentes(catalogo):
    """MJ4: crearCombo persiste el combo (Es_combo=1) + DetalleCombo."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo Doble", 220.0,
        [(catalogo["burger"], 2), (catalogo["papas"], 1)],
    )
    assert isinstance(idCombo, int) and idCombo > 0
    assert prodDAO().verCombos(catalogo["idSesion"]) == [
        (idCombo, "Combo Doble", 220.0)
    ]
    assert prodDAO().verComponentesCombo(idCombo) == [
        (catalogo["burger"], 2), (catalogo["papas"], 1)
    ]


def test_mj4_comboApareceComoProductoEnVenta(catalogo):
    """MJ4: el combo se agrega a una venta como un producto más."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo Simple", 140.0,
        [(catalogo["burger"], 1), (catalogo["papas"], 1)],
    )
    # Aparece en el listado de productos (pantalla de Venta).
    idsProductos = {
        fila[0]
        for fila in prodDAO().verProductos(catalogo["idSesion"])
    }
    assert idCombo in idsProductos
    # Se registra en DetalleVenta como cualquier producto.
    idVenta = ventaDAO().registrarVenta(
        catalogo["idSesion"], "2026-09-13 11:00:00.000001",
        [(idCombo, 1, 140.0)], montoNeto=140.0, cajaNueva=640.0,
    )
    assert ventaDAO().verVentas(catalogo["idSesion"]) == [
        (idVenta, "2026-09-13 11:00:00.000001", [(idCombo, 1, 140.0)])
    ]


def test_mj4_editarComboReemplazaComponentes(catalogo):
    """MJ4: editarCombo actualiza nombre, precio y reemplaza componentes."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo", 200.0,
        [(catalogo["burger"], 1)],
    )
    resultado = prodDAO().editarCombo(
        idCombo, "Combo Grande", 260.0,
        [(catalogo["burger"], 2), (catalogo["papas"], 2)],
    )
    assert resultado == (idCombo, "Combo Grande", 260.0)
    assert prodDAO().verCombos(catalogo["idSesion"]) == [
        (idCombo, "Combo Grande", 260.0)
    ]
    assert prodDAO().verComponentesCombo(idCombo) == [
        (catalogo["burger"], 2), (catalogo["papas"], 2)
    ]


def test_mj4_editarComboInexistenteDevuelveNone(catalogo):
    """MJ4: un ID inexistente o de producto común no se edita como combo."""
    assert prodDAO().editarCombo(9999, "X", 1.0, []) is None
    assert prodDAO().editarCombo(catalogo["burger"], "X", 1.0, []) is None


def test_mj4_eliminarComboLimpiaDetalleCombo(catalogo):
    """MJ4: eliminarCombo borra el combo y sus componentes (FK CASCADE)."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo", 200.0,
        [(catalogo["burger"], 1), (catalogo["papas"], 1)],
    )
    assert prodDAO().eliminarCombo(idCombo) == 1
    assert prodDAO().verCombos(catalogo["idSesion"]) == []
    assert prodDAO().verComponentesCombo(idCombo) == []
    # El catálogo vuelve a tener solo los productos comunes.
    assert prodDAO().verProductos(catalogo["idSesion"]) == [
        (catalogo["burger"], "Hamburguesa", 100.0),
        (catalogo["papas"], "Papas", 50.0),
    ]


def test_mj4_eliminarProductoComunNoTocaCombos(catalogo):
    """MJ4: eliminarCombo sobre un producto común devuelve 0 filas."""
    assert prodDAO().eliminarCombo(catalogo["burger"]) == 0


def test_mj4_comboConComponenteInexistenteElevaPersistenceError(catalogo):
    """Regla clave: un componente inexistente rompe la transacción y hace
    ROLLBACK (la cabecera del combo no queda persistida)."""
    with pytest.raises(PersistenceError):
        prodDAO().crearCombo(
            catalogo["idSesion"], "Combo", 100.0,
            [(9999, 1)],
        )
    assert prodDAO().verCombos(catalogo["idSesion"]) == []

