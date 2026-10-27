## Mejoras y Correcciones

# MJ2: Sección de estadísticas básicas  
- Agregar una nueva vista seleccionable desde la barra con estadísticas básicas:
- Total de entradas $
- Total de salidas $
- Cantidad de productos vendidos
- Cantidad de combos vendidos
- Cantidad de gastos/reingresos registrados
- Producto más vendido
- Combo más vendido

Agregar esta información al archivo de exportación .xlsx

# MJ3: Recuperación de credenciales  
- Implementar un mecanismo de seguridad para restablecer la contraseña en caso de olvido, mediante una pregunta de seguridad, implementada obligatoriamente al crear sesión

# COR6: Ajustes de resolución en la interfaz de inicio  
- Corregir la resolución de la pantalla de inicio para mejorar su legibilidad y aspecto visual

# COR7: Automatizar el fondo inicial  
- Eliminar el campo de definir fondo inicial en la pantalla de crear sesión. Que este valor sea la suma entre las cajas creadas.

# COR8: Corregir combos  
- Eliminar el atributo stock de los combos. Que al registrar la venta de uno se descuente el stock de los productos asociados al mismo. Que no permita vender más productos del stock existente por medio de un combo.

# COR9: Corregir los botones en la pantalla de interfaz de registrar gasto  
- Ajustar el tamaño de los botones “Registrar” y “Cancelar” de forma que puedan mostrar su contenido adecuadamente
