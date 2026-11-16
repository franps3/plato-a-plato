from control.controlador import Controlador
import os
import customtkinter as ctk

def main():
    """Compone controlador + interfaz y arranca el loop de CustomTkinter."""

    controlador = Controlador()

    from vistas.menu import Aplicacion

    app = Aplicacion(controlador)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(BASE_DIR, "vistas", "recursos", "logo.ico")

    app.iconbitmap(icon_path)

    app.mainloop()


if __name__ == "__main__":
    main()