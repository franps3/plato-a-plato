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


# ---------------------------------------------------------------------------
# Errores específicos del dominio de productos (CU4, CU5, CU7, CU8)
# ---------------------------------------------------------------------------

class NombreInvalido(DomainError):
    """El nombre del producto no cumple las reglas (ej. vacío)."""
    pass


class PrecioInvalido(DomainError):
    """El precio del producto es inválido (ej. negativo o no numérico)."""
    pass


class StockInvalido(DomainError):
    """El stock del producto es inválido (ej. negativo o no entero)."""
    pass


class ProductoNoEncontrado(DomainError):
    """No existe el producto solicitado en la sesión."""
    pass


class ProductoEnCarrito(DomainError):
    """Operación rechazada porque el producto está en el carrito actual."""
    pass


# ---------------------------------------------------------------------------
# Errores específicos del dominio de ventas, caja y gastos (CU9-CU12)
# ---------------------------------------------------------------------------

class CarritoVacio(DomainError):
    """Operación rechazada porque el carrito de venta está vacío."""
    pass


class StockInsuficiente(DomainError):
    """No hay stock suficiente del producto para la operación."""
    pass


class SaldoInsuficiente(DomainError):
    """No hay saldo suficiente en caja para registrar el egreso."""
    pass


class MontoInvalido(DomainError):
    """El monto ingresado es inválido (ej. negativo o no numérico)."""
    pass


class VentaNoEncontrada(DomainError):
    """No existe la venta solicitada en la sesión."""
    pass


class CajaNoEncontrada(DomainError):
    """No existe la caja solicitada (ID de caja inválido)."""
    pass


# ---------------------------------------------------------------------------
# Errores específicos del dominio de recuperación de credenciales (MJ3)
# ---------------------------------------------------------------------------

class RespuestaSeguridadInvalida(DomainError):
    """La respuesta de seguridad es inválida o no coincide con la guardada."""
    pass