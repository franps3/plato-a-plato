# MÃ³dulo controlador.py (Agente 3)
# Capa de control del sistema "Plato a Plato".
# Recibe llamados de las vistas y retorna diccionarios estructurados
# {"ok": bool, "mensaje": str, "datos": ...} para que la UI decida cÃ³mo
# refrescar componentes. Tiene operaciÃ³n directa Ãºnicamente sobre el manejo
# de la sesiÃ³n (CU1/CU2/CU3) y el carrito de la venta actual.
#
# Convenciones:
#   * Toda excepciÃ³n capturada se registra en plato.log con nivel ERROR y
#     stack trace completo; el usuario nunca ve el traceback.
#   * NingÃºn import de librerÃ­as de interfaz grÃ¡fica (prohibido por rol).

import hashlib
import logging
from datetime import datetime
from typing import Optional

from .excepciones import (
    AppError,
    CarritoVacio,
    CajaNoEncontrada,
    CredencialInvalida,
    MontoInvalido,
    PasswordInvalido,
    ProductoEnCarrito,
    ProductoNoEncontrado,
    SaldoInsuficiente,
    SesionNoEncontrada,
    SesionYaExiste,
    StockInsuficiente,
)
from .modelos import Caja, DetalleVenta, Sesion
from .servProd import ServProd
from .servStock import ServStock
from .servVenta import ServVenta

