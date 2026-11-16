# Módulo test_productos.py
# Pruebas unitarias del controlador (Agente 3) para los casos de uso
# CU4 (crear producto), CU5 (ver productos), CU7 (editar producto/stock)
# y CU8 (eliminar producto). CU6 es una tarea exclusivamente visual
# (habilita menú editar/borrar) y no requiere lógica de controlador.
#
# Se ejecutan contra DAOs falsos en memoria con estado compartido (FakeBD)
# y una sesión activa creada previamente (CU1 + CU2).

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Permite importar los paquetes del proyecto desde la raíz del repo.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from control.controlador import Controlador
from tests.fakeMainDAO import FakeBD, FakeMainDAO, FakeProdDAO, FakeStockDAO
from vistas.config import VistaConfigProductos
from vistas.venta import VistaVenta


@pytest.fixture
def controlador():
    """Controlador con DAOs falsos compartiendo estado y sesión activa."""
    bd = FakeBD()
    ctrl = Controlador(
        dao=FakeMainDAO(bd),
        prodDAO=FakeProdDAO(bd),
        stockDAO=FakeStockDAO(bd),
    )
    ctrl.crearSesion("clave1234", cajas=[("Caja principal", 500)])
    ctrl.iniciarSesion("clave1234")
    return ctrl


# ---------------------------------------------------------------------------
# CU4: crearProducto(nombre, stockInicial, precio)
# ---------------------------------------------------------------------------

def test_cu4_creaProductoValido(controlador):
    """CU4: agrega el ítem al catálogo con sus datos y stock inicial."""
    resultado = controlador.crearProducto("Milanesa", 10, 2500)

    assert resultado["ok"] is True
    producto = resultado["datos"]
    assert producto.nombre == "Milanesa"
    assert producto.precio == 2500.0
    assert producto.stock == 10
    # El stock queda persistido y consultable vía stockDAO.
    assert controlador.servStock.verStock(producto.idProducto) == 10


def test_cu4_aceptaStockCero(controlador):
    """CU4: un stock inicial de 0 es válido (>= 0)."""
    resultado = controlador.crearProducto("Pan", 0, 500)

    assert resultado["ok"] is True
    assert resultado["datos"].stock == 0


def test_cu4_fallaNombreVacio(controlador):
    """CU4: rechaza nombres vacíos o no textuales."""
    for nombre in ["", "   ", None, 123]:
        resultado = controlador.crearProducto(nombre, 5, 1000)
        assert resultado["ok"] is False
        assert "nombre" in resultado["mensaje"].lower()


def test_cu4_fallaPrecioNegativo(controlador):
    """CU4: rechaza un precio negativo."""
    resultado = controlador.crearProducto("Salchicha", 5, -1)

    assert resultado["ok"] is False
    assert "precio" in resultado["mensaje"].lower()


def test_cu4_fallaPrecioInvalido(controlador):
    """CU4: rechaza precios no numéricos o vacíos."""
    for precio in ["abc", "", None, True]:
        resultado = controlador.crearProducto("Salchicha", 5, precio)
        assert resultado["ok"] is False
        assert "precio" in resultado["mensaje"].lower()
def test_cu4_fallaStockInvalido(controlador):
    """CU4: rechaza stocks negativos, no enteros o no numéricos."""
    for stock in [-1, 2.5, "5", None, True]:
        resultado = controlador.crearProducto("Empanada", stock, 800)
        assert resultado["ok"] is False
        assert "stock" in resultado["mensaje"].lower()


# ---------------------------------------------------------------------------
# CU5: verProductos()
# ---------------------------------------------------------------------------

def test_cu5_listaProductosConStock(controlador):
    """CU5: despliega el listado completo con stock por cada ítem."""
    controlador.crearProducto("A", 3, 100)
    controlador.crearProducto("B", 7, 200)

    resultado = controlador.verProductos()

    assert resultado["ok"] is True
    productos = resultado["datos"]
    assert len(productos) == 2
    stocks = {p.idProducto: p.stock for p in productos}
    assert set(stocks.values()) == {3, 7}


