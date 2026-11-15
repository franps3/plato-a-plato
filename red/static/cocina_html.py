# Módulo red/static/cocina_html.py
# Monitor de Cocina (specTP.md)
COCINA_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Monitor de Cocina - Plato a Plato</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; }
    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 1rem;
      padding: 1.25rem;
      transition: all 0.2s ease;
    }
    .card.listo { border-color: #22c55e; background: #142320; }
    .card.preparando { opacity: 0.7; }
    .btn-listo {
      background: #22c55e;
      border-color: #22c55e;
      color: #0f172a;
    }
    .btn-listo:hover { background: #16a34a; }
    .badge {
      color: #22c55e;
      font-weight: 700;
    }
  </style>
</head>
<body class="min-h-screen p-4">
  <header class="border-b border-slate-700/60 mb-6">
    <div class="max-w-4xl mx-auto px-4 py-4 flex flex-wrap items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-white">Monitor de Cocina</h1>
        <p class="text-sm text-slate-400">Plato a Plato Host</p>
      </div>
      <div class="flex items-center gap-4 text-sm">
        <span class="px-3 py-1 rounded-full bg-slate-800">
          <span class="badge" id="clientesLabel">0</span>
          <span class="hidden sm:inline">cliente(s)</span>
        </span>
        <span class="text-slate-400" id="estadoLabel">ESPERA</span>
      </div>
    </div>
  </header>

  <main class="max-w-4xl mx-auto px-4">
    <div class="text-center text-sm text-slate-400 mb-4">
      ws://<span id="hostLabel">127.0.0.1</span>:8000/ws/cocina
    </div>

    <div id="ordenContainer" class="flex flex-wrap justify-center gap-4">
      <div class="card w-80 text-center">
        <p class="text-xs uppercase tracking-widest text-slate-500 mb-2">Esperando orden</p>
        <p class="text-2xl font-bold text-slate-400">Nueva orden</p>
        <p class="text-xs text-slate-500 mt-2">Esperando transmisión via WebSocket</p>
      </div>
    </div>
  </main>

  <audio id="beep"></audio>

  <script>
    (function () {
      // El navegador se conecta al WebSocket del servidor para recibir eventos de
      // estado y la llegada de nuevas órdenes. La pantalla de cocina es un cliente
      // ligero que no persiste información propia: todo se re-renderiza desde los
      // mensajes emitidos por el backend.
      const host = location.hostname || "127.0.0.1";
      const protocol = location.protocol === "https:" ? "wss://" : "ws://";
      const wsUrl = protocol + host + ":8000/ws/cocina";
      const labelClientes = document.getElementById("clientesLabel");
      const labelEstado = document.getElementById("estadoLabel");
      const hostLabel = document.getElementById("hostLabel");
      const container = document.getElementById("ordenContainer");
      const beep = document.getElementById("beep");
      let socket = null;

      // El sonido ayuda a avisar al personal cuando llega una nueva orden sin
      // fijarse en la pestaña del monitor.
      function playBeep() {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        gain.gain.value = 0.3;
        osc.start();
        osc.stop(ctx.currentTime + 0.15);
      }

      // Se encarga de abrir la conexión WebSocket y reintentar si el servidor está
      // aún arrancando o se cae inesperadamente. La lógica es sencilla: si llega un
      // mensaje de estado cambia el contador; si llega una nueva orden, se renderiza
      // la tarjeta correspondiente.
      function connect(retryCount) {
        retryCount = retryCount || 0;
        hostLabel.textContent = host;
        labelClientes.textContent = "0";
        labelEstado.textContent = "ESPERA";
        try {
          socket = new WebSocket(wsUrl);
        } catch (err) {
          setTimeout(() => connect(retryCount + 1), 3000);
          return;
        }
        socket.onopen = () => {
          labelEstado.textContent = "CONECTADO";
        };
        socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.evento === "ESTADO_CONEXION") {
            labelClientes.textContent = data.datos.clientes_activos;
            return;
          }
          if (data.evento === "NUEVA_ORDEN") {
            playBeep();
            renderOrder(data.datos);
          }
        };
        socket.onclose = () => {
          labelEstado.textContent = "RECONECTANDO";
          setTimeout(() => connect(retryCount + 1), 3000);
        };
        socket.onerror = () => socket.close();
      }

      // Genera la tarjeta visual para una orden nueva o reemplaza una existente con
      // el mismo id. Esto evita duplicados si el mismo pedido llega dos veces por
      // reintentos o recargas del cliente.
      function renderOrder(datos) {
        const { id_venta, caja, total_items, items } = datos;
        const existing = document.getElementById(`orden-${id_venta}`);

        if (existing) {
          existing.remove();
        }

        const itemRows = items.map((item) => `
          <div class="border-b border-slate-700/80 pb-2 mb-2 last:border-b-0 last:pb-0 last:mb-0">
            <p class="text-lg font-semibold text-white">${item.nombre}</p>
            <p class="text-sm text-slate-400">Cantidad: <span class="font-bold text-white">${item.cantidad}</span></p>
            ${item.observacion ? `<p class="text-xs text-slate-400 mt-2">Obs: ${item.observacion}</p>` : ""}
          </div>
        `).join("");

        const tarjeta = document.createElement("div");
        tarjeta.className = "card preparando text-left w-80";
        tarjeta.id = `orden-${id_venta}`;
        tarjeta.innerHTML = `
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs uppercase tracking-widest text-slate-500">Pedido ${id_venta}</span>
            <span class="px-2 py-0.5 rounded-full bg-slate-700 text-xs">${caja}</span>
          </div>
          <div class="space-y-2 mb-3">${itemRows}</div>
          <p class="text-xs text-slate-500 mt-2">Total items: ${total_items}</p>
          <div class="mt-4 flex justify-end gap-2">
            <button type="button" class="btn-listo text-sm px-3 py-1.5 rounded-lg">Listo</button>
          </div>
        `;

        const botonListo = tarjeta.querySelector(".btn-listo");
        botonListo.addEventListener("click", () => marcarListo(id_venta));

        container.appendChild(tarjeta);

        const placeholder = container.querySelector(".placeholder-order");
        if (placeholder) placeholder.remove();
      }

      // Cuando el cocinero confirma un pedido, la tarjeta cambia su estilo al estado
      // "listo" y luego se elimina del DOM con una pequeña demora para dar feedback
      // visual. Si ya no queda ninguna orden, se vuelve a mostrar el placeholder.
      function marcarListo(idVenta) {
        const tarjeta = document.getElementById(`orden-${idVenta}`);
        if (!tarjeta) return;

        tarjeta.classList.remove("preparando");
        tarjeta.classList.add("listo");

        setTimeout(() => {
          tarjeta.remove();
          if (!container.children.length) {
            container.innerHTML = `
              <div class="card placeholder-order w-80 text-center">
                <p class="text-xs uppercase tracking-widest text-slate-500 mb-2">Esperando orden</p>
                <p class="text-2xl font-bold text-slate-400">Nueva orden</p>
                <p class="text-xs text-slate-500 mt-2">Esperando transmisión via WebSocket</p>
              </div>
            `;
          }
        }, 350);
      }

      connect();
    })();
  </script>
</body>
</html>
"""