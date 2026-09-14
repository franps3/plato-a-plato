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
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).

import logging
import sqlite3
from pathlib import Path

from control.excepciones import PersistenceError

# Configuración de logging central (plato.log).
# Se usa un FileHandler explícito para que plato.log se cree bajo cualquier
# entorno (incluido pytest, que instala sus propios handlers en el root).
log = logging.getLogger("mainDAO")
_manejador = logging.FileHandler(
    filename="plato.log",
    mode="a",
    encoding="utf-8",
    errors="replace",
)
_manejador.setLevel(logging.ERROR)
_manejador.setFormatter(
    logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
)
log.addHandler(_manejador)
log.setLevel(logging.ERROR)

# Ruta absoluta de la base de datos local (raíz del proyecto).
RUTA_BD = Path(__file__).resolve().parent.parent / "bd.db"


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
            mainDAO.conn.commit()
            return mainDAO.cursor.lastrowid
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