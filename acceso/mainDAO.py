# Módulo mainDAO.py (Agente 1 - Modelo)
# Responsable único del archivo .db, el esquema y las consultas SQL.
# mainDAO gestiona la conexión compartida (conn/cursor) que usan los
# demás DAOs (prodDAO, stockDAO, ventaDAO) y el manejo de sesión
# (CU1/CU2/CU3).
#
# Contrato acordado (definido por el Agente 3):
#   * crearSesion(passHash, fondoInicial, caja, fechaInicio) -> int
#       Persiste la sesión única y devuelve su ID_sesion.
#   * obtenerSesion() -> tuple | None
#       Devuelve (ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass)
#       de la sesión registrada, o None si no existe.
#   * exportar(tipo, rutaDestino) -> str
#       tipo "historial" (CU13) genera un .xlsx con las hojas Ventas,
#       Gastos y Cajas (COR3: valor inicial/actual por caja y caja total);
#       tipo "sesion" (CU16) empaqueta bd.db en un .zip.
#       Devuelve la ruta del archivo generado.
#   * importar(rutaZip, passNueva) -> tuple | None
#       Sobrescribe la BD local con la del .zip (CU17). passNueva debe
#       llegar HASHEADA por el Agente 3 y se guarda como nueva Pass de
#       la sesión importada (la "clave" que se asigna al importar).
#       Devuelve la tupla (ID_sesion, Fecha_inicio, Fondo_inicial,
#       Caja, Pass) de la sesión importada.
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import logging
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from control.excepciones import PersistenceError

# Carpeta base de los datos de la aplicación (bd.db, plato.log y
# bd_respaldo.db): junto al ejecutable cuando la app está congelada con
# PyInstaller (ejecutable portable: los datos viajan con el .exe) y en la
# raíz del proyecto cuando se ejecuta desde el código fuente.
if getattr(sys, "frozen", False):
    CARPETA_BASE = Path(sys.executable).resolve().parent
else:
    CARPETA_BASE = Path(__file__).resolve().parent.parent

# Configuración de logging central (plato.log, dentro de CARPETA_BASE).
# Se usa un FileHandler explícito para que plato.log se cree bajo cualquier
# entorno (incluido pytest, que instala sus propios handlers en el root).
# delay=True: el archivo se abre recién ante el primer ERROR, así una
# carpeta sin permiso de escritura no impide que la app arranque.
log = logging.getLogger("mainDAO")
_manejador = logging.FileHandler(
    filename=str(CARPETA_BASE / "plato.log"),
    mode="a",
    encoding="utf-8",
    errors="replace",
    delay=True,
)
_manejador.setLevel(logging.ERROR)
_manejador.setFormatter(
    logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
)
log.addHandler(_manejador)
log.setLevel(logging.ERROR)

# Ruta absoluta de la base de datos local (dentro de CARPETA_BASE).
RUTA_BD = CARPETA_BASE / "bd.db"


