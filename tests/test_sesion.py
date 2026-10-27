# Módulo testSesion.py
# Pruebas unitarias del controlador (Agente 3) para los casos de uso
# CU1 (crear sesión), CU2 (iniciar sesión) y CU3 (cerrar sesión).
# Se ejecutan contra FakeMainDAO en memoria; no requieren la base real.

import sys
from pathlib import Path

import pytest

# Permite importar los paquetes del proyecto desde la raíz del repo.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from control.controlador import Controlador
from tests.fakeMainDAO import FakeMainDAO


@pytest.fixture
def controlador():
    """Controlador con FakeMainDAO limpio e inyectado."""
    return Controlador(dao=FakeMainDAO())


# ---------------------------------------------------------------------------
# CU1: crearSesion(password, fondoInicial)
# ---------------------------------------------------------------------------

def test_cu1_creaSesionValida(controlador):
    """CU1: crea sesión con password y fondo; caja arranca igual al fondo."""
    resultado = controlador.crearSesion("clave1234", cajas=[("Caja principal", 1500.50)])

    assert resultado["ok"] is True
    assert resultado["datos"] is not None
    sesion = resultado["datos"]
    assert sesion.fondoInicial == 1500.50
    assert sesion.caja == 1500.50


def test_cu1_fallaSiYaExisteSesion(controlador):
    """CU1: no permite crear más de una sesión (sesión única en bd)."""
    controlador.crearSesion("clave1234")
    resultado = controlador.crearSesion("otraclave")

    assert resultado["ok"] is False
    assert "ya existe" in resultado["mensaje"].lower()


def test_cu1_fallaPasswordCorta(controlador):
    """CU1: rechaza contraseñas de menos de 4 caracteres."""
    for passwordCorta in ["abc", "", "   ", None]:
        resultado = controlador.crearSesion(passwordCorta)
        assert resultado["ok"] is False
        assert "4 caracteres" in resultado["mensaje"]


def test_cu1_hashPasswordCorrecto(controlador):
    """CU1: la bd guarda el hash SHA-256 y no el texto plano."""
    controlador.crearSesion("clave1234")
    sesionBd = controlador.dao.obtenerSesion()
    # (ID, Fecha_inicio, Fondo_inicial, Caja, Pass)
    passHash = sesionBd[4]
    assert passHash == Controlador.hashearPassword("clave1234")
    assert "clave1234" not in passHash


# ---------------------------------------------------------------------------
# CU2: iniciarSesion(password)
# ---------------------------------------------------------------------------

def test_cu2_iniciaSesionCorrecta(controlador):
    """CU2: con la credencial correcta desbloquea la interfaz."""
    controlador.crearSesion("clave1234")
    credenciales = {
        "clave1234": True,   # Única credencial correcta (hash coincide).
        "clave12345": False,
        "con  espacios": False,   # Tiene largo válido pero no coincide el hash.
        "   clave1234  ": False,  # No se aplica trim (comparación exacta).
        "": False,
        "abc": False,  # Menos de 4 caracteres: inválida por dominio.
    }
    for credencial, esperado in credenciales.items():
        resultado = controlador.iniciarSesion(credencial)
        assert resultado["ok"] is esperado, f"credencial: {credencial!r}"

    # La correcta desbloquea: sesión activa y autenticado a True.
    resultado = controlador.iniciarSesion("clave1234")
    assert resultado["ok"] is True
    assert controlador.estaAutenticado() is True


def test_cu2_fallaSesionNoCreada():
    """CU2: sin sesión registrada no hay nada que validar."""
    controlador = Controlador(dao=FakeMainDAO())
    resultado = controlador.iniciarSesion("clave1234")
    assert resultado["ok"] is False
    assert "no hay una sesión" in resultado["mensaje"].lower()


# ---------------------------------------------------------------------------
# CU3: cerrarSesion()
# ---------------------------------------------------------------------------

def test_cu3_cierraSesionLimpiaEstado(controlador):
    """CU3: limpia sesión activa y carrito; vuelve a pedir credenciales."""
    controlador.crearSesion("clave1234")
    controlador.iniciarSesion("clave1234")
    controlador.carrito = {1: 3, 2: 1}

    resultado = controlador.cerrarSesion()

    assert resultado["ok"] is True
    assert controlador.estaAutenticado() is False
    assert controlador.carrito == {}


def test_cu3_requiereLoginNuevo(controlador):
    """CU3: tras cerrar, la vista debe volver a login (autenticado False)."""
    controlador.crearSesion("clave1234")
    controlador.iniciarSesion("clave1234")
    controlador.cerrarSesion()
    assert controlador.estaAutenticado() is False


# ---------------------------------------------------------------------------
# Regla de arquitectura: el controlador no importa librerías de UI.
# ---------------------------------------------------------------------------

def test_controladorNoImportaUI():
    """El controlador debe funcionar sin tkinter ni customtkinter."""
    import control.controlador as modulo
    with open(modulo.__file__, encoding="utf-8") as archivo:
        codigo = archivo.read()
    assert "tkinter" not in codigo
    assert "customtkinter" not in codigo