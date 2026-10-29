# Módulo test_daos_ventas.py
# Tests de integración de los DAOs reales del Agente 1 para los casos de uso
# CU10 (registrar venta), CU11 (registrar gasto/reinserción), CU12 (ver
# historial) y CU14 (borrar historial) a nivel de capa de datos.
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
from acceso.ventaDAO import ventaDAO
from control.excepciones import PersistenceError


@pytest.fixture
def bdTemporal(tmp_path, monkeypatch):
    """Redirige la base a un archivo temporal y reabre la conexión compartida."""
    rutaBd = tmp_path / "bd_daos_ventas_test.db"
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
    """Crea la sesión única (CU1) con caja 500 y devuelve su ID_sesion."""
    return mainDAO.crearSesion(
        "hash-de-prueba", "2026-09-13 10:00:00",
        cajas=[("Caja principal", 500.0)],
    )


@pytest.fixture
def catalogo(sesionId):
    """Crea dos productos (A: stock 5 precio 100; B: stock 3 precio 200)
    y devuelve sus ID_producto."""
    idA = prodDAO().crearProducto("A", 5, 100.0, sesionId)
    idB = prodDAO().crearProducto("B", 3, 200.0, sesionId)
    return {"A": idA, "B": idB}


def _detallesVentaA(catalogo):
    """Devuelve 2 líneas de detalle: 2xA a 100 y 1xB a 200 (total 400)."""
    return [
        (catalogo["A"], 2, 100.0),
        (catalogo["B"], 1, 200.0),
    ]


# ---------------------------------------------------------------------------
# CU10: registrarVenta(idSesion, fechaHora, detalles, montoNeto, cajaNueva)
# ---------------------------------------------------------------------------

def test_cu10_registraVentaConDetallesYActualizaCaja(bdTemporal, sesionId,
                                                     catalogo):
    """CU10: persiste Venta + DetalleVenta y actualiza Sesion.Caja en la
    misma transacción."""
    detalle = _detallesVentaA(catalogo)
    idVenta = ventaDAO().registrarVenta(
        sesionId, "2026-09-13 11:00:00.000001", detalle,
        montoNeto=400.0, cajaNueva=900.0,
    )

    assert isinstance(idVenta, int) and idVenta > 0
    # Caja persistida: 500 inicial + 400 de la venta = 900.
    assert mainDAO.obtenerSesion()[3] == 900.0
    # El historial devuelve la venta con sus dos líneas de detalle.
    assert ventaDAO().verVentas(sesionId) == [
        (idVenta, "2026-09-13 11:00:00.000001", detalle)
    ]


def test_cu10_registraVariasVentasYSegmentaDetalles(bdTemporal, sesionId,
                                                    catalogo):
    """CU10: cada venta conserva SOLO sus propios detalles (agrupación por
    ID_venta al leer el historial)."""
    idA = catalogo["A"]
    primera = ventaDAO().registrarVenta(
        sesionId, "2026-09-13 11:00:00.000001", [(idA, 1, 100.0)],
        100.0, 600.0,
    )
    segunda = ventaDAO().registrarVenta(
        sesionId, "2026-09-13 11:00:00.000002", [(idA, 2, 100.0)],
        200.0, 800.0,
    )

    ventas = ventaDAO().verVentas(sesionId)

    assert [(v[0], v[2]) for v in ventas] == [
        (primera, [(idA, 1, 100.0)]),
        (segunda, [(idA, 2, 100.0)]),
    ]


def test_cu10_violacionDeFkElevaPersistenceError(bdTemporal):
    """Regla clave: sqlite3.Error se encapsula en PersistenceError con
    ROLLBACK (ID de sesión inexistente -> violación de FK)."""
    with pytest.raises(PersistenceError):
        ventaDAO().registrarVenta(
            9999, "2026-09-13 11:00:00", [], 0.0, 0.0
        )


# ---------------------------------------------------------------------------
# CU11: registrarGasto(idSesion, nombre, monto, descripcion, fechaHora, cajaNueva)
# ---------------------------------------------------------------------------

def test_cu11_registraGastoConMontoFirmadoNegativo(bdTemporal, sesionId):
    """CU11: un gasto se persiste con monto NEGATIVO y descuenta la caja."""
    idGasto = ventaDAO().registrarGasto(
        sesionId, "Compra insumos", -100.0, "Platos y vasos",
        "2026-09-13 12:00:00.000001", 400.0,
    )

    assert isinstance(idGasto, int) and idGasto > 0
    assert ventaDAO().verGastos(sesionId) == [
        (idGasto, "Compra insumos", -100.0, "Platos y vasos",
         "2026-09-13 12:00:00.000001")
    ]
    # Caja persistida: 500 - 100 = 400.
    assert mainDAO.obtenerSesion()[3] == 400.0


