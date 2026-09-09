# Módulo mainDAO.py (contrato de interfaz - a implementar por Agente 1)
# Agente 1 es el responsable único del archivo .db, el esquema y las
# consultas SQL. Este módulo define el contrato que el controlador
# (Agente 3) espera de mainDAO para el manejo de sesiones (CU1/CU2/CU3).
#
# Contrato acordado:
#   * crearSesion(passHash, fondoInicial, caja, fechaInicio) -> int
#       Persiste la sesión única y devuelve su ID_sesion.
#   * obtenerSesion() -> tuple | None
#       Devuelve (ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass)
#       de la sesión registrada, o None si no existe.
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).


class mainDAO:
    """Contrato de acceso a datos de sesión (implementado por Agente 1)."""

    @staticmethod
    def crearSesion(passHash: str, fondoInicial: float, caja: float, fechaInicio: str) -> int:
        """Persiste la sesión única y devuelve su ID_sesion."""
        raise NotImplementedError(
            "mainDAO.crearSesion: implementación pendiente del Agente 1."
        )

    @staticmethod
    def obtenerSesion():
        """Devuelve (ID, Fecha_inicio, Fondo_inicial, Caja, Pass) o None."""
        raise NotImplementedError(
            "mainDAO.obtenerSesion: implementación pendiente del Agente 1."
        )