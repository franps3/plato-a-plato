# Módulo test_exportacion.py
# Pruebas unitarias del controlador (Agente 3) para:
#   * CU13 exportExcel(rutaDestino)   .xlsx con historial
#   * CU16 exportarDb(rutaDestino)    .zip con la sesión/BD
#   * CU17 importarDb(rutaZip, passNueva)
#
# Se ejecutan contra los DAOs falsos (FakeMainDAO.exportar/importar de
# paridad con el contrato del Agente 1). La generación real de .xlsx/.zip
# ya está cubierta por tests de integración del Agente 1.

import sys
from pathlib import Path

import pytest

# Permite importar los paquetes del proyecto desde la raíz del repo.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import tempfile

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
    ctrl.crearSesion("clave1234", 500)
    ctrl.iniciarSesion("clave1234")
    return ctrl


@pytest.fixture
def rutaTemporal():
    """Crea un directorio temporal para las exportaciones."""
    with tempfile.TemporaryDirectory() as dirTmp:
        yield Path(dirTmp)


# ---------------------------------------------------------------------------
# CU13: exportExcel(rutaDestino)
# ---------------------------------------------------------------------------

def test_cu13_exportaHistorial(controlador, rutaTemporal):
    """CU13: exporta el historial a un .xlsx y devuelve la ruta."""
    resultado = controlador.exportExcel(str(rutaTemporal))

    assert resultado["ok"] is True
    ruta = Path(resultado["datos"])
    assert ruta.suffix.lower() == ".xlsx"
    assert ruta.exists()


def test_cu13_aceptaRutaConArchivo(controlador, rutaTemporal):
    """CU13: completa extensión si la ruta apunta a una carpeta."""
    destino = rutaTemporal / "mi_historial"
    resultado = controlador.exportExcel(str(destino))

    assert resultado["ok"] is True
    assert Path(resultado["datos"]).exists()


# ---------------------------------------------------------------------------
# CU16: exportarDb(rutaDestino)
# ---------------------------------------------------------------------------

def test_cu16_exportaSesion(controlador, rutaTemporal):
    """CU16: empaqueta la sesión (BD) en un .zip y devuelve la ruta."""
    resultado = controlador.exportarDb(str(rutaTemporal))

    assert resultado["ok"] is True
    ruta = Path(resultado["datos"])
    assert ruta.suffix.lower() == ".zip"
    assert ruta.exists()


# ---------------------------------------------------------------------------
# CU17: importarDb(rutaZip, passNueva)
# ---------------------------------------------------------------------------

def test_cu17_importaSesionConClave(controlador, rutaTemporal):
    """CU17: importa un zip, hashea la clave y asigna la sesión."""
    rutaZip = rutaTemporal / "sesion.zip"
    rutaZip.touch()

    resultado = controlador.importarDb(str(rutaZip), "nuevaClave")

    assert resultado["ok"] is True
    sesionBd = controlador.dao.obtenerSesion()
    # La clave nueva llegó HASHEADA y se guardó como Pass de la sesión.
    assert sesionBd[4] == Controlador.hashearPassword("nuevaClave")
    assert controlador.estaAutenticado() is True


def test_cu17_fallaClaveCorta(controlador, rutaTemporal):
    """CU17: rechaza una clave de menos de 4 caracteres antes de importar."""
    rutaZip = rutaTemporal / "sesion.zip"
    rutaZip.touch()

    resultado = controlador.importarDb(str(rutaZip), "abc")

    assert resultado["ok"] is False
    assert "4 caracteres" in resultado["mensaje"]


def test_cu17_fallaZipInexistente(controlador, rutaTemporal):
    """CU17: un zip inexistente eleva PersistenceError -> ok=False."""
    resultado = controlador.importarDb(str(rutaTemporal / "nada.zip"), "clave1234")

    assert resultado["ok"] is False
    assert "no existe" in resultado["mensaje"]