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
from acceso.stockDAO import stockDAO
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
        "hash-de-prueba", "2026-09-13 10:00:00",
        cajas=[("Caja principal", 500.0)],
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


# ---------------------------------------------------------------------------
# COR8: los combos no tienen stock propio; su disponibilidad se deriva de
# los productos asociados y al vender uno se descuenta el stock de esos
# productos.
# ---------------------------------------------------------------------------

def test_cor8_crearComboSinStockGuardaZero(catalogo):
    """COR8: crearCombo ya no recibe stock; la fila del combo queda en 0."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo", 220.0,
        [(catalogo["burger"], 2), (catalogo["papas"], 1)],
    )
    # El stock almacenado de la fila combo en Producto es 0 (sin stock propio).
    mainDAO.conectar()
    stockInterno = mainDAO.cursor.execute(
        "SELECT Stock FROM Producto WHERE ID_producto = ?",
        (idCombo,),
    ).fetchone()[0]
    assert stockInterno == 0
    # verStock deriva la disponibilidad de los componentes: min(5//2, 10//1).
    assert stockDAO().verStock(idCombo) == 2


def test_cor8_verStockComboDerivaDeComponentes(catalogo):
    """COR8: verStock de un combo = MIN(Stock // Cantidad) de componentes."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo", 220.0,
        [(catalogo["burger"], 2), (catalogo["papas"], 1)],
    )
    # Hamburguesa 5 -> 5 // 2 = 2 combos; Papas 10 -> 10 // 1 = 10.
    assert stockDAO().verStock(idCombo) == 2
    # Se reduce el stock de un componente y baja la disponibilidad del combo.
    stockDAO().editarStock(catalogo["burger"], 4)
    assert stockDAO().verStock(idCombo) == 2  # 4//2 = 2
    stockDAO().editarStock(catalogo["burger"], 3)
    assert stockDAO().verStock(idCombo) == 1  # 3//2 = 1


def test_cor8_editarStockComboDevuelveNone(catalogo):
    """COR8: no se puede editar el stock de un combo (no tiene stock)."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo", 140.0,
        [(catalogo["burger"], 1)],
    )
    assert stockDAO().editarStock(idCombo, 99) is None
    # El stock de los componentes no se altera.
    assert stockDAO().verStock(catalogo["burger"]) == 5


def test_cor8_descontarComboDescuentaComponentes(catalogo):
    """COR8: al descontar un combo se descuenta el stock de los asociados."""
    idCombo = prodDAO().crearCombo(
        catalogo["idSesion"], "Combo Doble", 220.0,
        [(catalogo["burger"], 2), (catalogo["papas"], 1)],
    )
    # Vender 1 combo: burger 5-2=3, papas 10-1=9; disponible restante 1.
    assert stockDAO().descontar(idCombo, 1) == 1
    assert stockDAO().verStock(catalogo["burger"]) == 3
    assert stockDAO().verStock(catalogo["papas"]) == 9
    # Vender 1 combo más: burger 3-2=1, papas 9-1=8; disponible 0.
    assert stockDAO().descontar(idCombo, 1) == 0
    assert stockDAO().verStock(catalogo["burger"]) == 1
    assert stockDAO().verStock(catalogo["papas"]) == 8


def test_cor8_descontarComboInexistenteDevuelveNone(catalogo):
    """COR8: descontar un combo inexistente devuelve None (contrato)."""
    assert stockDAO().descontar(9999, 1) is None

