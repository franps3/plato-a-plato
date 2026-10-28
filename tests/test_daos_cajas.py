# Módulo test_daos_cajas.py
# Tests de integración de los DAOs reales del Agente 1 para las mejoras
# MJ1 (múltiples cajas / medios de pago) y MJ7 (valor de caja en UI):
# creación de N cajas al crear la sesión, consultas por caja y total, y
# asignación de una caja a cada venta/gasto para modificar su monto.
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
    rutaBd = tmp_path / "bd_daos_cajas_test.db"
    monkeypatch.setattr(mainDAO_mod, "RUTA_BD", rutaBd)
    mainDAO.conn = None
    mainDAO.cursor = None
    mainDAO.conectar()
    yield rutaBd
    # Restaura el singleton para no contaminar otros tests de la suite.
    mainDAO.conn = None
    mainDAO.cursor = None


def test_mj1_creaSesionConVariasCajas(bdTemporal):
    """MJ1/COR7: crearSesion acepta varias cajas (nombre, monto).

    Cada caja arranca con Fondo_inicial = Monto = monto indicado y el
    fondo inicial de la sesión pasa a ser la suma de esas cajas (COR7).
    """
    idSesion = mainDAO.crearSesion(
        "hash-de-prueba", "2026-09-13 10:00:00",
        cajas=[("Efectivo", 300.0), ("Mercado Pago", 200.0)],
    )
    cajas = mainDAO.verCajas(idSesion)
    assert [(c[1], c[2], c[3]) for c in cajas] == [
        ("Efectivo", 300.0, 300.0),
        ("Mercado Pago", 200.0, 200.0),
    ]
    # COR7: Fondo_inicial y Caja de la sesión = suma de las cajas (500).
    sesion = mainDAO.obtenerSesion()
    assert sesion[2] == 500.0   # Fondo_inicial
    assert sesion[3] == 500.0   # Caja


def test_mj1_sinCajasCreaCajaPrincipal(bdTemporal):
    """MJ1/COR7: sin el parámetro cajas se crea la 'Caja principal' con 0.

    El fondo inicial ya no se define por separado (COR7): sin cajas
    indicadas, la caja principal arranca con monto 0.
    """
    idSesion = mainDAO.crearSesion(
        "hash-de-prueba", "2026-09-13 10:00:00"
    )
    cajas = mainDAO.verCajas(idSesion)
    assert len(cajas) == 1
    assert cajas[0][1] == "Caja principal"
    assert cajas[0][2] == 0.0   # Fondo_inicial
    assert cajas[0][3] == 0.0   # Monto


def test_mj7_verTotalCajasSumaMontos(bdTemporal):
    """MJ7: verTotalCajas devuelve la suma de los Monto de todas las cajas."""
    idSesion = mainDAO.crearSesion(
        "hash", "2026-09-13 10:00:00",
        cajas=[("Efectivo", 400.0), ("Tarjeta", 200.0)],
    )
    assert mainDAO.verTotalCajas(idSesion) == 600.0


def test_mj1_obtenerCajaPorId(bdTemporal):
    """MJ1: obtenerCaja devuelve la tupla completa o None si no existe."""
    idSesion = mainDAO.crearSesion(
        "hash", "2026-09-13 10:00:00",
        cajas=[("Efectivo", 500.0)],
    )
    idCaja = mainDAO.verCajas(idSesion)[0][0]
    fila = mainDAO.obtenerCaja(idCaja)
    assert fila[0] == idCaja          # ID_caja
    assert fila[1] == idSesion        # ID_sesion
    assert fila[2] == "Efectivo"      # Nombre
    assert mainDAO.obtenerCaja(9999) is None