# ConfiguraciÃ³n de logging central de la aplicaciÃ³n.
# Se usa un FileHandler explÃ­cito para que plato.log se cree bajo cualquier
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
    """Orquesta las reglas de negocio y el manejo de sesiÃ³n de la app.

    El controlador se construye con una referencia a mainDAO (inyectable
    para pruebas). Por defecto instancia el DAO real de acceso.mainDAO.
    """

    def __init__(self, dao=None, prodDAO=None, stockDAO=None, ventaDAO=None):
        # Import perezoso: evita dependencias circulares y permite inyectar
        # DAOs falsos en pruebas sin tocar la lÃ³gica de negocio. Cuando el
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
        self.servVenta = ServVenta(ventaDAO, stockDAO, prodDAO)

        # Estado en memoria del controlador.
        self.sesionActiva: Optional[Sesion] = None
        self.carrito: dict = {}  # {"idProducto": cantidad}

    # ------------------------------------------------------------------
    # Utilidades de validaciÃ³n de dominio
    # ------------------------------------------------------------------
    @staticmethod
    def hashearPassword(password: str) -> str:
        """Devuelve el hash SHA-256 (hex) de una contraseÃ±a en texto plano."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _validarPassword(self, password: str) -> None:
        """Valida la contraseÃ±a definida por el usuario (mÃ­n. 4 caracteres)."""
        if not isinstance(password, str) or len(password) < 4:
            raise PasswordInvalido(
                "La contraseÃ±a debe tener al menos 4 caracteres."
            )

    # ------------------------------------------------------------------
    # CU1: crearSesion(password, fondoInicial)
    # Asigna contraseÃ±a y monto inicial; inicializa la sesiÃ³n generando la
    # base de datos local (caja = fondo inicial, sesiÃ³n Ãºnica en bd).
    # ------------------------------------------------------------------
    def crearSesion(self, password: str, cajas=None) -> dict:
        """Crea la sesiÃ³n Ãºnica del sistema.

        PostcondiciÃ³n (docs/CUs.md y decisiÃ³n de diseÃ±o):
          * Se inicializa la sesiÃ³n en mainDAO.
          * Caja queda igual al fondo inicial.
          * Falla con DomainError si ya existe una sesiÃ³n en la bd.

        Retorno: {"ok": bool, "mensaje": str, "datos": Sesion|None}
        """
        try:
            self._validarPassword(password)

            # COR7: el fondo inicial es la suma de los montos de las cajas.
            fondoInicial = round(
                sum(monto for _, monto in (cajas or [])), 2
            )

            if self.dao.obtenerSesion() is not None:
                raise SesionYaExiste("Ya existe una sesiÃ³n registrada.")

            fechaInicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            passHash = self.hashearPassword(password)
            idSesion = self.dao.crearSesion(
                passHash, fondoInicial, fondoInicial, fechaInicio,
                cajas,
            )

            # Actualiza el estado de la sesiÃ³n en el controlador.
            self.sesionActiva = Sesion(
                idSesion=idSesion,
                fechaInicio=fechaInicio,
                fondoInicial=fondoInicial,
                caja=fondoInicial,
            )
            return {
                "ok": True,
                "mensaje": "SesiÃ³n creada correctamente.",
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
        """Valida la contraseÃ±a de la sesiÃ³n registrada (desbloquea UI).

        Retorno: {"ok": bool, "mensaje": str, "datos": Sesion|None}
        """
        try:
            self._validarPassword(password)
            sesionBd = self.dao.obtenerSesion()
            if sesionBd is None:
                raise SesionNoEncontrada(
                    "No hay una sesiÃ³n registrada. Cree una sesiÃ³n primero."
                )

            idSesion, fechaInicio, fondoInicial, caja, passHash = sesionBd
            if passHash != self.hashearPassword(password):
                raise CredencialInvalida("ContraseÃ±a incorrecta.")

            # Desbloquea la interfaz: sesiÃ³n activa en memoria.
            self.sesionActiva = Sesion(
                idSesion=idSesion,
                fechaInicio=fechaInicio,
                fondoInicial=float(fondoInicial),
                caja=float(caja),
            )
            return {
                "ok": True,
                "mensaje": "SesiÃ³n iniciada correctamente.",
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
        """Cierra la sesiÃ³n actual: limpia sesiÃ³n activa y carrito.

        Retorno: {"ok": True, "mensaje": str, "datos": None}
        """
        self.sesionActiva = None
        self.carrito = {}
        return {
            "ok": True,
            "mensaje": "SesiÃ³n cerrada. Debe iniciar sesiÃ³n nuevamente.",
            "datos": None,
        }

    # ------------------------------------------------------------------
    # MJ1/MJ7: cajas (medios de pago) y total de caja
    # ------------------------------------------------------------------
    def verCajas(self, idSesion) -> dict:
        """Lista las cajas de la sesiÃ³n (MJ1).

        Retorno: {"ok": bool, "mensaje": str, "datos": [Caja, ...]}
        """
        try:
            filas = self.dao.verCajas(idSesion)
            cajas = [
                Caja(
                    idCaja=f[0], idSesion=idSesion, nombre=f[1],
                    fondoInicial=float(f[2]), monto=float(f[3]),
                )
                for f in filas
            ]
            return {
                "ok": True,
                "mensaje": "Cajas de la sesiÃ³n obtenidas.",
                "datos": cajas,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def verTotalCajas(self, idSesion) -> dict:
        """Devuelve el total de caja (suma de los Monto de todas las cajas) (MJ1/MJ7).

        Retorno: {"ok": bool, "mensaje": str, "datos": float}
        """
        try:
            total = self.dao.verTotalCajas(idSesion)
            return {
                "ok": True,
                "mensaje": "Total de caja calculado.",
                "datos": total,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def obtenerCaja(self, idCaja) -> dict:
        """Devuelve una caja por su ID (MJ1).

        Retorno: {"ok": bool, "mensaje": str, "datos": Caja|None}
        """
        try:
            fila = self.dao.obtenerCaja(idCaja)
            if fila is None:
                raise CajaNoEncontrada(f"No existe la caja con ID {idCaja}.")
            caja = Caja(
                idCaja=fila[0], idSesion=fila[1], nombre=fila[2],
                fondoInicial=float(fila[3]), monto=float(fila[4]),
            )
            return {
                "ok": True,
                "mensaje": "Caja obtenida.",
                "datos": caja,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # Auxiliar de estado para las vistas.
    # ------------------------------------------------------------------
    def estaAutenticado(self) -> bool:
        """Indica si hay una sesiÃ³n activa en memoria (UI desbloqueada)."""
        return self.sesionActiva is not None
    # ------------------------------------------------------------------
    # CU4: crearProducto(nombre, stockInicial, precio)
    # Ingresa nombre, precio y stock inicial: agrega el Ã­tem al catÃ¡logo
    # de la sesiÃ³n. Solo accesible con sesiÃ³n activa (lo garantiza la vista).
    # ------------------------------------------------------------------
    def crearProducto(self, nombre, stockInicial, precio) -> dict:
        """Agrega un producto al catÃ¡logo de la sesiÃ³n.

        Retorno: {"ok": bool, "mensaje": str, "datos": Producto|None}
        """
        try:
            producto = self.servProd.crearProducto(
                nombre, stockInicial, precio, self.sesionActiva.idSesion
            )
            return {
                "ok": True,
                "mensaje": "Producto agregado al catÃ¡logo.",
                "datos": producto,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU5: verProductos()
    # Despliega el listado completo de existencias. El controlador arma el
    # listado combinando prodDAO (productos sin stock) + stockDAO por Ã­tem
    # (decisiÃ³n de diseÃ±o acordada).
    # ------------------------------------------------------------------
    def verProductos(self) -> dict:
        """Lista los productos de la sesiÃ³n con su stock actual.

        Retorno: {"ok": bool, "mensaje": str, "datos": [Producto, ...]}
        """
        try:
            productos = self.servProd.verProductos(self.sesionActiva.idSesion)
            for producto in productos:
                producto.stock = self.servStock.verStock(producto.idProducto)
            return {
                "ok": True,
                "mensaje": "CatÃ¡logo actualizado.",
                "datos": productos,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # COR2: verProductosVenta()
    # Igual que verProductos(), pero el stock devuelto es el DISPONIBLE para
    # la pantalla de Venta: se le resta la cantidad reservada en el carrito
    # (reserva VISUAL, sin tocar la base). El descuento real del stock ocurre
    # reciÃ©n en confirmarVenta (CU10). La pantalla de ConfiguraciÃ³n debe
    # seguir usando verProductos() (stock real de la bd).
    # ------------------------------------------------------------------
    def verProductosVenta(self) -> dict:
        """Lista los productos con su stock DISPONIBLE para vender (COR2).

        Calcula el disponible como max(0, stock real - cantidad en carrito)
        de cada producto. Es una reserva visual para el descuento en vivo de
        la pantalla de Venta; NO escribe en la base (el stock real sÃ³lo se
        descuenta al confirmar la venta, CU10).

        Retorno: {"ok": bool, "mensaje": str, "datos": [Producto, ...]}
        """
        try:
            productos = self.servProd.verProductos(self.sesionActiva.idSesion)
            for producto in productos:
                stockReal = self.servStock.verStock(producto.idProducto)
                reservado = self.carrito.get(producto.idProducto, 0)
                producto.stock = max(0, stockReal - reservado)
            return {
                "ok": True,
                "mensaje": "CatÃ¡logo actualizado.",
                "datos": productos,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU6: seleccionarProducto(idProducto)
    # Tarea exclusivamente visual (Agente 2): el clic en un Ã­tem de la
    # lista habilita el menÃº editar/borrar. No requiere lÃ³gica acÃ¡.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CU7: editarProducto(idProducto, nombre, precio)
    #      editarStock(idProducto, stock)
    # Modifica nombre/precio (vÃ­a prodDAO) o stock (vÃ­a stockDAO). La vista
    # refresca el catÃ¡logo llamando a verProductos().
    # ------------------------------------------------------------------
    def editarProducto(self, idProducto, nombre, precio) -> dict:
        """Modifica nombre y precio de un producto del catÃ¡logo.

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
        """Modifica el stock de un producto del catÃ¡logo.

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
    # Da de baja el producto de la lista activa. EstÃ¡ prohibido eliminar
    # un producto que estÃ© en el carrito actual (regla acordada).
    # ------------------------------------------------------------------
    def eliminarProducto(self, idProducto) -> dict:
        """Elimina un producto del catÃ¡logo de la sesiÃ³n.

        Retorno: {"ok": bool, "mensaje": str, "datos": None}
        """
        try:
            if idProducto in self.carrito:
                raise ProductoEnCarrito(
                    "No se puede eliminar un producto que estÃ¡ en el carrito."
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
    # MJ4: combos (delegan en servProd / prodDAO)
    # ------------------------------------------------------------------
    def crearCombo(self, nombre, precio, componentes) -> dict:
        """Crea un combo y sus componentes (MJ4).

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            idCombo = self.servProd.crearCombo(
                self.sesionActiva.idSesion, nombre, precio, componentes
            )
            return {
                "ok": True,
                "mensaje": "Combo creado correctamente.",
                "datos": idCombo,
            }
        except (AppError, ValueError) as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def verCombos(self) -> dict:
        """Lista los combos de la sesiÃ³n (MJ4).

        Retorno: {"ok": bool, "mensaje": str, "datos": [(id, nombre, precio), ...]}
        """
        try:
            combos = self.servProd.verCombos(self.sesionActiva.idSesion)
            return {
                "ok": True,
                "mensaje": "Combos obtenidos.",
                "datos": combos,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def verComponentesCombo(self, idCombo) -> dict:
        """Devuelve los componentes de un combo (MJ4).

        Retorno: {"ok": bool, "mensaje": str, "datos": [(idProducto, cantidad), ...]}
        """
        try:
            componentes = self.servProd.verComponentesCombo(idCombo)
            return {
                "ok": True,
                "mensaje": "Componentes del combo obtenidos.",
                "datos": componentes,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def editarCombo(self, idCombo, nombre, precio, componentes) -> dict:
        """Actualiza nombre, precio y componentes de un combo (MJ4).

        Retorno: {"ok": bool, "mensaje": str, "datos": tuple|None}
        """
        try:
            resultado = self.servProd.editarCombo(
                idCombo, nombre, precio, componentes
            )
            if resultado is None:
                raise ProductoNoEncontrado("No se encontrÃ³ el combo a editar.")
            return {
                "ok": True,
                "mensaje": "Combo modificado correctamente.",
                "datos": resultado,
            }
        except (AppError, ValueError) as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def eliminarCombo(self, idCombo) -> dict:
        """Elimina un combo y sus componentes (MJ4).

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            filas = self.servProd.eliminarCombo(idCombo)
            if filas == 0:
                raise ProductoNoEncontrado("No se encontrÃ³ el combo a eliminar.")
            return {
                "ok": True,
                "mensaje": "Combo eliminado correctamente.",
                "datos": filas,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

# ------------------------------------------------------------------
    # Utilidad de validaciÃ³n de montos (CU11)
    # ------------------------------------------------------------------
    @staticmethod
    def _validarMonto(monto) -> float:
        """Valida que el monto sea numÃ©rico y mayor a cero (CU11)."""
        if isinstance(monto, bool) or not isinstance(monto, (int, float)):
            raise MontoInvalido("El monto debe ser un nÃºmero mayor a cero.")
        if monto <= 0:
            raise MontoInvalido("El monto debe ser un nÃºmero mayor a cero.")
        return float(monto)

    # ------------------------------------------------------------------
    # CU9: agregarProd(idProducto) / quitarProd(idProducto)
    # Los botones (+/-) junto al producto modifican la cantidad del Ã­tem
    # en el carrito actual. Reglas acordadas:
    #   * agregarProd valida no superar el stock disponible.
    #   * quitarProd resta 1 y al llegar a 0 elimina el Ã­tem del carrito
    #     (la vista garantiza que solo se invoca con el Ã­tem agregado).
    # ------------------------------------------------------------------
    def agregarProd(self, idProducto) -> dict:
        """Suma una unidad del producto al carrito si hay stock (CU9).

        Los combos no tienen stock propio (COR8): su disponibilidad se
        valida al confirmar la venta sobre sus componentes.

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            # COR8: los combos no tienen stock propio; se salta la
            # validaciÃ³n de stock (se valida al confirmar la venta).
            idsCombos = {
                c[0]
                for c in self.servProd.verCombos(self.sesionActiva.idSesion)
            }
            if idProducto not in idsCombos:
                stock = self.servStock.verStock(idProducto)
                cantidadActual = self.carrito.get(idProducto, 0)
                if cantidadActual + 1 > stock:
                    raise StockInsuficiente(
                        "No hay stock suficiente para agregar mÃ¡s unidades."
                    )
            self.carrito[idProducto] = self.carrito.get(idProducto, 0) + 1
            return {
                "ok": True,
                "mensaje": "Producto agregado a la venta.",
                "datos": self.carrito[idProducto],
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    def quitarProd(self, idProducto) -> dict:
        """Resta una unidad; al llegar a 0 elimina el Ã­tem del carrito (CU9).

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            if idProducto in self.carrito:
                nuevaCantidad = self.carrito[idProducto] - 1
                if nuevaCantidad <= 0:
                    del self.carrito[idProducto]
                else:
                    self.carrito[idProducto] = nuevaCantidad
            # La vista garantiza que solo se invoca si el Ã­tem estÃ¡ agregado.
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
    # Confirma la transacciÃ³n: registra venta + detalles, descuenta stock,
    # suma el total a caja y vacÃ­a el carrito. La caja nueva se persiste
    # en ventaDAO dentro de la misma transacciÃ³n que la venta.
    # ------------------------------------------------------------------
    def confirmarVenta(self, idCaja=None) -> dict:
        """Registra la venta multiproducto del carrito actual (CU10).

        El controlador arma los detalles con el precio actual (servProd),
        servVenta valida stock suficiente ANTES de persistir y luego
        servStock.descontar resta el stock de cada Ã­tem.

        Retorno: {"ok": bool, "mensaje": str, "datos": Venta|None}
        """
        try:
            if not self.carrito:
                raise CarritoVacio("El carrito estÃ¡ vacÃ­o.")

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
                        "No se encontrÃ³ el producto solicitado."
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

            # IDs de combo de la sesiÃ³n (COR8): su stock se descuenta de
            # los componentes, no del combo en sÃ­.
            idsCombos = {c[0] for c in self.servProd.verCombos(idSesion)}

            # Registra venta + detalles + caja en la misma transacciÃ³n.
            venta = self.servVenta.registrarVenta(
                idSesion, detalles, cajaNueva, idCaja
            )

            # Descuenta el stock de cada Ã­tem (validaciÃ³n ya hecha).
            # Si es un combo, se descuenta de sus componentes.
            for detalle in detalles:
                if detalle.idProducto in idsCombos:
                    componentes = self.servProd.verComponentesCombo(
                        detalle.idProducto
                    )
                    for idComp, cantComp in componentes:
                        self.servStock.descontar(
                            idComp, detalle.cantidad * cantComp
                        )
                else:
                    self.servStock.descontar(
                        detalle.idProducto, detalle.cantidad
                    )

            # Actualiza el estado en memoria y vacÃ­a el carrito.
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
    # El gasto registra un egreso (descuenta caja); la reinserciÃ³n suma
    # dinero a caja. Se persiste el monto FIRMADO (negativo = gasto,
    # positivo = reinserciÃ³n); el tipo sale del signo en el historial.
    # NO se permite dejar la caja en negativo con un gasto.
    # ------------------------------------------------------------------
    def gasto(self, nombre, desc, monto, idCaja=None) -> dict:
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
                cajaNueva, idCaja,
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

    def reinsertar(self, nombre, desc, monto, idCaja=None) -> dict:
        """Registra una reinserciÃ³n de dinero y suma a caja (CU11).

        Retorno: {"ok": bool, "mensaje": str, "datos": GastoSecundario|None}
        """
        try:
            montoValido = self._validarMonto(monto)
            cajaNueva = round(self.sesionActiva.caja + montoValido, 2)
            gasto = self.servVenta.registrarReinsercion(
                self.sesionActiva.idSesion, nombre, montoValido, desc,
                cajaNueva, idCaja,
            )
            self.sesionActiva.caja = cajaNueva
            return {
                "ok": True,
                "mensaje": "ReinserciÃ³n registrada correctamente.",
                "datos": gasto,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # CU12: verHistorial()
    # Renderiza la lista de ventas y gastos registrados en una lista Ãºnica
    # de movimientos ordenada cronolÃ³gica descendente (mÃ¡s reciente
    # primero). Ventas con detalles [{nombre, cantidad, monto}]; gastos
    # identificados por tipo ('gasto'/'reinsertar') segÃºn el signo.
    # ------------------------------------------------------------------
    def verHistorial(self) -> dict:
        """Devuelve los movimientos de la sesiÃ³n (ventas + gastos) (CU12).

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

            # Orden cronolÃ³gico descendente (mÃ¡s reciente primero).
            movimientos.sort(key=lambda m: m["fechaHora"], reverse=True)
            return {
                "ok": True,
                "mensaje": "Historial actualizado.",
                "datos": movimientos,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # Auxiliar para la vista de login (bloqueo del Agente 2)
    # ------------------------------------------------------------------
    def haySesion(self) -> dict:
        """Comprueba si existe una sesiÃ³n en la base de datos (login).

        No valida la contraseÃ±a: solo indica si hay una sesiÃ³n creada,
        para que la vista muestre la pantalla correcta (crear o iniciar).

        Retorno: {"ok": bool, "mensaje": str, "datos": bool|None}
        """
        try:
            return {
                "ok": True,
                "mensaje": "Consulta de sesiÃ³n realizada.",
                "datos": self.dao.obtenerSesion() is not None,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU9 (complemento): quitarProdCompleto(idProducto)
    # Quita un producto POR COMPLETO del carrito sin restar de a uno.
    # Requerido por el Agente 2 (botÃ³n x del carrito).
    # ------------------------------------------------------------------
    def quitarProdCompleto(self, idProducto) -> dict:
        """Elimina un producto del carrito por completo (bloqueo Agente 2).

        Retorno: {"ok": bool, "mensaje": str, "datos": int|None}
        """
        try:
            self.carrito.pop(idProducto, None)
            return {
                "ok": True,
                "mensaje": "Producto eliminado del carrito.",
                "datos": 0,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU14: borrarHistorial(password)
    # Ingresa la contraseÃ±a de confirmaciÃ³n; si es correcta, limpia el
    # registro de movimientos (ventas, detalles y gastos/reinserciones)
    # sin alterar el stock ni la sesiÃ³n. Si la contraseÃ±a no coincide,
    # no se borra nada.
    # ------------------------------------------------------------------
    def borrarHistorial(self, password) -> dict:
        """Descarta el historial de movimientos de la sesiÃ³n (CU14).

        Retorno: {"ok": bool, "mensaje": str, "datos": None}
        """
        try:
            self._validarPassword(password)
            idSesion = self.sesionActiva.idSesion
            sesionBd = self.dao.obtenerSesion()
            if sesionBd is None:
                raise SesionNoEncontrada(
                    "No hay una sesiÃ³n registrada. Cree una sesiÃ³n primero."
                )
            if sesionBd[4] != self.hashearPassword(password):
                raise CredencialInvalida("ContraseÃ±a incorrecta.")

            self.servVenta.borrarHistorial(idSesion)
            return {
                "ok": True,
                "mensaje": "Historial descartado correctamente.",
                "datos": None,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU15: reiniciar(password)
    # Ingresa la contraseÃ±a de confirmaciÃ³n; si es correcta, borra la
    # sesiÃ³n y la BD local, restaurando la aplicaciÃ³n a cero (nuke).
    # Tras reiniciar se limpia el estado en memoria y la vista vuelve
    # a la pantalla de creaciÃ³n de sesiÃ³n.
    # ------------------------------------------------------------------
    def reiniciar(self, password) -> dict:
        """Reinicia el sistema: borra la BD local y la sesiÃ³n (CU15).

        Retorno: {"ok": bool, "mensaje": str, "datos": None}
        """
        try:
            self._validarPassword(password)
            sesionBd = self.dao.obtenerSesion()
            if sesionBd is None:
                raise SesionNoEncontrada(
                    "No hay una sesiÃ³n registrada. Cree una sesiÃ³n primero."
                )
            if sesionBd[4] != self.hashearPassword(password):
                raise CredencialInvalida("ContraseÃ±a incorrecta.")

            self.dao.nuke()
            self.sesionActiva = None
            self.carrito = {}
            return {
                "ok": True,
                "mensaje": "Sistema reiniciado correctamente.",
                "datos": None,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
# ------------------------------------------------------------------
    # CU13: exportExcel(rutaDestino)
    # Selecciona directorio de destino (la vista elige con diÃ¡logo): genera
    # y guarda un archivo .xlsx con el historial de la sesiÃ³n (ventas y
    # gastos). Delega en mainDAO.exportar("historial", rutaDestino), que
    # eleva PersistenceError ante fallos.
    # ------------------------------------------------------------------
    def exportExcel(self, rutaDestino) -> dict:
        """Exporta el historial de la sesiÃ³n a un archivo .xlsx (CU13).

        Retorno: {"ok": bool, "mensaje": str, "datos": str|None}
        """
        try:
            rutaGenerada = self.dao.exportar("historial", rutaDestino)
            return {
                "ok": True,
                "mensaje": "Historial exportado correctamente.",
                "datos": rutaGenerada,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU16: exportarDb(rutaDestino)
    # Elige carpeta de destino (la vista la pide con diÃ¡logo): empaqueta la
    # BD y el estado actual en un .zip. Delega en
    # mainDAO.exportar("sesion", rutaDestino).
    # ------------------------------------------------------------------
    def exportarDb(self, rutaDestino) -> dict:
        """Exporta la sesiÃ³n (BD local) a un archivo .zip (CU16).

        Retorno: {"ok": bool, "mensaje": str, "datos": str|None}
        """
        try:
            rutaGenerada = self.dao.exportar("sesion", rutaDestino)
            return {
                "ok": True,
                "mensaje": "SesiÃ³n exportada correctamente.",
                "datos": rutaGenerada,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}

    # ------------------------------------------------------------------
    # CU17: importarDb(rutaZip, passNueva)
    # Selecciona archivo zip y asigna clave: la valida (mÃ­n. 4 caracteres),
    # la hashea y delega en mainDAO.importar(rutaZip, passHash) para
    # cargar/sobrescribir la sesiÃ³n importada. Tras importar, la sesiÃ³n
    # queda disponible para iniciar con la clave asignada.
    # ------------------------------------------------------------------
    def importarDb(self, rutaZip, passNueva) -> dict:
        """Importa una sesiÃ³n desde un archivo .zip y asigna clave (CU17).

        Retorno: {"ok": bool, "mensaje": str, "datos": Sesion|None}
        """
        try:
            self._validarPassword(passNueva)
            passHash = self.hashearPassword(passNueva)
            sesionBd = self.dao.importar(rutaZip, passHash)
            if sesionBd is None:
                raise SesionNoEncontrada(
                    "El archivo no contiene una sesiÃ³n importable."
                )
            idSesion, fechaInicio, fondoInicial, caja, _ = sesionBd
            self.sesionActiva = Sesion(
                idSesion=idSesion,
                fechaInicio=fechaInicio,
                fondoInicial=float(fondoInicial),
                caja=float(caja),
            )
            self.carrito = {}
            return {
                "ok": True,
                "mensaje": "SesiÃ³n importada correctamente.",
                "datos": self.sesionActiva,
            }
        except AppError as err:
            log.error("%s: %s", type(err).__name__, err, exc_info=True)
            return {"ok": False, "mensaje": str(err), "datos": None}
