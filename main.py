# Módulo main.py
# Punto de entrada de la aplicación "Plato a Plato".
# Stub de arranque del Agente 3: instancia el controlador y verifica que la
# capa de control esté operativa antes de que Agente 2 conecte las vistas.
# La UI final (CustomTkinter) la construirá el Agente 2 en /vistas.

from control.controlador import Controlador

if __name__ == "__main__":
    controlador = Controlador()
    print("Aplicación 'Plato a Plato' inicializada. (vista pendiente del Agente 2)")
    print("¿Sesión activa?", controlador.estaAutenticado())