# Módulo main.py
# Punto de entrada de la aplicación "Plato a Plato".
# Instancia el controlador y lanza la interfaz gráfica (shell de navegación
# del Agente 2), que arranca en el gestor de sesión.
#
# La lógica de negocio vive en la capa de control (Agente 3) y de acceso
# (Agente 1); main.py sólo compone la aplicación.

from control.controlador import Controlador


def main():
    """Compone controlador + interfaz y arranca el loop de CustomTkinter."""
    controlador = Controlador()

    # Import local: evita cargar Tkinter al importar main.py desde pruebas.
    from vistas.menu import Aplicacion

    app = Aplicacion(controlador)
    app.mainloop()


if __name__ == "__main__":
    main()