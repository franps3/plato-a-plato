# Módulo test_daos_credenciales.py
# Tests de integración de los DAOs reales del Agente 1 para la mejora MJ3
# (recuperación de credenciales mediante pregunta de seguridad): la tabla
# Sesion guarda Pregunta_seguridad y Respuesta_seguridad, crearSesion las
# persiste, obtenerSesion las incluye en su tupla y actualizarPass permite
# restablecer la contraseña tras superar la pregunta.
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


@pytest.fixture
def bdTemporal(tmp_path, monkeypatch):
    """Redirige la base a un archivo temporal y reabre la conexión compartida."""
    rutaBd = tmp_path / "bd_daos_credenciales_test.db"
    monkeypatch.setattr(mainDAO_mod, "RUTA_BD", rutaBd)
    mainDAO.conn = None
    mainDAO.cursor = None
    mainDAO.conectar()
    yield rutaBd
    # Restaura el singleton para no contaminar otros tests de la suite.
    mainDAO.conn = None
    mainDAO.cursor = None


@pytest.fixture
def sesionConPregunta(bdTemporal):
    """Crea la sesión con pregunta y respuesta de seguridad (MJ3)."""
    return mainDAO.crearSesion(
        "hash-pass", "2026-10-29 10:00:00",
        cajas=[("Caja principal", 500.0)],
        preguntaSeguridad="¿Cuál es tu comida favorita?",
        respuestaHash="hash-respuesta",
    )


def test_mj3_crearSesionGuardaPreguntaYRespuesta(sesionConPregunta):
    """MJ3: la sesión se crea con pregunta y respuesta de seguridad."""
    sesion = mainDAO.obtenerSesion()
    assert sesion[5] == "¿Cuál es tu comida favorita?"
    assert sesion[6] == "hash-respuesta"


def test_mj3_obtenerSesionAmpliadaMantieneTuplaCompatible(sesionConPregunta):
    """MJ3: los 5 primeros elementos conservan el contrato previo."""
    sesion = mainDAO.obtenerSesion()
    assert sesion[:5] == (
        sesionConPregunta, "2026-10-29 10:00:00", 500.0, 500.0, "hash-pass"
    )


def test_mj3_obtenerPreguntaSeguridad(sesionConPregunta):
    """MJ3: obtenerPreguntaSeguridad devuelve (ID, Pregunta, Respuesta)."""
    idSesion, pregunta, respuesta = mainDAO.obtenerPreguntaSeguridad()
    assert idSesion == sesionConPregunta
    assert pregunta == "¿Cuál es tu comida favorita?"
    assert respuesta == "hash-respuesta"


def test_mj3_obtenerPreguntaSeguridadSinSesionDevuelveNone(bdTemporal):
    """MJ3: sin sesión registrada no hay pregunta de seguridad (None)."""
    assert mainDAO.obtenerPreguntaSeguridad() is None


def test_mj3_actualizarPassRestableceContraseña(sesionConPregunta):
    """MJ3: actualizarPass reemplaza la Pass conservando la pregunta."""
    assert mainDAO.actualizarPass("hash-nueva-pass") is True

    sesion = mainDAO.obtenerSesion()
    assert sesion[4] == "hash-nueva-pass"
    assert sesion[5] == "¿Cuál es tu comida favorita?"
    assert sesion[6] == "hash-respuesta"


def test_mj3_actualizarPassSinSesionDevuelveFalse(bdTemporal):
    """MJ3: sin sesión no hay contraseña que actualizar (False)."""
    assert mainDAO.actualizarPass("hash-nueva") is False