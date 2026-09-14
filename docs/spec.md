### Módulos Principales

* Vistas: Cada interfaz tiene un archivo.py distinto. Únicamente se comunican con controlador.py por llamado de funciones.   
* Controlador: Recibe llamado de vista y devuelve en forma de lista o clase la función. No opera sobre datos directamente. Sólo tiene operación directa sobre el manejo de sesión. Tiene un diccionario carrito{idProd, cantidad} para almacenar los productos añadidos a una venta.   
* Servicios: Reciben llamado de controlador y devuelven en forma de lista o clase el resultado. Para consultar o escribir de bd se comunican con los DAOs. Devuelven productos y ventas en forma de objetos instanciados de modelos.py.   
* DAOs: Realizan consultas a bd y devuelven tuplas crudas. mainDAO se encarga de la conexión de base de datos, el cursor que usan los demás DAO y el manejo de sesiones. 

### Estructura de datos

- /vistas  
  - login.py  
  - venta.py  
  - confVenta.py  
  - config.py   
- /control  
  - controlador.py  
  - servProd.py  
  - servVenta.py  
  - servStock.py  
  - modelos.py
  - excepciones.py  
- /acceso  
  - prodDAO.py  
  - ventaDAO.py  
  - stockDAO.py  
  - mainDAO.py  
- main.py  
- bd.db   
- plato.log
- requirements.txt

### Parámetros de desarrollo

- Código claro, legible, en español y comentado por función y módulo  
- camelCase para variables, funciones y módulos 
- PascalCase para entidades de bd
- Una vez completada una tarea realizar commit y push
- Formato de commits "CUx, CUxx, agente x". Por cada commit escribir en changelog.txt fecha del commit, agente responsable y un breve resumen de lo que se hizo

### MER  
**Tablas y atributos  
* Sesion: ID_sesion (PK), Fecha_inicio, Fondo_inicial, Caja, Pass. 
* Producto: ID_producto (PK), ID_sesion (FK), Nombre, Stock, Precio.
* Venta: ID_venta (PK), ID_sesion (FK), Fecha_hora.
* DetalleVenta: ID_venta (FK), ID_Producto (FK), Cantidad, Precio_unitario.
* GastoSecundario: ID_gasto (PK), ID_sesion (FK), Nombre, Monto, Descripcion, Fecha_hora.

**Relaciones de Dominio  
* Sesion -> Producto / Venta / GastoSecundario: Relación 1:N (Una sesión agrupa múltiples productos, ventas y gastos registrados).  
* Venta <-> Producto: Relación N:M resolviendo la asociación intermedia mediante la tabla DetalleVenta.

### Mapeo de Casos de uso desde controlador  
* CU1: crearSesion(pass, fondoInicial) -> mainDAO.crearSesion()  
* CU2: iniciarSesion(pass)  
* CU3: cerrarSesion()  
* CU4: crearProducto(nombre, stockInicial, precio) -> servProd.crearProducto -> prodDAO  
* CU5: verProductos() -> servProd.verProductos(), servStock.verStock(idProd) -> prodDAO, stockDAO  
* CU6: seleccionarProducto(idProd)  
* CU7: editarProducto(idProd, newNombre, newPrecio) o editarStock(idProd, newStock) ->servProd.editarProducto(idProd, nombre, precio, stock), servStock.editarStock(idProd, newStock) -> prodDAO, stockDAO  
* CU8: eliminarProducto(idProd) -> servProd.eliminarProducto(idProd) -> prodDAO
* CU9: agregarProd(idProd)  
* CU10: confirmarVenta(carrito) -> servVenta.registrarVenta(carrito), servStock.descontar(idProd, stock) -> ventaDAO, stockDAO  
* CU11: gasto(nombre, desc, monto) -> servVenta.registrarGasto() -> ventaDAO
* CU12: verHistorial() -> servVenta.verVentas(), servVenta.verGastos(), servProd.verProductos() -> ventaDAO, prodDAO  
* CU13: exportExcel() -> mainDAO.exportar()  
* CU14: borrarHistorial() -> servVenta.borrarHistorial() -> ventaDAO  
* CU15: reiniciar() -> mainDAO.nuke()  
* CU16: exportarDb() -> mainDAO.exportar()  
* CU17: importarDb() -> mainDAO.importar()

### Excepciones  
**Jerarquía

* AppError(Exception)  
* DomainError(AppError)  
* PersistenceError(AppError)

Los errores específicos heredan de DomainError o PersistenceError (stockInsuficiente, etc.)

**Responsabilidad por capa

*Capa DAO: Captura excepciones nativas de la librería (sqlite3.Error), ejecuta conn.rollback() si hay una transacción activa y re-eleva la falla encapsulada en una subclase de PersistenceError.  
*Capa de Servicio: Aplica validaciones del dominio. Si una condición operativa no se cumple, eleva un DomainError. No manipula elementos gráficos.  
*Capa Controlador / UI: Captura exclusivamente instancias de AppError. Extrae el mensaje de error para mostrarlo en un componente visual (CTkMessagebox) y mantiene la aplicación estable sin detener el loop de Tkinter.

**Logging  
Toda excepción capturada en la capa de control/UI debe registrarse mediante el módulo logging de Python en plato.log. El registro incluirá la marca de tiempo, el nombre de la excepción y el stack trace completo con nivel ERROR. Queda prohibido mostrar detalles técnicos del traceback directamente al usuario.  