def test_cu5_listaVaciaSinProductos(controlador):
    """CU5: sin productos el listado es una lista vacía (ok True)."""
    resultado = controlador.verProductos()

    assert resultado["ok"] is True
    assert resultado["datos"] == []


# ---------------------------------------------------------------------------
# CU7: editarProducto(idProducto, nombre, precio) / editarStock(idProducto, stock)
# ---------------------------------------------------------------------------

def test_cu7_editaProducto(controlador):
    """CU7: modifica nombre y precio y refresca los datos."""
    creado = controlador.crearProducto("A", 3, 100)["datos"]

    resultado = controlador.editarProducto(creado.idProducto, "A2", 150)

    assert resultado["ok"] is True
    assert resultado["datos"].nombre == "A2"
    assert resultado["datos"].precio == 150.0


def test_cu7_editaProductoNoExiste(controlador):
    """CU7: no se puede editar un producto inexistente."""
    resultado = controlador.editarProducto(999, "X", 100)

    assert resultado["ok"] is False
    assert "producto" in resultado["mensaje"].lower()


def test_cu7_editaStock(controlador):
    """CU7: modifica el stock vía editarStock."""
    creado = controlador.crearProducto("A", 3, 100)["datos"]

    resultado = controlador.editarStock(creado.idProducto, 15)

    assert resultado["ok"] is True
    assert resultado["datos"] == 15
    assert controlador.servStock.verStock(creado.idProducto) == 15


def test_cu7_editaStockInvalido(controlador):
    """CU7: rechaza ediciones de stock con valores inválidos."""
    creado = controlador.crearProducto("A", 3, 100)["datos"]

    for stock in [-2, 1.5, "x", None]:
        resultado = controlador.editarStock(creado.idProducto, stock)
        assert resultado["ok"] is False
        assert "stock" in resultado["mensaje"].lower()

    # El stock original no se altera tras intentos fallidos.
    assert controlador.servStock.verStock(creado.idProducto) == 3


def test_cu7_editaStockNoExiste(controlador):
    """CU7: no se puede editar el stock de un producto inexistente."""
    resultado = controlador.editarStock(999, 5)

    assert resultado["ok"] is False


# ---------------------------------------------------------------------------
# CU8: eliminarProducto(idProducto)
# ---------------------------------------------------------------------------

def test_cu8_eliminaProducto(controlador):
    """CU8: da de baja el producto de la lista activa."""
    creado = controlador.crearProducto("A", 3, 100)["datos"]

    resultado = controlador.eliminarProducto(creado.idProducto)

    assert resultado["ok"] is True
    assert controlador.verProductos()["datos"] == []


def test_cu8_eliminaNoExiste(controlador):
    """CU8: no se puede eliminar un producto inexistente."""
    resultado = controlador.eliminarProducto(999)

    assert resultado["ok"] is False


def test_cu8_prohibidoEliminarEnCarrito(controlador):
    """CU8: está prohibido eliminar un producto que está en el carrito."""
    creado = controlador.crearProducto("A", 3, 100)["datos"]
    controlador.carrito[creado.idProducto] = 2

    resultado = controlador.eliminarProducto(creado.idProducto)

    assert resultado["ok"] is False
    assert "carrito" in resultado["mensaje"].lower()
    # El producto sigue en el catálogo.
    assert len(controlador.verProductos()["datos"]) == 1


def test_combo_no_muestra_stock_en_venta():
    """Los combos no deben renderizar un valor de stock en la lista de venta."""
    productoCombo = SimpleNamespace(idProducto=7, nombre="Combo", stock=99)
    productoNormal = SimpleNamespace(idProducto=3, nombre="Hamburguesa", stock=5)

    assert VistaVenta._textoStock(productoCombo, {7}) == ""
    assert VistaVenta._textoStock(productoNormal, {7}) == "5"


def test_config_separa_productos_y_combos():
    """La configuración debe listar productos comunes y combos por separado."""
    producto = SimpleNamespace(idProducto=1, nombre="Hamburguesa", stock=3)
    combo = SimpleNamespace(idProducto=7, nombre="Combo", stock=0)
    items = [producto, combo]

    assert VistaConfigProductos._filtrarProductos(items, {7}) == [producto]
    assert VistaConfigProductos._filtrarCombos(items, {7}) == [combo]