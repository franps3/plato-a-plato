# Módulo test_venta.py
# Pruebas unitarias del controlador (Agente 3) para los casos de uso
# CU9 (agregar/quitar a venta), CU10 (registrar venta), CU11 (gasto y
# reinserción de dinero) y CU12 (ver historial).
#
# Se ejecutan contra DAOs falsos en memoria con estado compartido (FakeBD)
# y una sesión activa creada previamente (CU1 + CU2).

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


@pytest.fixture
def catalogo(controlador):
    """Catálogo con tres productos: A (stock 5, precio 100), B (stock 3,
    precio 200) y C (stock 10, precio 50). Devuelve sus idProducto."""
    a = controlador.crearProducto("A", 5, 100)["datos"]
    b = controlador.crearProducto("B", 3, 200)["datos"]
    c = controlador.crearProducto("C", 10, 50)["datos"]
    return {"A": a.idProducto, "B": b.idProducto, "C": c.idProducto}


# ---------------------------------------------------------------------------
# CU9: agregarProd(idProducto) / quitarProd(idProducto)
# ---------------------------------------------------------------------------

def test_cu9_agregarYQuitarProducto(controlador, catalogo):
    """CU9: agrega y elimina del carrito con los botones (+/-)."""
    idA = catalogo["A"]

    # Suma dos unidades.
    resultado = controlador.agregarProd(idA)
    assert resultado["ok"] is True
    assert resultado["datos"] == 1
    resultado = controlador.agregarProd(idA)
    assert resultado["datos"] == 2
    assert controlador.carrito[idA] == 2

    # Resta una unidad: queda en 1.
    resultado = controlador.quitarProd(idA)
    assert resultado["ok"] is True
    assert resultado["datos"] == 1
    assert controlador.carrito[idA] == 1

    # Resta otra: llega a 0 y se elimina del carrito.
    controlador.quitarProd(idA)
    assert idA not in controlador.carrito


def test_cu9_noSuperaStockDisponible(controlador, catalogo):
    """CU9: no se pueden agregar más unidades de las que hay en stock."""
    idB = catalogo["B"]  # stock 3

    for _ in range(3):
        resultado = controlador.agregarProd(idB)
        assert resultado["ok"] is True

    resultado = controlador.agregarProd(idB)
    assert resultado["ok"] is False
    assert "stock" in resultado["mensaje"].lower()
    assert controlador.carrito[idB] == 3


def test_cu9_agregarProductoInexistente(controlador):
    """CU9: no se puede agregar un producto que no existe."""
    resultado = controlador.agregarProd(999)

    assert resultado["ok"] is False
    assert "producto" in resultado["mensaje"].lower()


# ---------------------------------------------------------------------------
# CU10: confirmarVenta()
# ---------------------------------------------------------------------------

def test_cu10_confirmaVentaMultiproducto(controlador, catalogo):
    """CU10: registra venta, descuenta stock, suma total a caja y vacía
    el carrito."""
    idA, idB = catalogo["A"], catalogo["B"]
    controlador.agregarProd(idA)
    controlador.agregarProd(idA)
    controlador.agregarProd(idB)

    resultado = controlador.confirmarVenta()

    assert resultado["ok"] is True
    venta = resultado["datos"]
    # Total = 2 * 100 + 1 * 200 = 400.
    assert venta.montoNeto == 400.0
    assert len(venta.detalles) == 2
    # Caja inicial 500 + 400 = 900.
    assert controlador.sesionActiva.caja == 900.0
    # Carrito vacío.
    assert controlador.carrito == {}
    # Stock descontado: A 5-2=3, B 3-1=2.
    assert controlador.servStock.verStock(idA) == 3
    assert controlador.servStock.verStock(idB) == 2


def test_cu10_fallaConCarritoVacio(controlador):
    """CU10: confirmar con el carrito vacío devuelve ok=False."""
    resultado = controlador.confirmarVenta()

    assert resultado["ok"] is False
    assert "carrito" in resultado["mensaje"].lower()


