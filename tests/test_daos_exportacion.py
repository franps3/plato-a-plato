# Módulo test_daos_exportacion.py
# Tests de integración de los DAOs reales del Agente 1 para los casos de
# uso CU13 (exportar historial .xlsx), CU16 (exportar sesión .zip) y CU17
# (importar sesión .zip) a nivel de capa de datos.
#
# Se ejecutan contra una base SQLite temporal (no tocan bd.db real): el
# fixture redirige mainDAO.RUTA_BD con monkeypatch y resetea el singleton
# de conexión (conn/cursor), igual que en test_daos_ventas.py.

import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest
from openpyxl import load_workbook

# Permite importar los paquetes del proyecto desde la raíz del repo.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from acceso import mainDAO as mainDAO_mod
from acceso.mainDAO import mainDAO
from acceso.prodDAO import prodDAO
from acceso.ventaDAO import ventaDAO
from control.excepciones import PersistenceError


@pytest.fixture
def bdTemporal(tmp_path, monkeypatch):
    """Redirige la base a un archivo temporal y reabre la conexión compartida."""
    rutaBd = tmp_path / "bd_daos_exportacion_test.db"
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
def conMovimientos(bdTemporal, sesionId):
    """Deja una venta de 2 líneas (2300) y un gasto de -100 en la sesión.

    Caja final: 500 + 2300 - 100 = 2700.
    """
    idEmpanada = prodDAO().crearProducto("Empanada", 5, 150.0, sesionId)
    idPizza = prodDAO().crearProducto("Pizza", 3, 2000.0, sesionId)
    ventaDAO().registrarVenta(
        sesionId, "2026-09-13 11:00:00.000001",
        [(idEmpanada, 2, 150.0), (idPizza, 1, 2000.0)],
        montoNeto=2300.0, cajaNueva=2800.0,
    )
    ventaDAO().registrarGasto(
        sesionId, "Insumos", -100.0, "Carteles",
        "2026-09-13 12:00:00.000001", 2700.0,
    )
    return {"Empanada": idEmpanada, "Pizza": idPizza}
def _crearZipDesdeBd(rutaBd, rutaZip, arcname="bd.db"):
    """Empaqueta una base en un .zip con el nombre bd.db (formato CU16)."""
    with zipfile.ZipFile(str(rutaZip), "w",
                         zipfile.ZIP_DEFLATED) as archivoZip:
        archivoZip.write(str(rutaBd), arcname=arcname)


