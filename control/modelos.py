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


@dataclass
class DetalleVenta:
    """Línea de detalle de una venta (tabla DetalleVenta).

    Atributos:
        idProducto: Producto vendido (FK).
        cantidad: Cantidad vendida (int > 0).
        precioUnitario: Precio unitario al momento de la venta.
        monto: Total de la línea = cantidad * precioUnitario.
    """
    idProducto: int
    cantidad: int
    precioUnitario: float
    monto: float


@dataclass
class Venta:
    """Venta registrada de la sesión.

    Atributos:
        idVenta: Identificador único de la venta en la base de datos.
        fechaHora: Marca de tiempo (str) de registro de la venta.
        detalles: Lista de DetalleVenta de la venta.
        montoNeto: Total de la venta (suma de los importes de las líneas).
    """
    idVenta: int
    fechaHora: str
    detalles: list
    montoNeto: float


@dataclass
class GastoSecundario:
    """Gasto o reinserción de dinero de la caja (tabla GastoSecundario).

    Atributos:
        idGasto: Identificador único del gasto en la base de datos.
        nombre: Nombre o concepto del gasto/reinserción.
        monto: Monto FIRMADO: negativo para gasto, positivo para
            reinserción (decisión acordada; el tipo sale del signo).
        descripcion: Descripción aportada por el usuario.
        fechaHora: Marca de tiempo (str) del registro.
    """
    idGasto: int
    nombre: str
    monto: float
    descripcion: str
    fechaHora: str