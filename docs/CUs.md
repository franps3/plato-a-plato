ID | Caso de uso | Operación/Disparador | Postcondición
CU1 | Crear sesión | Asigna contraseña y monto inicial | Inicializa la sesión y genera la base de datos local
CU2 | Iniciar Sesión | Ingresa credencial de acceso | Desbloquea la interfaz principal del sistema
CU3 | Cerrar Sesión | Selecciona salir | Vuelve a la pantalla de login requiriendo credenciales
CU4 | Crear Producto | Ingresa nombre, precio y stock inicial | Agrega el ítem al catálogo de la sesión
CU5 | Visualizar Productos | Accede a la pestaña de productos | Despliega el listado completo de existencias
CU6 | Seleccionar Producto | Hace clic sobre un ítem de la lista | Habilita los botones de modificación o baja
CU7 | Editar Producto | Modifica nombre, precio o stock | Guarda y refresca los cambios del producto
CU8 | Eliminar Producto | Confirma eliminación | Da de baja el producto de la lista activa
CU9 | Agregar a Venta | Usa botones (+ / -) junto al producto | Modifica la cantidad del ítem en el carrito actual
CU10 | Registrar Venta | Confirma la transacción | Registra venta, descuenta stock y suma total a caja
CU11 | Registrar Gasto | Ingresa nombre, monto y descripción | Registra egreso y restringe/descuenta el valor de caja
CU12 | Ver Historial | Selecciona la pestaña de historial | Renderiza la lista de ventas y gastos registrados
CU13 | Exportar Historial | Selecciona directorio de destino | Genera y guarda un archivo .xlsx
CU14 | Descartar Historial | Ingresa contraseña de confirmación | Limpia el registro de movimientos sin alterar el stock
CU15 | Reiniciar Sistema | Ingresa contraseña de confirmación | Borra la sesión y BD local, restaurando la app a cero
CU16 | Exportar Sesión | Elige carpeta de destino | Empaqueta la BD y estado actual en un .zip
CU17 | Importar Sesión | Selecciona archivo zip y asigna clave | Carga/sobrescribe los datos de la sesión importada.  