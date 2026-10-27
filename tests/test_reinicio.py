# Módulo test_reinicio.py
# Pruebas unitarias del controlador (Agente 3) para:
#   * haySesion()              (bloqueo Agente 2: pantalla correcta de login)
#   * quitarProdCompleto(idProducto) (bloqueo Agente 2: quitar producto del carrito)
#   * CU14 borrarHistorial(password)
#   * CU15 reiniciar(password)
#
# Se ejecutan contra DAOs falsos en memoria con estado compartido (FakeBD).

import sys
from pathlib import Path

import pytest

# Permite importar los paquetes del proyecto desde la raíz del repo.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from control.controlador import Controlador
from tests.fakeMainDAO import (
    FakeBD,
    FakeMainDAO,
    FakeProdDAO,
    FakeStockDAO,
    FakeVentaDAO,
)


@pytest.fixture
def controlador():
    """Controlador con DAOs falsos compartiendo estado y sesión activa."""
    bd = FakeBD()
    ctrl = Controlador(
        dao=FakeMainDAO(bd),
        prodDAO=FakeProdDAO(bd),
        stockDAO=FakeStockDAO(bd),
        ventaDAO=FakeVentaDAO(bd),
    )
    ctrl.crearSesion("clave1234", cajas=[("Caja principal", 500)])
    ctrl.iniciarSesion("clave1234")
    return ctrl


def _generarMovimientos(controlador):
    """Deja una venta y un gasto registrados en la sesión."""
    p = controlador.crearProducto("Empanada", 10, 150)["datos"]
    controlador.agregarProd(p.idProducto)
    controlador.confirmarVenta()
    controlador.gasto("Compra insumos", "Carteles", 50)
    return p.idProducto


# ---------------------------------------------------------------------------
# haySesion() (bloqueo del Agente 2)
# ---------------------------------------------------------------------------

def test_haySesion_trueConSesionCreada(controlador):
    """haySesion: devuelve True si existe una sesión en la base."""
    resultado = controlador.haySesion()

    assert resultado["ok"] is True
    assert resultado["datos"] is True


def test_haySesion_falseSinSesion():
    """haySesion: devuelve False cuando no hay sesión en la base."""
    bd = FakeBD()
    ctrl = Controlador(
        dao=FakeMainDAO(bd),
        prodDAO=FakeProdDAO(bd),
        stockDAO=FakeStockDAO(bd),
        ventaDAO=FakeVentaDAO(bd),
    )
    resultado = ctrl.haySesion()

    assert resultado["ok"] is True
    assert resultado["datos"] is False


# ---------------------------------------------------------------------------
# quitarProdCompleto(idProducto) (bloqueo del Agente 2)
# ---------------------------------------------------------------------------

def test_quitarProdCompleto_eliminaProductoDelCarrito(controlador):
    """quitarProdCompleto: quita el producto por completo del carrito."""
    p = controlador.crearProducto("Hamburguesa", 10, 200)["datos"]
    controlador.agregarProd(p.idProducto)
    controlador.agregarProd(p.idProducto)
    assert controlador.carrito.get(p.idProducto) == 2

    resultado = controlador.quitarProdCompleto(p.idProducto)

    assert resultado["ok"] is True
    assert p.idProducto not in controlador.carrito


def test_quitarProdCompleto_sobreProductoAusenteNoRompe(controlador):
    """quitarProdCompleto: sobre un producto ausente del carrito es inofensivo."""
    resultado = controlador.quitarProdCompleto(999)

    assert resultado["ok"] is True
# ---------------------------------------------------------------------------
# CU14: borrarHistorial(password)
# ---------------------------------------------------------------------------

def test_cu14_borraHistorialConPasswordCorrecta(controlador):
    """CU14: con la contraseña correcta limpia ventas y gastos pero
    conserva productos y sesión (stock intacto)."""
    idProducto = _generarMovimientos(controlador)
    assert len(controlador.verHistorial()["datos"]) == 2
    stockAntes = controlador.servStock.verStock(idProducto)

    resultado = controlador.borrarHistorial("clave1234")

    assert resultado["ok"] is True
    # Historial vacío.
    assert controlador.verHistorial()["datos"] == []
    # Productos y stock intactos.
    assert len(controlador.verProductos()["datos"]) == 1
    assert controlador.servStock.verStock(idProducto) == stockAntes
    # La sesión sigue activa.
    assert controlador.estaAutenticado() is True


def test_cu14_noBorraConPasswordIncorrecta(controlador):
    """CU14: con contraseña incorrecta devuelve ok=False y no borra nada."""
    _generarMovimientos(controlador)

    resultado = controlador.borrarHistorial("incorrecta")

    assert resultado["ok"] is False
    assert "contrase" in resultado["mensaje"].lower()
    assert len(controlador.verHistorial()["datos"]) == 2


def test_cu14_noBorraConPasswordCorta(controlador):
    """CU14: rechaza contraseñas de menos de 4 caracteres."""
    _generarMovimientos(controlador)

    resultado = controlador.borrarHistorial("abc")

    assert resultado["ok"] is False
    assert len(controlador.verHistorial()["datos"]) == 2


# ---------------------------------------------------------------------------
# CU15: reiniciar(password)
# ---------------------------------------------------------------------------

def test_cu15_reiniciaSistemaConPasswordCorrecta(controlador):
    """CU15: con la contraseña correcta borra la BD local y limpia el
    estado en memoria (se cierra la sesión)."""
    _generarMovimientos(controlador)

    resultado = controlador.reiniciar("clave1234")

    assert resultado["ok"] is True
    # Estado en memoria a cero.
    assert controlador.estaAutenticado() is False
    assert controlador.carrito == {}
    # La base quedó sin datos: no hay sesión ni movimientos.
    assert controlador.haySesion()["datos"] is False


def test_cu15_noReiniciaConPasswordIncorrecta(controlador):
    """CU15: con contraseña incorrecta devuelve ok=False y no borra nada."""
    _generarMovimientos(controlador)

    resultado = controlador.reiniciar("incorrecta")

    assert resultado["ok"] is False
    assert "contrase" in resultado["mensaje"].lower()
    # Sigue todo igual: sesión activa y movimientos presentes.
    assert controlador.estaAutenticado() is True
    assert len(controlador.verHistorial()["datos"]) == 2


def test_cu15_noReiniciaConPasswordCorta(controlador):
    """CU15: rechaza contraseñas de menos de 4 caracteres."""
    _generarMovimientos(controlador)

    resultado = controlador.reiniciar("abc")

    assert resultado["ok"] is False
    assert controlador.estaAutenticado() is True


def test_cu15_trasReiniciarSePuedeCrearSesionNueva(controlador):
    """CU15: tras reiniciar se puede crear una sesión nueva sin conflictos."""
    _generarMovimientos(controlador)
    controlador.reiniciar("clave1234")

    resultado = controlador.crearSesion("nuevaClave",
                                        cajas=[("Caja principal", 1000)])

    assert resultado["ok"] is True
    assert controlador.estaAutenticado() is True
    assert controlador.sesionActiva.caja == 1000.0
    assert controlador.carrito == {}