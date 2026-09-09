### Contexto del Sistema: "Plato a Plato"

Propósito: Aplicación de escritorio monousuario para agilizar y digitalizar en tiempo real el registro de ventas, control de inventario y balance de caja durante ferias del plato escolares.

Alcance Funcional:  
* Gestión de Catálogo (CRUD): Alta, modificación, eliminación y listado de productos (nombre, precio, stock).  
* Registro de Ventas: Venta multiproducto con cálculo de balance y descuento automático e instantáneo de existencias.  
* Caja y Gastos: Control de fondo inicial (vuelto) y registro de gastos secundarios/insumos.  
* Sesiones e Historial: Creación, apertura, cierre, exportación e importación de sesiones; consulta de historial; exportación a Excel; y reseteo parcial o total del sistema.

Fuera de Alcance:  
* Sin Inteligencia de Negocios (reportes avanzados, gráficos ni alertas de stock bajo).  
* Sin registro ni seguimiento de datos de clientes

Stack y Arquitectura:  
* Stack: Python, CustomTkinter (UI), SQLite (Base de datos local), PyInstaller (Ejecutable portable).  
* Patrón: Monolítico local bajo arquitectura MVC \+ Capa de Servicios \+ DAOs.

### Roles de los agentes

## Agente 1: Modelo  
* Objetivo: Garantizar la estructura, integridad y acceso eficiente a los datos almacenados localmente en SQLite  
* Límites: Responsable único del archivo .db, la creación de esquemas, los DTOs y la ejecución de consultas SQL.  
* Entidades a Cargo: Sesion, Producto, Venta, DetalleVenta, GastoSecundario  
* Componentes: mainDAO, ventaDAO, prodDAO, stockDAO  
* Regla clave: Capturar sqlite.Error, ejecutar ROLLBACK y devolver como PersistenceError . Prohibido importar librerias de UI o definir deglas de negocio. 

## Agente 2: Vista  
* Objetivo: Construir la interfaz de usuario con CustomTkinter y renderizar diálogos/alertas.  
* Componentes: login, venta, confVenta, config  
* Regla clave: Cero lógica operativa. Sólo leer entradas, invocar métodos del controlador y refrescar componentes según el resultado. Analizar diseños en archivo png antes de generar una vista. 

## Agente 3: Controlador y Servicios  
* Objetivo: Validar reglas de negocio, orquestar operaciones transaccionales entre DAOs y canalizar respuestas a la UI .  
* Componentes: controlador, servProd, servVenta, servStock, modelos, excepciones  
* Regla Clave: Elevar DomainError ante inconsistencias operativas (ej. stock insuficiente). El Controlador captura cualquier AppError para retornar resultados estructurados a la Vista. 