class mainDAO:
    """Acceso a datos de sesión y conexión compartida (Agente 1).

    La conexión y el cursor son atributos de clase: los comparten
    prodDAO, stockDAO y ventaDAO para operar sobre la misma base.
    """

    # Conexión y cursor compartidos por todos los DAOs.
    conn = None
    cursor = None

    # Esquema completo de la base (MER de docs/spec.md). Se crea de forma
    # idempotente (IF NOT EXISTS) al primer arranque (CU1).
    _ESQUEMA = """
    CREATE TABLE IF NOT EXISTS Sesion (
        ID_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
        Fecha_inicio TEXT NOT NULL,
        Fondo_inicial REAL NOT NULL,
        Caja REAL NOT NULL,
        Pass TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Producto (
        ID_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_sesion INTEGER NOT NULL,
        Nombre TEXT NOT NULL,
        Stock INTEGER NOT NULL,
        Precio REAL NOT NULL,
        FOREIGN KEY (ID_sesion) REFERENCES Sesion(ID_sesion) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS Venta (
        ID_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_sesion INTEGER NOT NULL,
        Fecha_hora TEXT NOT NULL,
        FOREIGN KEY (ID_sesion) REFERENCES Sesion(ID_sesion) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS DetalleVenta (
        ID_venta INTEGER NOT NULL,
        ID_Producto INTEGER NOT NULL,
        Cantidad INTEGER NOT NULL,
        Precio_unitario REAL NOT NULL,
        PRIMARY KEY (ID_venta, ID_Producto),
        FOREIGN KEY (ID_venta) REFERENCES Venta(ID_venta) ON DELETE CASCADE,
        FOREIGN KEY (ID_Producto) REFERENCES Producto(ID_producto) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS GastoSecundario (
        ID_gasto INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_sesion INTEGER NOT NULL,
        Nombre TEXT NOT NULL,
        Monto REAL NOT NULL,
        Descripcion TEXT,
        Fecha_hora TEXT NOT NULL,
        FOREIGN KEY (ID_sesion) REFERENCES Sesion(ID_sesion) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS Caja (
        ID_caja INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_sesion INTEGER NOT NULL,
        Nombre TEXT NOT NULL,
        Fondo_inicial REAL NOT NULL,
        Monto REAL NOT NULL,
        FOREIGN KEY (ID_sesion) REFERENCES Sesion(ID_sesion) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_producto_sesion ON Producto(ID_sesion);
    CREATE INDEX IF NOT EXISTS idx_venta_sesion ON Venta(ID_sesion);
    CREATE INDEX IF NOT EXISTS idx_detalle_venta ON DetalleVenta(ID_venta);
    CREATE INDEX IF NOT EXISTS idx_detalle_producto ON DetalleVenta(ID_Producto);
    CREATE INDEX IF NOT EXISTS idx_gasto_sesion ON GastoSecundario(ID_sesion);
    """

    @staticmethod
    def conectar():
        """Abre/crea bd.db, activa FKs y crea el esquema si no existe.

        Si la conexión ya está abierta, la reutiliza (patrón singleton a
        nivel de clase). Es la conexión compartida por todos los DAOs.
        """
        if mainDAO.conn is not None:
            return mainDAO.conn
        try:
            mainDAO.conn = sqlite3.connect(str(RUTA_BD))
            mainDAO.cursor = mainDAO.conn.cursor()
            # Garantiza la integridad referencial entre tablas.
            mainDAO.cursor.execute("PRAGMA foreign_keys = ON")
            # Crea el esquema completo de forma idempotente.
            mainDAO.cursor.executescript(mainDAO._ESQUEMA)
            # COR3 / migración MJ1: toda sesión preexistente (creada antes
            # de la tabla Caja) se siembra con su "Caja principal", usando
            # su fondo inicial y caja actual. Idempotente (NOT EXISTS).
            mainDAO.cursor.execute(
                "INSERT INTO Caja (ID_sesion, Nombre, Fondo_inicial, Monto) "
                "SELECT ID_sesion, 'Caja principal', Fondo_inicial, Caja "
                "FROM Sesion WHERE NOT EXISTS ("
                "    SELECT 1 FROM Caja c WHERE c.ID_sesion = Sesion.ID_sesion"
                ")"
            )
            mainDAO.conn.commit()
            return mainDAO.conn
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def _manejarError(err):
        """Captura sqlite3.Error, ejecuta ROLLBACK y eleva PersistenceError.

        Regla clave del Agente 1: ninguna excepción nativa de sqlite3
        escapa de la capa DAO; siempre se encapsula en PersistenceError.
        """
        if mainDAO.conn is not None:
            try:
                mainDAO.conn.rollback()
            except sqlite3.Error:
                pass
        log.error("%s: %s", type(err).__name__, err, exc_info=True)
        raise PersistenceError(f"Error de persistencia: {err}") from err

    @staticmethod
    def crearSesion(passHash: str, fondoInicial: float, caja: float,
                    fechaInicio: str) -> int:
        """Persiste la sesión única y devuelve su ID_sesion (CU1).

        La sesión es única en la base: el controlador valida antes de
        llamar que no exista una sesión registrada (SesionYaExiste).
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "INSERT INTO Sesion (Fecha_inicio, Fondo_inicial, Caja, Pass) "
                "VALUES (?, ?, ?, ?)",
                (fechaInicio, fondoInicial, caja, passHash),
            )
            idSesion = mainDAO.cursor.lastrowid
            # COR3 / preparación MJ1 (N cajas): toda sesión nueva arranca con
            # su "Caja principal" (fondo inicial = monto actual = fondoInicial).
            mainDAO.cursor.execute(
                "INSERT INTO Caja (ID_sesion, Nombre, Fondo_inicial, Monto) "
                "VALUES (?, ?, ?, ?)",
                (idSesion, "Caja principal", fondoInicial, caja),
            )
            mainDAO.conn.commit()
            return idSesion
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def obtenerSesion():
        """Devuelve la sesión registrada o None si no existe (CU2).

        Tupla cruda: (ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass).
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass "
                "FROM Sesion ORDER BY ID_sesion LIMIT 1"
            )
            fila = mainDAO.cursor.fetchone()
            return tuple(fila) if fila is not None else None
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def verCajas(idSesion: int):
        """Devuelve las cajas (medios de pago) de la sesión (COR3 / MJ1).

        Formato de cada tupla: (ID_caja, Nombre, Fondo_inicial, Monto).
        El valor inicial de cada caja es su Fondo_inicial; el valor
        actual es su Monto; la caja total se calcula como la suma de
        los Monto (query resumen en _exportarHistorial).
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute(
                "SELECT ID_caja, Nombre, Fondo_inicial, Monto "
                "FROM Caja WHERE ID_sesion = ? "
                "ORDER BY ID_caja",
                (idSesion,),
            )
            return [tuple(fila) for fila in mainDAO.cursor.fetchall()]
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

    @staticmethod
    def nuke():
        """Borra la sesión y toda la base de datos local (CU15 reiniciar).

        Elimina todos los datos (sesión, productos, ventas, detalles y
        gastos) restaurando la aplicación a cero. El archivo bd.db y el
        esquema se conservan para la próxima creación de sesión.
        """
        mainDAO.conectar()
        try:
            mainDAO.cursor.execute("DELETE FROM DetalleVenta")
            mainDAO.cursor.execute("DELETE FROM Venta")
            mainDAO.cursor.execute("DELETE FROM GastoSecundario")
            mainDAO.cursor.execute("DELETE FROM Producto")
            mainDAO.cursor.execute("DELETE FROM Sesion")
            mainDAO.conn.commit()
        except sqlite3.Error as err:
            mainDAO._manejarError(err)
# ------------------------------------------------------------------
    # CU13/CU16: exportar(tipo, rutaDestino)
    # Método único parametrizado (decisión acordada, fiel a docs/spec.md):
    # el tipo decide el formato, "historial" -> .xlsx (CU13) y
    # "sesion" -> .zip (CU16).
    # ------------------------------------------------------------------
    @staticmethod
    def exportar(tipo: str, rutaDestino: str) -> str:
        """Exporta el historial (.xlsx) o la sesión (.zip) según el tipo.

        Parámetros:
            tipo: "historial" (CU13) o "sesion" (CU16).
            rutaDestino: Ruta del archivo a generar. Si apunta a una
                carpeta existente (o no trae la extensión esperada) se
                completa con un nombre y extensión por defecto.

        Retorno: ruta del archivo generado. Ante fallos eleva
        PersistenceError (regla clave de Agente 1).
        """
        mainDAO.conectar()
        if mainDAO.obtenerSesion() is None:
            raise PersistenceError(
                "No hay una sesión registrada para exportar."
            )
        if tipo == "historial":
            return mainDAO._exportarHistorial(rutaDestino)
        if tipo == "sesion":
            return mainDAO._exportarSesion(rutaDestino)
        raise ValueError(f"Tipo de exportación no soportado: {tipo!r}")

    @staticmethod
    def _exportarHistorial(rutaDestino: str) -> str:
        """Genera el .xlsx del historial de la sesión activa (CU13).

        Hoja "Ventas": una fila por línea de detalle (fecha y hora,
        producto, cantidad, precio unitario y subtotal). Hoja "Gastos":
        una fila por gasto/reinserción (fecha y hora, nombre,
        descripción y monto). Hoja "Cajas" (COR3): por cada caja su
        valor inicial (Fondo_inicial), valor actual (Monto) y la caja
        total (suma de Montos). Espejo del historial de la UI (spec.md).
        """
        idSesion = mainDAO.obtenerSesion()[0]
        try:
            mainDAO.cursor.execute(
                "SELECT v.Fecha_hora, p.Nombre, d.Cantidad, "
                "d.Precio_unitario "
                "FROM Venta v "
                "JOIN DetalleVenta d ON d.ID_venta = v.ID_venta "
                "JOIN Producto p ON p.ID_producto = d.ID_Producto "
                "WHERE v.ID_sesion = ? "
                "ORDER BY v.Fecha_hora, v.ID_venta, d.ID_Producto",
                (idSesion,),
            )
            lineasVenta = mainDAO.cursor.fetchall()
            mainDAO.cursor.execute(
                "SELECT ID_gasto, Nombre, Monto, Descripcion, Fecha_hora "
                "FROM GastoSecundario WHERE ID_sesion = ? "
                "ORDER BY Fecha_hora, ID_gasto",
                (idSesion,),
            )
            gastos = mainDAO.cursor.fetchall()
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

        libro = Workbook()
        hojaVentas = libro.active
        hojaVentas.title = "Ventas"
        hojaVentas.append(
            ["Fecha y hora", "Producto", "Cantidad",
             "Precio unitario", "Subtotal"]
        )
        for fechaHora, nombre, cantidad, precio in lineasVenta:
            hojaVentas.append([
                fechaHora, nombre, cantidad, precio,
                round(cantidad * precio, 2),
            ])

        hojaGastos = libro.create_sheet("Gastos")
        hojaGastos.append(
            ["Fecha y hora", "Nombre", "Descripción", "Monto"]
        )
        for idGasto, nombre, monto, descripcion, fechaHora in gastos:
            hojaGastos.append([fechaHora, nombre, descripcion, monto])

        # COR3: incluir valor inicial de cada caja, valor actual y caja total.
        # Por cada caja se reporta su Fondo_inicial (valor inicial) y su Monto
        # (valor actual). La última fila es el total de caja (suma de Montos).
        hojaCajas = libro.create_sheet("Cajas")
        hojaCajas.append(["Caja", "Valor inicial", "Valor actual", "Caja total"])
        cajas = mainDAO.verCajas(idSesion)
        for _idCaja, nombreCaja, fondoInicial, montoActual in cajas:
            hojaCajas.append([
                nombreCaja,
                round(fondoInicial, 2),
                round(montoActual, 2),
                None,
            ])
        cajaTotal = round(sum(montoActual
                              for _idCaja, _nombreCaja, _fondoInicial,
                              montoActual in cajas), 2)
        if cajas:
            hojaCajas.append(["Caja total", None, None, cajaTotal])

        ruta = mainDAO._resolverRutaSalida(
            rutaDestino, ".xlsx", "historial"
        )
        try:
            libro.save(str(ruta))
        except OSError as err:
            mainDAO._manejarErrorArchivo(err)
        return str(ruta)

    @staticmethod
    def _exportarSesion(rutaDestino: str) -> str:
        """Empaqueta la base de datos local en un .zip (CU16).

        El .zip contiene la base actual con el nombre bd.db para que
        importar() (CU17) la localice. El archivo NO se cifra (decisión
        acordada: la "clave" del CU17 es la nueva Pass de la sesión).
        """
        mainDAO.conectar()
        try:
            # Asegura que el archivo en disco esté al día (sin transac-
            # ciones pendientes) antes de empaquetarlo.
            mainDAO.conn.commit()
        except sqlite3.Error as err:
            mainDAO._manejarError(err)

        ruta = mainDAO._resolverRutaSalida(rutaDestino, ".zip", "sesion")
        try:
            with zipfile.ZipFile(str(ruta), "w",
                                 zipfile.ZIP_DEFLATED) as archivoZip:
                archivoZip.write(str(RUTA_BD), arcname="bd.db")
        except OSError as err:
            mainDAO._manejarErrorArchivo(err)
        return str(ruta)

    @staticmethod
    def _resolverRutaSalida(rutaDestino: str, extension: str,
                            prefijo: str) -> Path:
        """Completa la ruta de salida si apunta a carpeta o falta extensión.

        Si rutaDestino es una carpeta existente se genera un nombre con
        marca de tiempo; si es un archivo sin la extensión esperada se
        agrega la extensión. Devuelve la ruta final (Path).
        """
        ruta = Path(rutaDestino)
        if ruta.is_dir():
            marca = datetime.now().strftime("%Y%m%d_%H%M%S")
            return ruta / f"{prefijo}_{marca}{extension}"
        if ruta.suffix.lower() != extension:
            return ruta.with_suffix(extension)
        return ruta

    @staticmethod
    def _manejarErrorArchivo(err):
        """Encapsula fallos de archivos/exportación como PersistenceError.

        Los errores de archivo no dejan transacciones SQL abiertas, por lo
        que no hace falta ROLLBACK; sí se conserva la regla de que ninguna
        falla de la capa de datos escapa sin encapsularse en
        PersistenceError (con logging a plato.log).
        """
        log.error("%s: %s", type(err).__name__, err, exc_info=True)
        raise PersistenceError(f"Error de persistencia: {err}") from err
# ------------------------------------------------------------------
    # CU17: importar(rutaZip, passNueva)
    # Carga y sobrescribe la sesión desde un .zip. La "clave" que asigna
    # el usuario se guarda como nueva Pass de la sesión importada
    # (decisión acordada: el .zip NO va cifrado).
    # ------------------------------------------------------------------
    @staticmethod
    def importar(rutaZip: str, passNueva: str = None) -> tuple:
        """Importa y sobrescribe la base local desde un .zip (CU17).

        El .zip debe contener un bd.db con el esquema del MER
        (docs/spec.md) y al menos una sesión; si no, eleva
        PersistenceError y la base activa queda intacta. Antes de
        sobrescribir se respalda la base actual en bd_respaldo.db.

        Parámetros:
            rutaZip: Ruta del archivo .zip exportado (CU16).
            passNueva: Nueva Pass de la sesión importada (la "clave"
                del CU17). Debe llegar HASHEADA por el Agente 3 (misma
                convención que crearSesion). Si es None, se conserva la
                Pass que traía el archivo.

        Retorno: tupla (ID_sesion, Fecha_inicio, Fondo_inicial, Caja,
        Pass) de la sesión importada, ya con la clave aplicada.
        """
        ruta = Path(rutaZip)
        if not ruta.exists():
            raise PersistenceError("El archivo de sesión no existe.")

        # 1) Valida el .zip y extrae bd.db en memoria.
        try:
            with zipfile.ZipFile(str(ruta), "r") as archivoZip:
                contenido = archivoZip.read("bd.db")
        except KeyError:
            raise PersistenceError(
                "El archivo de sesión no contiene una base de datos (bd.db)."
            )
        except (zipfile.BadZipFile, OSError) as err:
            mainDAO._manejarErrorArchivo(err)

        # 2) Vuelca el contenido a un archivo temporal y valida esquema +
        #    sesión sin tocar la base activa.
        try:
            with tempfile.NamedTemporaryFile(suffix=".db",
                                             delete=False) as archivoTmp:
                archivoTmp.write(contenido)
                rutaTmp = Path(archivoTmp.name)
        except OSError as err:
            mainDAO._manejarErrorArchivo(err)
        try:
            conexionTmp = sqlite3.connect(str(rutaTmp))
            try:
                tablas = {
                    fila[0]
                    for fila in conexionTmp.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'table'"
                    )
                }
                tablasEsperadas = {
                    "Sesion", "Producto", "Venta",
                    "DetalleVenta", "GastoSecundario",
                }
                if not tablasEsperadas.issubset(tablas):
                    raise PersistenceError(
                        "La base del archivo no tiene el esquema esperado."
                    )
                fila = conexionTmp.execute(
                    "SELECT ID_sesion, Fecha_inicio, Fondo_inicial, "
                    "Caja, Pass FROM Sesion ORDER BY ID_sesion LIMIT 1"
                ).fetchone()
                if fila is None:
                    raise PersistenceError(
                        "El archivo no contiene una sesión."
                    )
                idSesionImportado = fila[0]
            finally:
                conexionTmp.close()

            # 3) Respaldo de la base actual antes de sobrescribir.
            if RUTA_BD.exists():
                try:
                    shutil.copy2(
                        str(RUTA_BD),
                        str(RUTA_BD.parent / "bd_respaldo.db"),
                    )
                except OSError as err:
                    mainDAO._manejarErrorArchivo(err)

            # 4) Cierra la conexión compartida para poder reemplazar el
            #    archivo en disco.
            if mainDAO.conn is not None:
                mainDAO.conn.close()
            mainDAO.conn = None
            mainDAO.cursor = None

            # 5) Sobrescribe bd.db; ante un fallo se intenta restaurar el
            #    respaldo para no dejar la app sin base.
            try:
                shutil.copy2(str(rutaTmp), str(RUTA_BD))
            except OSError as err:
                rutaRespaldo = RUTA_BD.parent / "bd_respaldo.db"
                try:
                    if rutaRespaldo.exists():
                        shutil.copy2(str(rutaRespaldo), str(RUTA_BD))
                except OSError:
                    pass
                mainDAO._manejarErrorArchivo(err)

            # 6) Reabre la conexión compartida sobre la base importada.
            mainDAO.conectar()

            # 7) Asigna la nueva clave de sesión (CU17: "asigna clave").
            if passNueva:
                mainDAO.cursor.execute(
                    "UPDATE Sesion SET Pass = ? WHERE ID_sesion = ?",
                    (passNueva, idSesionImportado),
                )
                mainDAO.conn.commit()
        except sqlite3.Error as err:
            mainDAO._manejarError(err)
        finally:
            rutaTmp.unlink(missing_ok=True)

        sesionImportada = mainDAO.obtenerSesion()
        return tuple(sesionImportada) if sesionImportada is not None else None