def test_cu11_registraReinsercionConMontoPositivo(bdTemporal, sesionId):
    """CU11: una reinserción se persiste con monto POSITIVO y suma a caja."""
    idGasto = ventaDAO().registrarGasto(
        sesionId, "Vuelto sobrante", 250.0, "Reposición",
        "2026-09-13 12:00:00.000001", 750.0,
    )

    assert ventaDAO().verGastos(sesionId)[0] == (
        idGasto, "Vuelto sobrante", 250.0, "Reposición",
        "2026-09-13 12:00:00.000001",
    )
    assert mainDAO.obtenerSesion()[3] == 750.0


def test_cu11_violacionDeFkElevaPersistenceError(bdTemporal):
    """Regla clave: registrarGasto con sesión inexistente eleva
    PersistenceError (violación de FK)."""
    with pytest.raises(PersistenceError):
        ventaDAO().registrarGasto(
            9999, "Fantasma", -50.0, "x",
            "2026-09-13 12:00:00", 0.0,
        )


# ---------------------------------------------------------------------------
# CU12: verVentas / verGastos
# ---------------------------------------------------------------------------

def test_cu12_aislaMovimientosPorSesion(bdTemporal):
    """CU12: cada sesión ve únicamente sus propios movimientos."""
    idSesionA = mainDAO.crearSesion(
        "hash-a", "t1", cajas=[("Caja principal", 100.0)]
    )
    idSesionB = mainDAO.crearSesion(
        "hash-b", "t2", cajas=[("Caja principal", 200.0)]
    )
    idA = prodDAO().crearProducto("Pizza", 2, 3000.0, idSesionA)
    prodDAO().crearProducto("Empanada", 4, 800.0, idSesionB)

    ventaA = ventaDAO().registrarVenta(
        idSesionA, "2026-09-13 10:00:00.000001", [(idA, 1, 3000.0)],
        3000.0, 3100.0,
    )
    ventaDAO().registrarGasto(
        idSesionB, "Flete", -50.0, "Traslado",
        "2026-09-13 10:00:00.000001", 150.0,
    )

    assert ventaDAO().verVentas(idSesionA) == [
        (ventaA, "2026-09-13 10:00:00.000001", [(idA, 1, 3000.0)])
    ]
    assert ventaDAO().verVentas(idSesionB) == []
    assert ventaDAO().verGastos(idSesionA) == []
    assert len(ventaDAO().verGastos(idSesionB)) == 1


def test_cu12_listasVaciassSinMovimientos(bdTemporal, sesionId):
    """CU12: sin movimientos el historial devuelve listas vacías."""
    assert ventaDAO().verVentas(sesionId) == []
    assert ventaDAO().verGastos(sesionId) == []


# ---------------------------------------------------------------------------
# CU14: borrarHistorial(idSesion)
# ---------------------------------------------------------------------------

def test_cu14_borraHistorialSinTocarStockNiCaja(bdTemporal, sesionId,
                                                catalogo):
    """CU14: limpia ventas y gastos preservando Producto.Stock y Sesion.Caja."""
    idA = catalogo["A"]
    ventaDAO().registrarVenta(
        sesionId, "2026-09-13 11:00:00.000001", [(idA, 2, 100.0)],
        200.0, 700.0,
    )
    ventaDAO().registrarGasto(
        sesionId, "Insumos", -100.0, "Carteles",
        "2026-09-13 12:00:00.000001", 600.0,
    )

    borradas = ventaDAO().borrarHistorial(sesionId)

    assert borradas == 1
    assert ventaDAO().verVentas(sesionId) == []
    assert ventaDAO().verGastos(sesionId) == []
    # Postcondición CU14: no se altera stock ni caja.
    assert stockDAO().verStock(idA) == 5
    assert mainDAO.obtenerSesion()[3] == 600.0


def test_cu14_devuelveCantidadDeVentasBorradas(bdTemporal, sesionId,
                                               catalogo):
    """CU14: el retorno es la cantidad de ventas borradas (no de gastos)."""
    idA = catalogo["A"]
    ventaDAO().registrarVenta(sesionId, "t1", [(idA, 1, 100.0)], 100.0, 600.0)
    ventaDAO().registrarVenta(sesionId, "t2", [(idA, 1, 100.0)], 100.0, 700.0)
    ventaDAO().registrarGasto(sesionId, "Flete", -50.0, "x", "t3", 650.0)

    assert ventaDAO().borrarHistorial(sesionId) == 2