def _crearBdOrigen(rutaBd, passBd="hash-origen"):
    """Crea una base 'origen' con sesión, un producto y 1000 de caja."""
    conn = sqlite3.connect(str(rutaBd))
    conn.executescript(mainDAO._ESQUEMA)
    conn.execute(
        "INSERT INTO Sesion (Fecha_inicio, Fondo_inicial, Caja, Pass) "
        "VALUES ('2026-09-14 09:00:00', 1000, 1000, ?)",
        (passBd,),
    )
    idSesion = conn.execute(
        "SELECT ID_sesion FROM Sesion ORDER BY ID_sesion LIMIT 1"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO Producto (ID_sesion, Nombre, Stock, Precio) "
        "VALUES (?, 'Hamburguesa', 10, 500.0)",
        (idSesion,),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# CU13: exportar("historial", rutaDestino) -> .xlsx
# ---------------------------------------------------------------------------

def test_cu13_generaXlsxConVentasYGastos(bdTemporal, conMovimientos,
                                         tmp_path):
    """CU13: genera el .xlsx con hojas Ventas y Gastos pobladas."""
    ruta = mainDAO.exportar("historial", str(tmp_path))

    assert ruta.endswith(".xlsx") and Path(ruta).exists()

    libro = load_workbook(ruta)
    assert set(libro.sheetnames) == {"Ventas", "Gastos", "Cajas",
                                     "Estadísticas"}
    filasVentas = list(libro["Ventas"].iter_rows(values_only=True))
    assert filasVentas[0] == ("Fecha y hora", "Producto", "Cantidad",
                              "Precio unitario", "Subtotal")
    # 2 líneas de detalle con sus subtotales cantidad * precio.
    assert ("2026-09-13 11:00:00.000001", "Empanada", 2, 150.0,
            300.0) in filasVentas[1:]
    assert ("2026-09-13 11:00:00.000001", "Pizza", 1, 2000.0,
            2000.0) in filasVentas[1:]

    filasGastos = list(libro["Gastos"].iter_rows(values_only=True))
    assert filasGastos[0] == ("Fecha y hora", "Nombre", "Descripción",
                              "Monto")
    assert filasGastos[1] == ("2026-09-13 12:00:00.000001", "Insumos",
                              "Carteles", -100.0)

    # COR3: la hoja "Cajas" reporta valor inicial, valor actual y caja total.
    filasCajas = list(libro["Cajas"].iter_rows(values_only=True))
    assert filasCajas[0] == ("Caja", "Valor inicial", "Valor actual",
                             "Caja total")
    # Caja principal: fondo inicial 500, valor actual final 2700
    # (500 + 2300 de la venta - 100 del gasto).
    assert ("Caja principal", 500.0, 2700.0, None) in filasCajas[1:]
    assert ("Caja total", None, None, 2700.0) in filasCajas[1:]


def test_cu13_xlsxConHistorialVacioSoloHeaders(bdTemporal, sesionId,
                                               tmp_path):
    """CU13: sin movimientos el .xlsx queda solo con los encabezados."""
    ruta = mainDAO.exportar("historial", str(tmp_path / "vacio.xlsx"))

    libro = load_workbook(ruta)
    assert len(list(libro["Ventas"].iter_rows(values_only=True))) == 1
    assert len(list(libro["Gastos"].iter_rows(values_only=True))) == 1


def test_cu13_xlsxIncluyeHojaEstadisticas(bdTemporal, conMovimientos,
                                          tmp_path):
    """MJ2: el .xlsx incluye la hoja 'Estadísticas' con las 7 métricas."""
    ruta = mainDAO.exportar("historial", str(tmp_path / "stats.xlsx"))
    libro = load_workbook(str(ruta))

    assert "Estadísticas" in libro.sheetnames
    hoja = libro["Estadísticas"]
    filas = list(hoja.iter_rows(values_only=True))
    assert filas[0] == ("Indicador", "Valor")
    valores = {fila[0]: fila[1] for fila in filas[1:]}
    # Ventas 2300 (2x150 + 1x2000); sin reingresos en la sesión.
    assert valores["Total de entradas $"] == 2300.0
    # Único gasto de -100 en valor absoluto.
    assert valores["Total de salidas $"] == 100.0
    assert valores["Cantidad de productos vendidos"] == 3
    assert valores["Cantidad de combos vendidos"] == 0
    assert valores["Cantidad de gastos/reingresos registrados"] == 1
    # Producto más vendido: Empanada (2) vs Pizza (1).
    assert valores["Producto más vendido"] == "Empanada (2)"
    assert valores["Combo más vendido"] == "Sin registros"


def test_cu13_agregaExtensionYRespetaRutaCompleta(bdTemporal,
                                                  conMovimientos, tmp_path):
    """CU13: agrega .xlsx si falta y respeta la ruta completa si la trae."""
    ruta1 = mainDAO.exportar("historial", str(tmp_path / "historial"))
    assert ruta1.endswith(".xlsx") and Path(ruta1).exists()

    ruta2 = mainDAO.exportar("historial", str(tmp_path / "custom.xlsx"))
    assert ruta2 == str(tmp_path / "custom.xlsx")


def test_cu13_sinSesionElevaPersistenceError(bdTemporal, tmp_path):
    """CU13: sin sesión la exportación falla con PersistenceError."""
    with pytest.raises(PersistenceError, match="sesión"):
        mainDAO.exportar("historial", str(tmp_path))


def test_cu13_tipoInvalidoElevaValueError(bdTemporal, sesionId, tmp_path):
    """CU13: un tipo no soportado es un error de contrato (ValueError)."""
    with pytest.raises(ValueError):
        mainDAO.exportar("pdf", str(tmp_path))


def test_cu13_rutaInvalidaElevaPersistenceError(bdTemporal, sesionId,
                                                tmp_path):
    """CU13: una carpeta de destino inexistente eleva PersistenceError."""
    rutaMala = tmp_path / "no_existe" / "historial.xlsx"
    with pytest.raises(PersistenceError):
        mainDAO.exportar("historial", str(rutaMala))


# ---------------------------------------------------------------------------
# CU16: exportar("sesion", rutaDestino) -> .zip
# ---------------------------------------------------------------------------

def test_cu16_generaZipConLaBdDentro(bdTemporal, sesionId, tmp_path):
    """CU16: empaqueta bd.db tal cual está en disco dentro del .zip."""
    ruta = mainDAO.exportar("sesion", str(tmp_path / "respaldo.zip"))

    assert ruta.endswith(".zip") and Path(ruta).exists()
    with zipfile.ZipFile(ruta) as archivoZip:
        assert archivoZip.namelist() == ["bd.db"]
        assert archivoZip.read("bd.db") == bdTemporal.read_bytes()


def test_cu16_nombrePorDefectoEnCarpeta(bdTemporal, sesionId, tmp_path):
    """CU16: si el destino es una carpeta se genera nombre con marca de tiempo."""
    ruta = mainDAO.exportar("sesion", str(tmp_path))

    nombre = Path(ruta).name
    assert nombre.startswith("sesion_") and nombre.endswith(".zip")
    assert Path(ruta).exists()


def test_cu16_sinSesionElevaPersistenceError(bdTemporal, tmp_path):
    """CU16: sin sesión la exportación falla con PersistenceError."""
    with pytest.raises(PersistenceError, match="sesión"):
        mainDAO.exportar("sesion", str(tmp_path))


def test_cu16_rutaInvalidaElevaPersistenceError(bdTemporal, sesionId,
                                                tmp_path):
    """CU16: una carpeta de destino inexistente eleva PersistenceError."""
    rutaMala = tmp_path / "carpeta_inexistente" / "x.zip"
    with pytest.raises(PersistenceError):
        mainDAO.exportar("sesion", str(rutaMala))
# ---------------------------------------------------------------------------
# CU17: importar(rutaZip, passNueva)
# ---------------------------------------------------------------------------

def test_cu17_importaSobrescribeBdYAplicaClaveNueva(bdTemporal,
                                                    conMovimientos, tmp_path):
    """CU17: sobrescribe la BD local con la del .zip y asigna la clave nueva."""
    rutaBdOrigen = tmp_path / "bd_origen.db"
    _crearBdOrigen(rutaBdOrigen)
    zipFuente = tmp_path / "fuente.zip"
    _crearZipDesdeBd(rutaBdOrigen, zipFuente)

    sesion = mainDAO.importar(str(zipFuente), "hash-nueva-clave")

    assert sesion is not None
    assert sesion[1] == "2026-09-14 09:00:00"
    assert sesion[2] == 1000.0
    assert sesion[3] == 1000.0
    # La "clave" asignada en el CU17 quedó como nueva Pass.
    assert sesion[4] == "hash-nueva-clave"
    # La BD importada sobrescribió la anterior: solo existe el producto
    # de la sesión importada.
    assert len(prodDAO().verProductos(sesion[0])) == 1
    assert prodDAO().verProductos(sesion[0]) == [(1, "Hamburguesa", 500.0)]


def test_cu17_importaConservaPassDelArchivoSiNoSeAsigna(bdTemporal,
                                                        conMovimientos,
                                                        tmp_path):
    """CU17: sin passNueva se conserva la Pass que traía el .zip."""
    rutaBdOrigen = tmp_path / "bd_origen.db"
    _crearBdOrigen(rutaBdOrigen, passBd="hash-viejo")
    zipFuente = tmp_path / "fuente.zip"
    _crearZipDesdeBd(rutaBdOrigen, zipFuente)

    sesion = mainDAO.importar(str(zipFuente))

    assert sesion[4] == "hash-viejo"


def test_cu17_generaRespaldoAntesDeSobrescribir(bdTemporal, conMovimientos,
                                                tmp_path):
    """CU17: genera bd_respaldo.db con la sesión anterior antes de sobrescribir."""
    rutaBdOrigen = tmp_path / "bd_origen.db"
    _crearBdOrigen(rutaBdOrigen)
    zipFuente = tmp_path / "fuente.zip"
    _crearZipDesdeBd(rutaBdOrigen, zipFuente)

    mainDAO.importar(str(zipFuente), "hash-nueva")

    respaldo = bdTemporal.parent / "bd_respaldo.db"
    assert respaldo.exists()
    # El respaldo conserva la sesión anterior (caja 2700 de los movimientos).
    conn = sqlite3.connect(str(respaldo))
    caja = conn.execute("SELECT Caja FROM Sesion LIMIT 1").fetchone()[0]
    conn.close()
    assert caja == 2700.0


def test_cu16_cu17_redondoExportaZipYReimporta(bdTemporal, sesionId,
                                               conMovimientos, tmp_path):
    """CU16 -> CU17: el zip exportado se reimporta y restaura la sesión."""
    rutaZip = mainDAO.exportar("sesion", str(tmp_path / "respaldo.zip"))

    # La BD cambia (otra sesión), luego se reimporta la exportada.
    mainDAO.nuke()
    mainDAO.crearSesion(
        "hash-otra", "2026-09-15 08:00:00",
        cajas=[("Caja principal", 99.0)],
    )

    sesion = mainDAO.importar(rutaZip, "hash-reimportada")

    assert sesion[1] == "2026-09-13 10:00:00"
    assert sesion[2] == 500.0
    assert sesion[3] == 2700.0
    assert sesion[4] == "hash-reimportada"
    # Ventas y gastos restaurados desde el zip.
    assert len(ventaDAO().verVentas(sesion[0])) == 1
    assert len(ventaDAO().verGastos(sesion[0])) == 1
def test_cu17_zipSinBdDbElevaPersistenceError(bdTemporal, conMovimientos,
                                              tmp_path):
    """CU17: un .zip sin bd.db es rechazado con PersistenceError."""
    zipFuente = tmp_path / "sin_bd.zip"
    with zipfile.ZipFile(zipFuente, "w") as archivoZip:
        archivoZip.writestr("otro.txt", "x")

    with pytest.raises(PersistenceError, match="bd.db"):
        mainDAO.importar(str(zipFuente))


def test_cu17_archivoNoEsZipElevaPersistenceError(bdTemporal,
                                                  conMovimientos, tmp_path):
    """CU17: un archivo que no es .zip válido eleva PersistenceError."""
    zipFuente = tmp_path / "no_es_zip.zip"
    zipFuente.write_text("esto no es un zip válido")

    with pytest.raises(PersistenceError):
        mainDAO.importar(str(zipFuente))


def test_cu17_archivoInexistenteElevaPersistenceError(bdTemporal,
                                                      conMovimientos,
                                                      tmp_path):
    """CU17: una ruta inexistente eleva PersistenceError."""
    with pytest.raises(PersistenceError, match="no existe"):
        mainDAO.importar(str(tmp_path / "nada.zip"))


def test_cu17_esquemaInvalidoElevaPersistenceError(bdTemporal,
                                                   conMovimientos, tmp_path):
    """CU17: una base sin el esquema del MER es rechazada y no toca la activa."""
    rutaBdMala = tmp_path / "bd_mala.db"
    conn = sqlite3.connect(str(rutaBdMala))
    conn.execute("CREATE TABLE Otra (id INTEGER)")
    conn.execute("INSERT INTO Otra (id) VALUES (1)")
    conn.commit()
    conn.close()
    zipFuente = tmp_path / "mala.zip"
    _crearZipDesdeBd(rutaBdMala, zipFuente)

    with pytest.raises(PersistenceError, match="esquema"):
        mainDAO.importar(str(zipFuente))
    # La base activa queda intacta (la sesión original sigue operativa).
    assert mainDAO.obtenerSesion()[2] == 500.0


def test_cu17_sinSesionEnElZipElevaPersistenceError(bdTemporal,
                                                    conMovimientos, tmp_path):
    """CU17: esquema completo pero sin fila en Sesion es rechazado."""
    rutaBdVacia = tmp_path / "bd_vacia.db"
    conn = sqlite3.connect(str(rutaBdVacia))
    conn.executescript(mainDAO._ESQUEMA)
    conn.commit()
    conn.close()
    zipFuente = tmp_path / "vacia.zip"
    _crearZipDesdeBd(rutaBdVacia, zipFuente)

    with pytest.raises(PersistenceError, match="sesión"):
        mainDAO.importar(str(zipFuente))


def test_cu17_contenidoNoEsSqliteElevaPersistenceError(bdTemporal,
                                                       conMovimientos,
                                                       tmp_path):
    """CU17: un bd.db con contenido no SQLite eleva PersistenceError."""
    zipFuente = tmp_path / "garbage.zip"
    with zipfile.ZipFile(zipFuente, "w") as archivoZip:
        archivoZip.writestr("bd.db", "esto no es una base sqlite")

    with pytest.raises(PersistenceError):
        mainDAO.importar(str(zipFuente))