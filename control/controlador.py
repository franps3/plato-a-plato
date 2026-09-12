# Módulo controlador.py (Agente 3)
# Capa de control del sistema "Plato a Plato".
# Recibe llamados de las vistas y retorna diccionarios estructurados
# {"ok": bool, "mensaje": str, "datos": ...} para que la UI decida cómo
# refrescar componentes. Tiene operación directa únicamente sobre el manejo
# de la sesión (CU1/CU2/CU3) y el carrito de la venta actual.
#
# Convenciones:
#   * Toda excepción capturada se registra en plato.log con nivel ERROR y
#     stack trace completo; el usuario nunca ve el traceback.
#   * Ningún import de librerías de interfaz gráfica (prohibido por rol).

import hashlib
import logging
from datetime import datetime
from typing import Optional

from .excepciones import (
    AppError,
    CarritoVacio,
    CredencialInvalida,
    FondoInvalido,
    MontoInvalido,
    PasswordInvalido,
    ProductoEnCarrito,
    ProductoNoEncontrado,
    SaldoInsuficiente,
    SesionNoEncontrada,
    SesionYaExiste,
    StockInsuficiente,
)
from .modelos import DetalleVenta, Sesion
from .servProd import ServProd
from .servStock import ServStock
from .servVenta import ServVenta

# Configuración de logging central de la aplicación.
# Se usa un FileHandler explícito para que plato.log se cree bajo cualquier
# entorno (incluido pytest, que instala sus propios handlers en el root).
log = logging.getLogger("controlador")
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


