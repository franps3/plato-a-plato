# Módulo excepciones.py
# Define la jerarquía de errores de la aplicación "Plato a Plato".
# La capa de Servicio eleva DomainError; la capa DAO encapsula fallas de
# persistencia en PersistenceError. El Controlador captura AppError y
# retorna resultados estructurados a la Vista.

class AppError(Exception):
    """Error base de la aplicación. Toda excepción propia hereda de él."""
    pass


class DomainError(AppError):
    """Error de dominio: una regla de negocio no se cumplió en la operación."""
    pass


class PersistenceError(AppError):
    """Error de persistencia: falló una operación sobre la base de datos local."""
    pass


# ---------------------------------------------------------------------------
# Errores específicos del dominio de sesión (CU1, CU2, CU3)
# ---------------------------------------------------------------------------

class PasswordInvalido(DomainError):
    """La contraseña no cumple las reglas (ej. menos de 4 caracteres)."""
    pass


class FondoInvalido(DomainError):
    """El monto inicial de la sesión es inválido (ej. negativo o no numérico)."""
    pass


class SesionYaExiste(DomainError):
    """Ya existe una sesión registrada en la base de datos (sesión única)."""
    pass


class SesionNoEncontrada(DomainError):
    """No existe una sesión registrada sobre la cual operar."""
    pass


class CredencialInvalida(DomainError):
    """Las credenciales ingresadas no coinciden con la sesión guardada."""
    pass