def test_cu14_soloLimpiaLaSesionIndicada(bdTemporal):
    """CU14: borrar el historial de una sesión no afecta a las demás."""
    idSesionA = mainDAO.crearSesion(
        "hash-a", "t1", cajas=[("Caja principal", 100.0)]
    )
    idSesionB = mainDAO.crearSesion(
        "hash-b", "t2", cajas=[("Caja principal", 200.0)]
    )
    idA = prodDAO().crearProducto("A", 3, 100.0, idSesionA)
    idB = prodDAO().crearProducto("B", 3, 100.0, idSesionB)

    ventaDAO().registrarVenta(idSesionA, "t1", [(idA, 1, 100.0)], 100.0, 200.0)
    ventaB = ventaDAO().registrarVenta(
        idSesionB, "t1", [(idB, 1, 100.0)], 100.0, 300.0
    )

    assert ventaDAO().borrarHistorial(idSesionA) == 1
    assert ventaDAO().verVentas(idSesionA) == []
    # La sesión B conserva su venta intacta.
    assert ventaDAO().verVentas(idSesionB) == [
        (ventaB, "t1", [(idB, 1, 100.0)])
    ]


# ---------------------------------------------------------------------------
# MJ2: estadísticas básicas (obtenerEstadisticas)
# ---------------------------------------------------------------------------

def test_mj2_estadisticasSinMovimientos(bdTemporal, sesionId):
    """MJ2: sin movimientos todos los indicadores son cero/None."""
    stats = ventaDAO().obtenerEstadisticas(sesionId)

    assert stats["totalEntradas"] == 0.0
    assert stats["totalSalidas"] == 0.0
    assert stats["cantidadProductosVendidos"] == 0
    assert stats["cantidadCombosVendidos"] == 0
    assert stats["cantidadGastos"] == 0
    assert stats["productoMasVendido"] is None
    assert stats["comboMasVendido"] is None


def test_mj2_estadisticasConVentasGastosYReingresos(bdTemporal, sesionId,
                                                   catalogo):
    """MJ2: entradas/salidas/cantidades con ventas, gastos y reingresos."""
    idA, idB = catalogo["A"], catalogo["B"]
    ventaDAO().registrarVenta(
        sesionId, "t1", [(idA, 2, 100.0), (idB, 1, 200.0)],
        400.0, 900.0,
    )
    # Montos firmados: negativo = gasto, positivo = reinserción.
    ventaDAO().registrarGasto(
        sesionId, "Gasto", -100.0, "x", "t2", 800.0,
    )
    ventaDAO().registrarGasto(
        sesionId, "Reingreso", 50.0, "y", "t3", 850.0,
    )

    stats = ventaDAO().obtenerEstadisticas(sesionId)

    # Entradas = 400 (venta) + 50 (reingreso) = 450.
    assert stats["totalEntradas"] == 450.0
    # Salidas = |-100| = 100.
    assert stats["totalSalidas"] == 100.0
    assert stats["cantidadProductosVendidos"] == 3
    assert stats["cantidadCombosVendidos"] == 0
    assert stats["cantidadGastos"] == 2
    # Producto más vendido: A (2) por sobre B (1).
    assert stats["productoMasVendido"][0] == idA
    assert stats["productoMasVendido"][2] == 2
    assert stats["comboMasVendido"] is None


def test_mj2_estadisticasConCombosAcumulanComponentes(bdTemporal, sesionId,
                                                      catalogo):
    """MJ2: al vender combos, los componentes suman a 'productos vendidos'."""
    idA, idB = catalogo["A"], catalogo["B"]
    # Combo = 2 unidades de A + 1 unidad de B.
    idCombo = prodDAO().crearCombo(
        sesionId, "Combo AB", 250.0,
        [(idA, 2), (idB, 1)],
    )
    # Se venden 2 combos y una unidad directa de A.
    ventaDAO().registrarVenta(
        sesionId, "t1", [(idCombo, 2, 250.0)], 500.0, 1000.0,
    )
    ventaDAO().registrarVenta(
        sesionId, "t2", [(idA, 1, 100.0)], 100.0, 1100.0,
    )

    stats = ventaDAO().obtenerEstadisticas(sesionId)

    assert stats["totalEntradas"] == 600.0
    assert stats["totalSalidas"] == 0.0
    # Directas de A: 1. Vía combos: A 2*2=4 + B 2*1=2 => 6. Total 7.
    assert stats["cantidadProductosVendidos"] == 7
    assert stats["cantidadCombosVendidos"] == 2
    # A es el más vendido: 1 directa + 4 en combos = 5.
    assert stats["productoMasVendido"][0] == idA
    assert stats["productoMasVendido"][2] == 5
    # Único combo vendido con 2 unidades.
    assert stats["comboMasVendido"][0] == idCombo
    assert stats["comboMasVendido"][2] == 2