def test_cu10_fallaSiStockInsuficiente(controlador, catalogo):
    """CU10: stock insuficiente al confirmar -> DomainError y no se
    registra la venta ni se descuenta stock."""
    idC = catalogo["C"]  # stock 10, precio 50
    for _ in range(8):
        controlador.agregarProd(idC)

    # Reduce el stock a 5 por otro medio (editando stock).
    controlador.editarStock(idC, 5)

    resultado = controlador.confirmarVenta()

    assert resultado["ok"] is False
    assert "stock" in resultado["mensaje"].lower()
    # No se descuenta nada y el carrito conserva su estado.
    assert controlador.servStock.verStock(idC) == 5
    assert controlador.carrito[idC] == 8
# ---------------------------------------------------------------------------
# CU11: gasto(nombre, desc, monto) / reinsertar(nombre, desc, monto)
# ---------------------------------------------------------------------------

def test_cu11_registraGasto(controlador):
    """CU11: registra egreso y descuenta el valor de caja."""
    resultado = controlador.gasto("Compra de insumos", "Platos y vasos", 100)

    assert resultado["ok"] is True
    gasto = resultado["datos"]
    assert gasto.monto < 0  # Gasto se guarda firmado en negativo.
    assert gasto.nombre == "Compra de insumos"
    # Caja inicial 500 - 100 = 400.
    assert controlador.sesionActiva.caja == 400.0


def test_cu11_fallaGastoMayorACaja(controlador):
    """CU11: no se puede dejar la caja en negativo (saldo insuficiente)."""
    resultado = controlador.gasto("Alquiler", "Mantenimiento", 99999)

    assert resultado["ok"] is False
    assert "saldo" in resultado["mensaje"].lower()
    # La caja no cambió.
    assert controlador.sesionActiva.caja == 500.0


def test_cu11_fallaMontoInvalido(controlador):
    """CU11: rechaza montos negativos, cero, no numéricos o vacíos."""
    for monto in [-1, 0, "abc", None, True]:
        resultado = controlador.gasto("Cualquiera", "x", monto)
        assert resultado["ok"] is False
        assert "monto" in resultado["mensaje"].lower()
        resultado = controlador.reinsertar("Cualquiera", "x", monto)
        assert resultado["ok"] is False
        assert "monto" in resultado["mensaje"].lower()


def test_cu11_registraReinsercion(controlador):
    """CU11: la reinserción suma dinero a caja (monto firmado positivo)."""
    resultado = controlador.reinsertar("Vuelto sobrante", "Reposición de caja", 250)

    assert resultado["ok"] is True
    gasto = resultado["datos"]
    assert gasto.monto > 0  # Reinserción se guarda firmada en positivo.
    # Caja inicial 500 + 250 = 750.
    assert controlador.sesionActiva.caja == 750.0


def test_cu11_gastoYReinsercionEnCaja(controlador):
    """CU11: secuencia gasto + reinserción actualiza la caja en orden."""
    controlador.gasto("Insumos", "Servilletas", 100)     # 500 - 100 = 400
    controlador.reinsertar("Caja de ahorro", "Prestamo", 300)  # 400 + 300 = 700

    assert controlador.sesionActiva.caja == 700.0


# ---------------------------------------------------------------------------
# CU12: verHistorial()
# ---------------------------------------------------------------------------

def test_cu12_historialMezclaVentasYGastos(controlador, catalogo):
    """CU12: lista única de movimientos con ventas (detalles) y gastos,
    ordenada de más reciente a más antiguo."""
    idA, idB = catalogo["A"], catalogo["B"]
    controlador.agregarProd(idA)
    controlador.confirmarVenta()
    controlador.gasto("Compra insumos", "Carteles", 50)

    resultado = controlador.verHistorial()

    assert resultado["ok"] is True
    movimientos = resultado["datos"]
    assert len(movimientos) == 2

    # Orden descendente: primero el gasto (más reciente) y luego la venta.
    assert movimientos[0]["tipo"] == "gasto"
    assert movimientos[0]["montoNeto"] == 50.0
    assert movimientos[0]["nombre"] == "Compra insumos"
    assert movimientos[0]["descripcion"] == "Carteles"

    assert movimientos[1]["tipo"] == "venta"
    assert movimientos[1]["montoNeto"] == 100.0
    assert movimientos[1]["detalles"] == [
        {"nombre": "A", "cantidad": 1, "monto": 100.0}
    ]