class Controlador:
    """Orquesta las reglas de negocio y el manejo de sesión de la app.

    El controlador se construye con una referencia a mainDAO (inyectable
    para pruebas). Por defecto instancia el DAO real de acceso.mainDAO.
    """

    def __init__(self, dao=None, prodDAO=None, stockDAO=None, ventaDAO=None):
        # Import perezoso: evita dependencias circulares y permite inyectar
        # DAOs falsos en pruebas sin tocar la lógica de negocio. Cuando el
        # Agente 1 entregue los DAOs reales, estos defaults quedan operativos.
        if dao is None:
            from acceso.mainDAO import mainDAO

            dao = mainDAO
        if prodDAO is None:
            from acceso.prodDAO import prodDAO as prodDAOReal

            prodDAO = prodDAOReal()
        if stockDAO is None:
            from acceso.stockDAO import stockDAO as stockDAOReal

            stockDAO = stockDAOReal()
        if ventaDAO is None:
            from acceso.ventaDAO import ventaDAO as ventaDAOReal

            ventaDAO = ventaDAOReal()

        self.dao = dao
        self.prodDAO = prodDAO
        self.stockDAO = stockDAO
        self.ventaDAO = ventaDAO

        # Servicios de negocio (capa de servicios del Agente 3).
        self.servProd = ServProd(prodDAO)
        self.servStock = ServStock(stockDAO)
        self.servVenta = ServVenta(ventaDAO, stockDAO)

        # Estado en memoria del controlador.
        self.sesionActiva: Optional[Sesion] = None
        self.carrito: dict = {}  # {"idProducto": cantidad}

    # ------------------------------------------------------------------
    # Utilidades de validación de dominio
    # ------------------------------------------------------------------
    @staticmethod
    def hashearPassword(password: str) -> str:
        """Devuelve el hash SHA-256 (hex) de una contraseña en texto plano."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _validarPassword(self, password: str) -> None:
        """Valida la contraseña definida por el usuario (mín. 4 caracteres)."""
        if not isinstance(password, str) or len(password) < 4:
            raise PasswordInvalido(
                "La contraseña debe tener al menos 4 caracteres."
            )

    def _validarFondo(self, fondoInicial) -> None:
        """Valida el monto inicial de la sesión (mayor o igual a cero)."""
        if isinstance(fondoInicial, bool) or not isinstance(
            fondoInicial, (int, float)
        ):
            raise FondoInvalido(
                "El fondo inicial debe ser un número mayor o igual a cero."
            )
        if fondoInicial < 0:
            raise FondoInvalido(
                "El fondo inicial debe ser mayor o igual a cero."
            )

    # ------------------------------------------------------------------
    # CU1: crearSesion(password, fondoInicial)
    # Asigna contraseña y monto inicial; inicializa la sesión generando la
    # base de datos local (caja = fondo inicial, sesión única en bd).
    # ------------------------------------------------------------------
    def crearSesion(self, password: str, fondoInicial) -> dict:
        """Crea la sesión única del sistema.

        Postcondición (docs/CUs.md y decisión de diseño):
          * Se inicializa la sesión en mainDAO.
          * Caja queda igual al fondo inicial.
          * Falla con DomainError si ya existe una sesión en la bd.

        Retorno: {"ok": bool, "mensaje": str, "datos": Sesion|None}
        """
        try:
            self._validarPassword(password)
            self._validarFondo(fondoInicial)

            if self.dao.obtenerSesion() is not None:
                raise SesionYaExiste("Ya existe una sesión registrada.")

            fechaInicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            passHash = self.hashearPassword(password)
            idSesion = self.dao.crearSesion(
                passHash, float(fondoInicial), float(fondoInicial), fechaInicio
            )

            # Actualiza el estado de la sesión en el controlador.
            self.sesionActiva = Sesion(
                idSesion=idSesion,
                fechaInicio=fechaInicio,
                fondoInicial=float(fondoInicial),
                caja=float(fondoInicial),
            )
            return {
                "ok": True,
                "mensaje": "Sesión creada correctamente.",
                "datos": self.sesionActiva,
            }

        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU2: iniciarSesion(password)
    # Ingresa la credencial de acceso y desbloquea la interfaz principal.
    # ------------------------------------------------------------------
    def iniciarSesion(self, password: str) -> dict:
        """Valida la contraseña de la sesión registrada (desbloquea UI).

        Retorno: {"ok": bool, "mensaje": str, "datos": Sesion|None}
        """
        try:
            self._validarPassword(password)
            sesionBd = self.dao.obtenerSesion()
            if sesionBd is None:
                raise SesionNoEncontrada(
                    "No hay una sesión registrada. Cree una sesión primero."
                )

            idSesion, fechaInicio, fondoInicial, caja, passHash = sesionBd
            if passHash != self.hashearPassword(password):
                raise CredencialInvalida("Contraseña incorrecta.")

            # Desbloquea la interfaz: sesión activa en memoria.
            self.sesionActiva = Sesion(
                idSesion=idSesion,
                fechaInicio=fechaInicio,
                fondoInicial=float(fondoInicial),
                caja=float(caja),
            )
            return {
                "ok": True,
                "mensaje": "Sesión iniciada correctamente.",
                "datos": self.sesionActiva,
            }

        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU3: cerrarSesion()
    # Selecciona salir: vuelve a la pantalla de login requiriendo
    # credenciales. Solo limpia el estado en memoria (no toca la bd).
    # ------------------------------------------------------------------
    def cerrarSesion(self) -> dict:
        """Cierra la sesión actual: limpia sesión activa y carrito.

        Retorno: {"ok": True, "mensaje": str, "datos": None}
        """
        self.sesionActiva = None
        self.carrito = {}
        return {
            "ok": True,
            "mensaje": "Sesión cerrada. Debe iniciar sesión nuevamente.",
            "datos": None,
        }

    # ------------------------------------------------------------------
    # Auxiliar de estado para las vistas.
    # ------------------------------------------------------------------
    def estaAutenticado(self) -> bool:
        """Indica si hay una sesión activa en memoria (UI desbloqueada)."""
        return self.sesionActiva is not None
    # ------------------------------------------------------------------
    # CU4: crearProducto(nombre, stockInicial, precio)
    # Ingresa nombre, precio y stock inicial: agrega el ítem al catálogo
    # de la sesión. Solo accesible con sesión activa (lo garantiza la vista).
    # ------------------------------------------------------------------
    def crearProducto(self, nombre, stockInicial, precio) -> dict:
        """Agrega un producto al catálogo de la sesión.

        Retorno: {"ok": bool, "mensaje": str, "datos": Producto|None}
        """
        try:
            producto = self.servProd.crearProducto(
                nombre, stockInicial, precio, self.sesionActiva.idSesion
            )
            return {
                "ok": True,
                "mensaje": "Producto agregado al catálogo.",
                "datos": producto,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU5: verProductos()
    # Despliega el listado completo de existencias. El controlador arma el
    # listado combinando prodDAO (productos sin stock) + stockDAO por ítem
    # (decisión de diseño acordada).
    # ------------------------------------------------------------------
    def verProductos(self) -> dict:
        """Lista los productos de la sesión con su stock actual.

        Retorno: {"ok": bool, "mensaje": str, "datos": [Producto, ...]}
        """
        try:
            productos = self.servProd.verProductos(self.sesionActiva.idSesion)
            for producto in productos:
                producto.stock = self.servStock.verStock(producto.idProducto)
            return {
                "ok": True,
                "mensaje": "Catálogo actualizado.",
                "datos": productos,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU6: seleccionarProducto(idProducto)
    # Tarea exclusivamente visual (Agente 2): el clic en un ítem de la
    # lista habilita el menú editar/borrar. No requiere lógica acá.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CU7: editarProducto(idProducto, nombre, precio)
    #      editarStock(idProducto, stock)
    # Modifica nombre/precio (vía prodDAO) o stock (vía stockDAO). La vista
    # refresca el catálogo llamando a verProductos().
    # ------------------------------------------------------------------
    def editarProducto(self, idProducto, nombre, precio) -> dict:
        """Modifica nombre y precio de un producto del catálogo.

        Retorno: {"ok": bool, "mensaje": str, "datos": Producto|None}
        """
        try:
            producto = self.servProd.editarProducto(idProducto, nombre, precio)
            return {
                "ok": True,
                "mensaje": "Producto modificado correctamente.",
                "datos": producto,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def editarStock(self, idProducto, stock) -> dict:
        """Modifica el stock de un producto del catálogo.

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            stockNuevo = self.servStock.editarStock(idProducto, stock)
            return {
                "ok": True,
                "mensaje": "Stock actualizado correctamente.",
                "datos": stockNuevo,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU8: eliminarProducto(idProducto)
    # Da de baja el producto de la lista activa. Está prohibido eliminar
    # un producto que esté en el carrito actual (regla acordada).
    # ------------------------------------------------------------------
    def eliminarProducto(self, idProducto) -> dict:
        """Elimina un producto del catálogo de la sesión.

        Retorno: {"ok": bool, "mensaje": str, "datos": None}
        """
        try:
            if idProducto in self.carrito:
                raise ProductoEnCarrito(
                    "No se puede eliminar un producto que está en el carrito."
                )
            self.servProd.eliminarProducto(idProducto)
            return {
                "ok": True,
                "mensaje": "Producto eliminado correctamente.",
                "datos": None,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # Utilidad de validación de montos (CU11)
    # ------------------------------------------------------------------
    @staticmethod
    def _validarMonto(monto) -> float:
        """Valida que el monto sea numérico y mayor a cero (CU11)."""
        if isinstance(monto, bool) or not isinstance(monto, (int, float)):
            raise MontoInvalido("El monto debe ser un número mayor a cero.")
        if monto <= 0:
            raise MontoInvalido("El monto debe ser un número mayor a cero.")
        return float(monto)

    # ------------------------------------------------------------------
    # CU9: agregarProd(idProducto) / quitarProd(idProducto)
    # Los botones (+/-) junto al producto modifican la cantidad del ítem
    # en el carrito actual. Reglas acordadas:
    #   * agregarProd valida no superar el stock disponible.
    #   * quitarProd resta 1 y al llegar a 0 elimina el ítem del carrito
    #     (la vista garantiza que solo se invoca con el ítem agregado).
    # ------------------------------------------------------------------
    def agregarProd(self, idProducto) -> dict:
        """Suma una unidad del producto al carrito si hay stock (CU9).

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            stock = self.servStock.verStock(idProducto)
            cantidadActual = self.carrito.get(idProducto, 0)
            if cantidadActual + 1 > stock:
                raise StockInsuficiente(
                    "No hay stock suficiente para agregar más unidades."
                )
            self.carrito[idProducto] = cantidadActual + 1
            return {
                "ok": True,
                "mensaje": "Producto agregado a la venta.",
                "datos": self.carrito[idProducto],
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def quitarProd(self, idProducto) -> dict:
        """Resta una unidad; al llegar a 0 elimina el ítem del carrito (CU9).

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            if idProducto in self.carrito:
                nuevaCantidad = self.carrito[idProducto] - 1
                if nuevaCantidad <= 0:
                    del self.carrito[idProducto]
                else:
                    self.carrito[idProducto] = nuevaCantidad
            # La vista garantiza que solo se invoca si el ítem está agregado.
            return {
                "ok": True,
                "mensaje": "Cantidad actualizada.",
                "datos": self.carrito.get(idProducto, 0),
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # CU10: confirmarVenta()
    # Confirma la transacción: registra venta + detalles, descuenta stock,
    # suma el total a caja y vacía el carrito. La caja nueva se persiste
    # en ventaDAO dentro de la misma transacción que la venta.
    # ------------------------------------------------------------------
    def confirmarVenta(self) -> dict:
        """Registra la venta multiproducto del carrito actual (CU10).

        El controlador arma los detalles con el precio actual (servProd),
        servVenta valida stock suficiente ANTES de persistir y luego
        servStock.descontar resta el stock de cada ítem.

        Retorno: {"ok": bool, "mensaje": str, "datos": Venta|None}
        """
        try:
            if not self.carrito:
                raise CarritoVacio("El carrito está vacío.")

            idSesion = self.sesionActiva.idSesion

            # Arma los detalles con el precio actual del producto.
            productos = {
                p.idProducto: p
                for p in self.servProd.verProductos(idSesion)
            }
            detalles = []
            for idProducto, cantidad in self.carrito.items():
                producto = productos.get(idProducto)
                if producto is None:
                    raise ProductoNoEncontrado(
                        "No se encontró el producto solicitado."
                    )
                monto = round(cantidad * producto.precio, 2)
                detalles.append(
                    DetalleVenta(
                        idProducto=idProducto,
                        cantidad=cantidad,
                        precioUnitario=producto.precio,
                        monto=monto,
                    )
                )

            montoNeto = round(sum(d.monto for d in detalles), 2)
            cajaNueva = round(self.sesionActiva.caja + montoNeto, 2)

            # Registra venta + detalles + caja en la misma transacción.
            venta = self.servVenta.registrarVenta(
                idSesion, detalles, cajaNueva
            )

            # Descuenta el stock de cada ítem (validación ya hecha).
            for detalle in detalles:
                self.servStock.descontar(detalle.idProducto, detalle.cantidad)

            # Actualiza el estado en memoria y vacía el carrito.
            self.sesionActiva.caja = cajaNueva
            self.carrito = {}
            return {
                "ok": True,
                "mensaje": "Venta registrada correctamente.",
                "datos": venta,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # CU11: gasto(nombre, desc, monto) / reinsertar(nombre, desc, monto)
    # El gasto registra un egreso (descuenta caja); la reinserción suma
    # dinero a caja. Se persiste el monto FIRMADO (negativo = gasto,
    # positivo = reinserción); el tipo sale del signo en el historial.
    # NO se permite dejar la caja en negativo con un gasto.
    # ------------------------------------------------------------------
    def gasto(self, nombre, desc, monto) -> dict:
        """Registra un egreso y descuenta el valor de caja (CU11).

        Retorno: {"ok": bool, "mensaje": str, "datos": GastoSecundario|None}
        """
        try:
            montoValido = self._validarMonto(monto)
            if montoValido > self.sesionActiva.caja:
                raise SaldoInsuficiente(
                    "No hay saldo suficiente en caja para el gasto."
                )
            cajaNueva = round(self.sesionActiva.caja - montoValido, 2)
            gasto = self.servVenta.registrarGasto(
                self.sesionActiva.idSesion, nombre, montoValido, desc,
                cajaNueva,
            )
            self.sesionActiva.caja = cajaNueva
            return {
                "ok": True,
                "mensaje": "Gasto registrado correctamente.",
                "datos": gasto,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def reinsertar(self, nombre, desc, monto) -> dict:
        """Registra una reinserción de dinero y suma a caja (CU11).

        Retorno: {"ok": bool, "mensaje": str, "datos": GastoSecundario|None}
        """
        try:
            montoValido = self._validarMonto(monto)
            cajaNueva = round(self.sesionActiva.caja + montoValido, 2)
            gasto = self.servVenta.registrarReinsercion(
                self.sesionActiva.idSesion, nombre, montoValido, desc,
                cajaNueva,
            )
            self.sesionActiva.caja = cajaNueva
            return {
                "ok": True,
                "mensaje": "Reinserción registrada correctamente.",
                "datos": gasto,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # CU12: verHistorial()
    # Renderiza la lista de ventas y gastos registrados en una lista única
    # de movimientos ordenada cronológica descendente (más reciente
    # primero). Ventas con detalles [{nombre, cantidad, monto}]; gastos
    # identificados por tipo ('gasto'/'reinsertar') según el signo.
    # ------------------------------------------------------------------
    def verHistorial(self) -> dict:
        """Devuelve los movimientos de la sesión (ventas + gastos) (CU12).

        Retorno: {"ok": bool, "mensaje": str, "datos": [dict, ...]}
        """
        try:
            idSesion = self.sesionActiva.idSesion
            ventas = self.servVenta.verVentas(idSesion)
            gastos = self.servVenta.verGastos(idSesion)
            nombres = {
                p.idProducto: p.nombre
                for p in self.servProd.verProductos(idSesion)
            }

            movimientos = []
            for venta in ventas:
                detalles = [
                    {
                        "nombre": nombres.get(d.idProducto, "Producto"),
                        "cantidad": d.cantidad,
                        "monto": d.monto,
                    }
                    for d in venta.detalles
                ]
                movimientos.append({
                    "tipo": "venta",
                    "fechaHora": venta.fechaHora,
                    "montoNeto": venta.montoNeto,
                    "detalles": detalles,
                })
            for gasto in gastos:
                tipo = "reinsertar" if gasto.monto >= 0 else "gasto"
                movimientos.append({
                    "tipo": tipo,
                    "fechaHora": gasto.fechaHora,
                    "montoNeto": round(abs(gasto.monto), 2),
                    "nombre": gasto.nombre,
                    "descripcion": gasto.descripcion,
                })

            # Orden cronológico descendente (más reciente primero).
            movimientos.sort(key=lambda m: m["fechaHora"], reverse=True)
            return {
                "ok": True,
                "mensaje": "Historial actualizado.",
                "datos": movimientos,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}