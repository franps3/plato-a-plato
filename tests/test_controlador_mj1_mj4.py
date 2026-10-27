# Módulo test_controlador_mj1_mj4.py
# Pruebas unitarias del controlador (Agente 3) para las mejoras:
#   MJ1 (multiples cajas / medios de pago): crearSesion con cajas,
#   verCajas, verTotalCajas, obtenerCaja.
#   MJ4 (combos): crearCombo, verCombos, verComponentesCombo,
#   editarCombo, eliminarCombo.
# Se ejecutan contra fakes en memoria; no requieren la base SQLite real
# ni librerías de UI.

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from control.controlador import Controlador
from tests.fakeMainDAO import (
    FakeBD, FakeMainDAO, FakeProdDAO, FakeStockDAO, FakeVentaDAO,
)


@pytest.fixture
def controlador():
    """Controlador con DAOs falsos compartiendo un mismo FakeBD."""
    bd = FakeBD()
    return Controlador(
        dao=FakeMainDAO(bd=bd),
        prodDAO=FakeProdDAO(bd=bd),
        stockDAO=FakeStockDAO(bd=bd),
        ventaDAO=FakeVentaDAO(bd=bd),
    )


def _idCaja(controlador):
    """Devuelve el ID de la primera caja registrada en el FakeBD."""
    return list(controlador.dao._bd.cajas.keys())[0]


# ---------------------------------------------------------------------------
# MJ1: cajas (medios de pago)
# ---------------------------------------------------------------------------

def test_mj1_creaSesionConCajasMultiples(controlador):
    """MJ1: crearSesion acepta lista de cajas y crea una por item."""
    cajas = [("Efectivo", 300.00), ("MercadoPago", 200.00)]
    resultado = controlador.crearSesion("clave1234", cajas=cajas)

    assert resultado["ok"] is True
    sesion = resultado["datos"]
    assert sesion.fondoInicial == 500.00
    assert sesion.caja == 500.00

    cajasBd = controlador.dao.verCajas(sesion.idSesion)
    assert len(cajasBd) == 2
    nombres = {c[1] for c in cajasBd}
    assert nombres == {"Efectivo", "MercadoPago"}
    montos = {c[1]: c[3] for c in cajasBd}
    assert montos["Efectivo"] == 300.00
    assert montos["MercadoPago"] == 200.00


def test_mj1_creaSesionSinCajasCreaCajaPrincipal(controlador):
    """MJ1: si no se pasan cajas, se crea la 'Caja principal' (CU1 intacto)."""
    resultado = controlador.crearSesion("clave1234")

    assert resultado["ok"] is True
    sesion = resultado["datos"]
    cajasBd = controlador.dao.verCajas(sesion.idSesion)
    assert len(cajasBd) == 1
    assert cajasBd[0][1] == "Caja principal"
    assert cajasBd[0][3] == 0.00


def test_mj1_verCajas(controlador):
    """MJ1: verCajas lista las cajas de la sesión."""
    controlador.crearSesion("clave1234",
                            cajas=[("Efectivo", 300.00), ("Tarjeta", 700.00)])
    sesion = controlador.sesionActiva

    resultado = controlador.verCajas(sesion.idSesion)
    assert resultado["ok"] is True
    cajas = resultado["datos"]
    assert len(cajas) == 2
    assert all(hasattr(c, "idCaja") and hasattr(c, "monto") for c in cajas)
    nombres = {c.nombre for c in cajas}
    assert nombres == {"Efectivo", "Tarjeta"}


def test_mj1_verTotalCajas(controlador):
    """MJ1/MJ7: verTotalCajas suma los Monto de todas las cajas."""
    controlador.crearSesion("clave1234",
                            cajas=[("Efectivo", 300.00), ("Tarjeta", 700.00)])
    sesion = controlador.sesionActiva

    resultado = controlador.verTotalCajas(sesion.idSesion)
    assert resultado["ok"] is True
    assert resultado["datos"] == 1000.00


def test_mj1_obtenerCaja(controlador):
    """MJ1: obtenerCaja devuelve una caja por su ID."""
    controlador.crearSesion("clave1234",
                            cajas=[("Efectivo", 300.00)])
    idCaja = _idCaja(controlador)

    resultado = controlador.obtenerCaja(idCaja)
    assert resultado["ok"] is True
    caja = resultado["datos"]
    assert caja.idCaja == idCaja
    assert caja.nombre == "Efectivo"
    assert caja.monto == 300.00


def test_mj1_obtenerCajaNoExiste(controlador):
    """MJ1: obtenerCaja con ID inexistente falla."""
    controlador.crearSesion("clave1234",
                            cajas=[("Caja principal", 500.00)])

    resultado = controlador.obtenerCaja(9999)
    assert resultado["ok"] is False
    assert "no existe" in resultado["mensaje"].lower()


def test_mj1_confirmarVentaAceptaIdCaja(controlador):
    """MJ1: confirmarVenta acepta idCaja (falla por carrito vacío, no por caja)."""
    controlador.crearSesion("clave1234",
                            cajas=[("Efectivo", 300.00)])
    idCaja = _idCaja(controlador)

    resultado = controlador.confirmarVenta(idCaja=idCaja)
    assert resultado["ok"] is False
    assert "carrito" in resultado["mensaje"].lower()



