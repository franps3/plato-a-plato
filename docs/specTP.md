# SPEC TÉCNICO: MONITOR DE COCINA (WEBSOCKETS & WEB APP)

Este módulo es una extensión no oficial de un producto ya diseñado y desarrollado. 

## 1. Visión General

Módulo distribuido en red local (LAN) para transmitir pedidos en tiempo real desde la app de escritorio ("Plato a Plato") hacia dispositivos móviles (celular/tablet en cocina) sin internet ni compilación nativa.

```
[PC: CustomTkinter + VentaService] ──(COMMIT BD)──> [FastAPI Server]
                                                            │
                                                     (WebSocket LAN)
                                                            ▼
                                               [Celular: Web App / PWA]

```

## 2. Stack Tecnológico

* **Servidor PC:** Python 3.x, FastAPI + Uvicorn (ejecutado en hilo secundario `daemon`), `qrcode`.

* **Persistencia PC:** SQLite (local).

* **Cliente Móvil:** Web App (HTML5 + JS ES6 Nativo `WebSocket` + Tailwind CSS CDN + Web Audio API).

* **Protocolo:** WebSockets sobre HTTP (LAN). Endpoint: `ws://<IP_PC>:8000/ws/cocina`.

## 3. Integración en Capas (MVC + Network)

1. **Vista Desktop:** Despliega estado del servidor, IP local (`http://<IP_PC>:8000/cocina`), QR de acceso y contador de clientes conectados.

2. **Servicio (`VentaService`):** Tras ejecutar `COMMIT` exitoso en SQLite, envía la venta a la Capa de Red.

3. **Capa de Red (`SocketServerManager`):** Administra el servidor asíncrono y emite la trama JSON a todos los sockets activos.

4. **Cliente Web App:** Recibe el JSON, dispara tono auditivo y renderiza la tarjeta de pedido.

## 4. Funciones por Sector

### A. Sector PC (Desktop App)

* **`ServidorAutonomo`:** Inicializa FastAPI/Uvicorn al abrir la app.

* **`GeneradorQRConexion`:** Crea QR dinámico con la URL de conexión local.

* **`BroadcastVenta`:** Convierte la venta en JSON y emite el evento de red.

* **`ControlConexiones`:** Mantiene registro de monitores conectados.

### B. Sector Celular (Web App)

* **`AutoConexionWS`:** Conexión y reconexión automática tras caídas de Wi-Fi.

* **`AlertaAuditivaVisual`:** Reproduce sonido y destaca pantalla ante `NUEVA_ORDEN`.

* **`GestionEstadoOrden`:** Permite marcar tarjetas como *En Preparación* o *Listo*.

## 5. Contratos de Datos (JSON)

### Evento: `NUEVA_ORDEN` (PC $\rightarrow$ Celular)

```
{
  "evento": "NUEVA_ORDEN",
  "timestamp": "2026-11-05T14:35:10",
  "datos": {
    "id_venta": 104,
    "caja": "Efectivo",
    "total_items": 3,
    "items": [
      {
        "nombre": "Hamburguesa Completa",
        "cantidad": 2,
        "observacion": ""
      },
      {
        "nombre": "Gaseosa 500ml",
        "cantidad": 1,
        "observacion": ""
      }
    ]
  }
}

```

### Evento: `ESTADO_CONEXION` (Handshake)

```
{
  "evento": "ESTADO_CONEXION",
  "timestamp": "2026-11-05T14:35:00",
  "datos": {
    "estado": "CONECTADO",
    "servidor": "Plato a Plato Host",
    "clientes_activos": 1
  }
}

```

## 6. Reglas de Resiliencia

* **Desconexión Total:** La falla de red o la ausencia de celulares no interrumpe el cobro ni la transacción local en la PC.

* **Reconexión Móvil:** El cliente JS reintenta la conexión WebSocket cada 3 segundos si pierde señal.