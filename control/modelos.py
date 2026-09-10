# Módulo modelos.py
# Define las clases de dominio (DTOs) que los servicios devuelven al
# controlador, sin acoplar la capa de negocios a los DAOs ni a la UI.

from dataclasses import dataclass


@dataclass
class Sesion:
    """Sesión activa de la feria del plato.

    Atributos:
        idSesion: Identificador único de la sesión en la base de datos.
        fechaInicio: Marca de tiempo (str) de creación de la sesión.
        fondoInicial: Monto (float) cargado como fondo/vuelto al crear.
        caja: Disponible actual (float) en caja de la sesión.
    """
    idSesion: int
    fechaInicio: str
    fondoInicial: float
    caja: float


@dataclass
class Producto:
    """Producto del catálogo de la sesión activa.

    Atributos:
        idProducto: Identificador único del producto en la base de datos.
        nombre: Nombre del producto (no vacío).
        precio: Precio unitario (float) mayor o igual a cero.
        stock: Existencias actuales (int) mayor o igual a cero. En
            verProductos() el controlador lo completa consultando a
            servStock.verStock por producto.
    """
    idProducto: int
    nombre: str
    precio: float
    stock: int = 0