# ---------------------------------------------------------------------------
# MJ4: combos
# ---------------------------------------------------------------------------

def _crearProducto(controlador, nombre, precio, stock=10):
    """Helper: crea un producto y devuelve su idProducto."""
    resultado = controlador.crearProducto(nombre, stock, precio)
    assert resultado["ok"] is True
    return resultado["datos"].idProducto


def _crearSesionYProductos(controlador):
    """Helper: crea sesión y dos productos para usar como componentes."""
    controlador.crearSesion("clave1234", cajas=[("Caja principal", 1000.00)])
    idHamburguesa = _crearProducto(controlador, "Hamburguesa", 2500.00, 10)
    idPapas = _crearProducto(controlador, "Papas fritas", 1500.00, 20)
    return idHamburguesa, idPapas


def test_mj4_crearCombo(controlador):
    """MJ4: crearCombo registra un combo y devuelve su idCombo."""
    idHamburguesa, idPapas = _crearSesionYProductos(controlador)

    componentes = [(idHamburguesa, 1), (idPapas, 1)]
    resultado = controlador.crearCombo("Combo clasico", 3500.00, componentes)

    assert resultado["ok"] is True
    idCombo = resultado["datos"]
    assert isinstance(idCombo, int) and idCombo > 0


def test_mj4_crearComboValidaComponentes(controlador):
    """MJ4: crearCombo rechaza componentes vacíos, cantidad <= 0 o nombre vacío."""
    idHamburguesa, _ = _crearSesionYProductos(controlador)

    # Componentes vacios se permiten (combo sin componentes); solo se
    # rechazan cantidad <= 0 y nombre invalido.
    assert controlador.crearCombo("Combo malo", 100.00,
                                  [(idHamburguesa, 0)])["ok"] is False
    assert controlador.crearCombo("", 100.00,
                                  [(idHamburguesa, 1)])["ok"] is False


def test_mj4_verCombos(controlador):
    """MJ4: verCombos lista los combos creados en la sesión."""
    idHamburguesa, idPapas = _crearSesionYProductos(controlador)
    controlador.crearCombo("Combo A", 3000.00,
                           [(idHamburguesa, 1), (idPapas, 1)])
    controlador.crearCombo("Combo B", 4000.00, [(idHamburguesa, 2)])

    resultado = controlador.verCombos()
    assert resultado["ok"] is True
    combos = resultado["datos"]
    assert len(combos) == 2
    nombres = {c[1] for c in combos}
    assert nombres == {"Combo A", "Combo B"}


def test_mj4_verComponentesCombo(controlador):
    """MJ4: verComponentesCombo devuelve los componentes de un combo."""
    idHamburguesa, idPapas = _crearSesionYProductos(controlador)
    resultado = controlador.crearCombo("Combo mixto", 3500.00,
                                       [(idHamburguesa, 1), (idPapas, 2)])
    idCombo = resultado["datos"]

    resultado = controlador.verComponentesCombo(idCombo)
    assert resultado["ok"] is True
    componentes = resultado["datos"]
    assert len(componentes) == 2
    ids = {c[0] for c in componentes}
    assert ids == {idHamburguesa, idPapas}
    cantidades = {c[0]: c[1] for c in componentes}
    assert cantidades[idHamburguesa] == 1
    assert cantidades[idPapas] == 2


def test_mj4_editarCombo(controlador):
    """MJ4: editarCombo actualiza nombre, precio y componentes."""
    idHamburguesa, idPapas = _crearSesionYProductos(controlador)
    resultado = controlador.crearCombo("Combo viejo", 3000.00,
                                       [(idHamburguesa, 1)])
    idCombo = resultado["datos"]

    nuevo = [(idPapas, 3)]
    resultado = controlador.editarCombo(idCombo, "Combo nuevo", 4500.00, nuevo)
    assert resultado["ok"] is True
    datos = resultado["datos"]
    assert datos[0] == idCombo
    assert datos[1] == "Combo nuevo"
    assert datos[2] == 4500.00

    resultado = controlador.verComponentesCombo(idCombo)
    componentes = resultado["datos"]
    assert len(componentes) == 1
    assert componentes[0] == (idPapas, 3)


def test_mj4_editarComboNoExiste(controlador):
    """MJ4: editarCombo con id inexistente falla."""
    assert controlador.editarCombo(9999, "X", 10.00, [])["ok"] is False


def test_mj4_eliminarCombo(controlador):
    """MJ4: eliminarCombo borra el combo y sus componentes."""
    idHamburguesa, _ = _crearSesionYProductos(controlador)
    resultado = controlador.crearCombo("Para borrar", 1000.00,
                                       [(idHamburguesa, 1)])
    idCombo = resultado["datos"]

    resultado = controlador.eliminarCombo(idCombo)
    assert resultado["ok"] is True
    assert resultado["datos"] == 1

    resultado = controlador.verCombos()
    assert resultado["ok"] is True
    assert len(resultado["datos"]) == 0


def test_mj4_eliminarComboNoExiste(controlador):
    """MJ4: eliminarCombo con id inexistente devuelve ok=False."""
    assert controlador.eliminarCombo(9999)["ok"] is False