def test_mj1_registrarVentaModificaCajaAsignada(bdTemporal):
    """MJ1: una venta con idCaja suma su monto a esa caja (delta)."""
    idSesion = mainDAO.crearSesion(
        "hash", "2026-09-13 10:00:00",
        cajas=[("Efectivo", 300.0), ("Mercado Pago", 200.0)],
    )
    idProducto = prodDAO().crearProducto("A", 5, 100.0, idSesion)
    idEfectivo, idMp = (c[0] for c in mainDAO.verCajas(idSesion))

    ventaDAO().registrarVenta(
        idSesion, "2026-09-13 11:00:00.000001", [(idProducto, 2, 100.0)],
        montoNeto=200.0, cajaNueva=700.0, idCaja=idEfectivo,
    )

    assert mainDAO.obtenerCaja(idEfectivo)[4] == 500.0   # 300 + 200
    assert mainDAO.obtenerCaja(idMp)[4] == 200.0          # sin cambios
    assert mainDAO.obtenerSesion()[3] == 700.0            # caja total
    assert ventaDAO().verVentas(idSesion)[0][0] > 0


def test_mj1_registrarGastoDescuentaCajaAsignada(bdTemporal):
    """MJ1: un gasto con idCaja resta su monto a esa caja (delta firmado)."""
    idSesion = mainDAO.crearSesion(
        "hash", "2026-09-13 10:00:00",
        cajas=[("Efectivo", 300.0), ("Mercado Pago", 200.0)],
    )
    idEfectivo, idMp = (c[0] for c in mainDAO.verCajas(idSesion))

    ventaDAO().registrarGasto(
        idSesion, "Insumos", -50.0, "Carteles",
        "2026-09-13 12:00:00.000001", 450.0, idCaja=idEfectivo,
    )

    assert mainDAO.obtenerCaja(idEfectivo)[4] == 250.0   # 300 - 50
    assert mainDAO.obtenerCaja(idMp)[4] == 200.0          # sin cambios
    assert mainDAO.obtenerSesion()[3] == 450.0            # caja total


def test_mj1_idCajaInexistenteElevaPersistenceError(bdTemporal):
    """MJ1: asignar una caja inexistente a una venta es PersistenceError."""
    idSesion = mainDAO.crearSesion("hash", "2026-09-13 10:00:00")
    idProducto = prodDAO().crearProducto("A", 5, 100.0, idSesion)

    with pytest.raises(PersistenceError):
        ventaDAO().registrarVenta(
            idSesion, "2026-09-13 11:00:00", [(idProducto, 1, 100.0)],
            montoNeto=100.0, cajaNueva=600.0, idCaja=9999,
        )


def test_mj1_registrarVentaSinIdCajaConservaComportamiento(bdTemporal):
    """MJ1: sin idCaja se conserva el comportamiento previo (caja principal)."""
    idSesion = mainDAO.crearSesion(
        "hash", "2026-09-13 10:00:00",
        cajas=[("Caja principal", 500.0)],
    )
    idProducto = prodDAO().crearProducto("A", 5, 100.0, idSesion)

    ventaDAO().registrarVenta(
        idSesion, "2026-09-13 11:00:00.000001", [(idProducto, 1, 100.0)],
        montoNeto=100.0, cajaNueva=600.0,
    )

    assert mainDAO.verCajas(idSesion)[0][3] == 600.0
    assert mainDAO.obtenerSesion()[3] == 600.0
    # El stock no se descuenta en el DAO de ventas (lo hace stockDAO en CU10).
    assert stockDAO().verStock(idProducto) == 5


def test_mj1_nukeLimpiaCajas(bdTemporal):
    """CU15: reiniciar (nuke) limpia también las cajas de la sesión."""
    idSesion = mainDAO.crearSesion(
        "hash", "2026-09-13 10:00:00",
        cajas=[("Efectivo", 300.0), ("Mercado Pago", 200.0)],
    )
    assert len(mainDAO.verCajas(idSesion)) == 2
    mainDAO.nuke()
    assert mainDAO.obtenerSesion() is None
    assert mainDAO.verCajas(idSesion) == []

