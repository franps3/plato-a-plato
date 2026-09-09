# Módulo fakeMainDAO.py (solo para pruebas)
# Implementa en memoria el contrato de mainDAO (Agente 1) para poder
# desarrollar y testear el controlador (Agente 3) sin necesidad de la
# base de datos SQLite real. Replica el orden exacto de la tupla:
#   (ID_sesion, Fecha_inicio, Fondo_inicial, Caja, Pass)


class FakeMainDAO:
    """Falso DAO de sesiones: simula la persistencia en memoria."""

    def __init__(self):
        # Sesión simulada: id, fechaInicio, fondoInicial, caja, passHash
        self._sesion = None
        self._proximoId = 1

    def crearSesion(self, passHash, fondoInicial, caja, fechaInicio) -> int:
        """Persiste (sobreescribe) la sesión simulada y devuelve su ID."""
        idSesion = self._proximoId
        self._proximoId += 1
        self._sesion = (idSesion, fechaInicio, fondoInicial, caja, passHash)
        return idSesion

    def obtenerSesion(self):
        """Devuelve la tupla de la sesión simulada o None si no existe."""
        return self._sesion