def test_cu12_historialConReinsercion(controlador):
    """CU12: una reinserción figura como tipo 'reinsertar' con montoNeto
    positivo (valor absoluto)."""
    controlador.reinsertar("Reposicion", "Sobrante", 120)

    movimientos = controlador.verHistorial()["datos"]

    assert len(movimientos) == 1
    assert movimientos[0]["tipo"] == "reinsertar"
    assert movimientos[0]["montoNeto"] == 120.0


def test_cu12_historialVacio(controlador):
    """CU12: sin movimientos el historial es una lista vacía (ok True)."""
    resultado = controlador.verHistorial()

    assert resultado["ok"] is True
    assert resultado["datos"] == []

# ---------------------------------------------------------------------------
# COR2: verProductosVenta() (descuento de stock en vivo, reserva visual)
# ---------------------------------------------------------------------------

def test_cor2_descuentaReservaDelCarrito(controlador, catalogo):
    """COR2: verProductosVenta resta del stock lo reservado en el carrito."""
    idA = catalogo["A"]  # stock 5

    controlador.agregarProd(idA)
    controlador.agregarProd(idA)

    disponibles = {
        p.idProducto: p.stock
        for p in controlador.verProductosVenta()["datos"]
    }
    # Stock real 5 - 2 en el carrito = 3 disponibles.
    assert disponibles[idA] == 3


def test_cor2_verProductosMantieneStockReal(controlador, catalogo):
    """COR2: verProductos (Config) sigue mostrando el stock real de la bd."""
    idA = catalogo["A"]  # stock 5

    controlador.agregarProd(idA)

    stocks = {
        p.idProducto: p.stock
        for p in controlador.verProductos()["datos"]
    }
    assert stocks[idA] == 5  # la reserva del carrito no lo afecta.


def test_cor2_quitarProdDevuelveReserva(controlador, catalogo):
    """COR2: al quitar del carrito vuelve a subir el disponible en venta."""
    idA = catalogo["A"]  # stock 5

    controlador.agregarProd(idA)
    controlador.agregarProd(idA)
    controlador.quitarProd(idA)  # queda 1 unidad en el carrito.

    disponibles = {
        p.idProducto: p.stock
        for p in controlador.verProductosVenta()["datos"]
    }
    assert disponibles[idA] == 4


def test_cor2_disponibleNuncaNegativo(controlador, catalogo):
    """COR2: si la reserva superara el stock, el disponible queda en 0."""
    idC = catalogo["C"]  # stock 10
    # Simula una reserva mayor al stock real (estado interno del carrito).
    controlador.carrito[idC] = 12

    disponibles = {
        p.idProducto: p.stock
        for p in controlador.verProductosVenta()["datos"]
    }
    assert disponibles[idC] == 0


def test_cor2_confirmarVentaDescuentaReal(controlador, catalogo):
    """COR2: tras confirmar, el stock real baja y el carrito se vacía."""
    idA = catalogo["A"]  # stock 5

    controlador.agregarProd(idA)
    controlador.agregarProd(idA)
    resultado = controlador.confirmarVenta()

    assert resultado["ok"] is True
    # El stock real en la bd bajó de 5 a 3.
    assert controlador.servStock.verStock(idA) == 3
    assert controlador.carrito == {}
    # Y el disponible vuelve a coincidir con el real.
    disponibles = {
        p.idProducto: p.stock
        for p in controlador.verProductosVenta()["datos"]
    }
    assert disponibles[idA] == 3
