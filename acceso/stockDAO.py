# Módulo stockDAO.py (contrato de interfaz - a implementar por Agente 1)
# Agente 1 es el responsable único del archivo .db, el esquema y las
# consultas SQL. Este módulo define el contrato que el controlador
# (Agente 3) espera de stockDAO para el manejo de existencias (CU5/CU7).
#
# Contrato acordado:
#   * verStock(idProducto) -> int | None
#       Devuelve el stock actual del producto o None si no existe.
#   * editarStock(idProducto, stock) -> int | None
#       Actualiza el stock y devuelve el nuevo valor, o None si no existe.
#
# Regla clave de Agente 1: capturar sqlite3.Error, ejecutar ROLLBACK y
# re-elevar como subclase de PersistenceError (control.excepciones).


class stockDAO:
    """Contrato de acceso a datos de stock (implementado por Agente 1)."""

    @staticmethod
    def verStock(idProducto: int):
        """Devuelve el stock del producto o None si no existe."""
        raise NotImplementedError(
            "stockDAO.verStock: implementación pendiente del Agente 1."
        )

    @staticmethod
    def editarStock(idProducto: int, stock: int):
        """Actualiza el stock y devuelve el nuevo valor, o None si no existe."""
        raise NotImplementedError(
            "stockDAO.editarStock: implementación pendiente del Agente 1."
        )