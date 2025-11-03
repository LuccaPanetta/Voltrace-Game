/* ===================================================================
   MÓDULO DE UI DEL JUEGO (gameUI.js)
   Renderiza el tablero, estado de jugadores, log y maneja interacciones del juego.
   =================================================================== */

import { escapeHTML, playSound } from './utils.js';
// Necesitaremos la referencia a GameAnimations si la usamos aquí
// import { GameAnimations } from '../animations.js'; // Asumiendo que animations.js también se modulariza

// Referencias DOM
let eventosListaDisplay, jugadoresEstadoDisplay, rondaActualDisplay, turnoJugadorDisplay;
let btnLanzarDado, btnMostrarHab, tableroElement, resultadoDadoDisplay;
let chatMensajesJuegoDisplay, mensajeJuegoInput, btnEnviarMensajeJuego;
let listaHabDisplay, modalHabElement, btnCerrarHab;
let modalFinalElement, resultadosFinalesDisplay, btnNuevaPartida, btnVolverLobby;
let guiaDrawer, guiaToggleBtn;

// Referencias a estado/funciones externas
let _socket = null;
let _currentUser = null;
let _idSala = null;
let _estadoJuego = null; // Referencia mutable al estado del juego
let _mapaColores = null; // Referencia mutable al mapa de colores
let _habilidadUsadaTurno = { value: false }; // Objeto para pasar por referencia
let _openPerkModalFunc = null; // Referencia a la función para abrir perks
let _state = null;

/**
 * Inicializa el módulo de UI del juego.
 * @param {object} socketRef - Instancia de Socket.IO.
 * @param {object} stateRef - Referencia al objeto 'state' global de main.js. <--- PARÁMETRO CORRECTO
 * @param {object} idSalaRef - Referencia al objeto idSala ({ value: ... }).
 * @param {object} estadoJuegoRef - Referencia al objeto estadoJuego.
 * @param {object} mapaColoresRef - Referencia al objeto mapaColores.
 * @param {object} habilidadUsadaRef - Referencia al objeto habilidadUsadaTurno ({ value: ... }).
 * @param {function} openPerksFuncRef - Referencia a la función para abrir el modal de perks.
 */
export function initGameUI(socketRef, stateRef, idSalaRef, estadoJuegoRef, mapaColoresRef, habilidadUsadaRef, openPerksFuncRef) {
    _socket = socketRef;
    _state = stateRef; 
    _idSala = idSalaRef;
    _estadoJuego = estadoJuegoRef;
    _mapaColores = mapaColoresRef;
    _habilidadUsadaTurno = habilidadUsadaRef;
    _openPerkModalFunc = openPerksFuncRef;

    // Cachear elementos DOM (Esto debe ir DESPUÉS de asignar _state, _socket, etc.)
    eventosListaDisplay = document.getElementById("eventos-lista");
    jugadoresEstadoDisplay = document.getElementById("jugadores-estado");
    rondaActualDisplay = document.getElementById("ronda-actual");
    turnoJugadorDisplay = document.getElementById("turno-jugador");
    btnLanzarDado = document.getElementById("btn-lanzar-dado");
    btnMostrarHab = document.getElementById("btn-mostrar-habilidades");
    tableroElement = document.getElementById("tablero");
    resultadoDadoDisplay = document.getElementById("resultado-dado");
    chatMensajesJuegoDisplay = document.getElementById("chat-juego-mensajes");
    mensajeJuegoInput = document.getElementById("mensaje-juego-input");
    btnEnviarMensajeJuego = document.getElementById("btn-enviar-mensaje-juego");
    listaHabDisplay = document.getElementById("habilidades-lista");
    modalHabElement = document.getElementById("modal-habilidades");
    btnCerrarHab = document.getElementById("btn-cerrar-habilidades");
    modalFinalElement = document.getElementById("modal-final");
    resultadosFinalesDisplay = document.getElementById("resultados-finales");
    btnNuevaPartida = document.getElementById("btn-nueva-partida");
    btnVolverLobby = document.getElementById("btn-volver-lobby");
    guiaDrawer = document.getElementById("guia-partida-drawer");
    guiaToggleBtn = document.getElementById("guia-partida-toggle");

    // Asignar listeners
    btnLanzarDado?.addEventListener("click", handleLanzarDado);
    btnMostrarHab?.addEventListener("click", handleMostrarHabilidades);
    btnCerrarHab?.addEventListener("click", () => {
        playSound('OpenCloseModal', 0.2);
        if(modalHabElement) modalHabElement.style.display = 'none';
    });
    btnEnviarMensajeJuego?.addEventListener("click", handleEnviarMensajeJuego);
    mensajeJuegoInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleEnviarMensajeJuego(); });
    btnNuevaPartida?.addEventListener("click", handleSolicitarRevancha);
    btnVolverLobby?.addEventListener("click", handleVolverAlLobby);
    guiaToggleBtn?.addEventListener('click', handleToggleGuia);

    console.log("Módulo GameUI inicializado."); // Log para confirmar
}

// --- Manejadores de Eventos ---

function handleLanzarDado() {
    if (!_idSala || !_idSala.value || btnLanzarDado?.disabled) return;
    btnLanzarDado.disabled = true;
    playSound('Dice', 0.4);

    // Asumiendo que GameAnimations está disponible globalmente o importado
    if (window.GameAnimations && window.GameAnimations.isEnabled) {
        window.GameAnimations.animateAbilityUse("magic", btnLanzarDado);
    }
    _socket.emit("lanzar_dado", { id_sala: _idSala.value });
}

function handleMostrarHabilidades() {
    playSound('OpenCloseModal', 0.2);
    
    if (!_estadoJuego || !_state.currentUser || !_state.currentUser.username || !listaHabDisplay || !modalHabElement) return;

    const yo = _estadoJuego.jugadores?.find((j) => j.nombre === _state.currentUser.username);
    if (!yo || !yo.habilidades) return;

    listaHabDisplay.innerHTML = ""; 

    if (yo.habilidades.length === 0) {
        listaHabDisplay.innerHTML = '<p style="text-align:center; color: var(--muted);">No tienes habilidades.</p>';
    } else {
        yo.habilidades.forEach((h, originalIndex) => {
            const cooldownRestante = h.cooldown || 0;
            const item = document.createElement("div");
            item.className = "habilidad-item";
            if (cooldownRestante > 0) item.style.opacity = "0.6";

            const cooldownText = cooldownRestante > 0
                ? `<small style="color: var(--warning); font-weight: bold;"> (CD: ${cooldownRestante}t)</small>`
                : "";

            item.innerHTML = `
              <div>
                ${originalIndex + 1}. ${h.simbolo} <strong>${escapeHTML(h.nombre)}</strong>${cooldownText}
                <br>
                <small>${escapeHTML(h.descripcion)}</small>
              </div>`;

            const btn = document.createElement("button");
            btn.className = "btn-primary";
            btn.textContent = "Usar";
            btn.disabled = cooldownRestante > 0 || _habilidadUsadaTurno.value;

            if (_habilidadUsadaTurno.value && cooldownRestante === 0) {
                btn.title = "Ya usaste una habilidad este turno.";
            } else if (cooldownRestante > 0) {
                btn.title = `Disponible en ${cooldownRestante} turno(s).`;
            }

            btn.onclick = () => {
                if (btn.disabled) return;
                let objetivo = null;
                if (["Sabotaje", "Intercambio Forzado", "Retroceso", "Bloqueo Energético"].includes(h.nombre)) {
                    objetivo = prompt(`¿A quién quieres usar ${h.nombre}? Ingresa el nombre exacto:`);
                    if (objetivo === null) return;
                } else if (h.nombre === "Dado Perfecto") {
                    objetivo = prompt("¿Cuánto quieres avanzar? (1-6)?");
                    if (objetivo === null) return;
                }

                // Reproducir sonidos
                if (h.tipo === 'movimiento') playSound('MovementAbility', 0.3);
                else if (h.tipo === 'ofensiva') playSound('OffensiveAbility', 0.3);
                else if (h.tipo === 'defensiva' || h.tipo === 'control') playSound('DefensiveAbility', 0.3);
                else playSound('ClickMouse', 0.3);

                _socket.emit("usar_habilidad", {
                    id_sala: _idSala.value,
                    indice_habilidad: originalIndex + 1,
                    objetivo: objetivo,
                });
                if(modalHabElement) modalHabElement.style.display = "none";
            };

            item.appendChild(btn);
            listaHabDisplay.appendChild(item);
        });
    }
    if(modalHabElement) modalHabElement.style.display = "flex";
}

function handleEnviarMensajeJuego() {
    playSound('ClickMouse', 0.3);
    const msg = mensajeJuegoInput?.value.trim();

    if (!msg || !_idSala || !_idSala.value) return; 

    _socket.emit("enviar_mensaje", { id_sala: _idSala.value, mensaje: msg }); 

    if(mensajeJuegoInput) mensajeJuegoInput.value = "";
}

function handleSolicitarRevancha() {
    playSound('ClickMouse', 0.3);
    if (!btnNuevaPartida || !btnVolverLobby) return; // Asegurarse que los botones existen

    const idSalaActual = _idSala.value;

    btnNuevaPartida.disabled = true;
    btnVolverLobby.disabled = true;
    btnNuevaPartida.textContent = "Esperando...";

    if (idSalaActual) { 
        _socket.emit('solicitar_revancha', { 
            value: idSalaActual,
            username: _state.currentUser.username 
        });
        let waitingMsg = document.getElementById('rematch-waiting-msg');
        if (!waitingMsg && resultadosFinalesDisplay) {
            waitingMsg = document.createElement('p');
            waitingMsg.textContent = "Esperando respuesta de otros jugadores...";
            waitingMsg.style.textAlign = 'center';
            waitingMsg.style.marginTop = '10px';
            waitingMsg.id = 'rematch-waiting-msg';
            resultadosFinalesDisplay.appendChild(waitingMsg);
        }
    } else {
        const notifContainer = document.getElementById('notificaciones');
        let errorMsg = "Error: No se encontró la sala anterior.";
        if (!_state || !_state.currentUser || !_state.currentUser.username) {
            errorMsg = "Error: No se pudo identificar al usuario para la revancha.";
        }
        showNotification(errorMsg, notifContainer, "error");
        btnVolverLobby.disabled = false;
        btnNuevaPartida.textContent = "🎮 Nueva Partida";
    }
}

function handleVolverAlLobby() {
    playSound('ClickMouse', 0.3);
    if (typeof window.resetAndShowLobby === 'function') {
        window.resetAndShowLobby();
    } else {
        console.error("Función global resetAndShowLobby no encontrada.");
        // Fallback simple (puede no limpiar todo)
        if (modalFinalElement) modalFinalElement.style.display = "none";
        // Necesitamos acceso a _showFunc y _screens desde aquí, o una función global
         if (typeof window.showScreen === 'function') window.showScreen('lobby');
    }
}

function handleToggleGuia() {
    playSound('ClickMouse', 0.3);
    guiaDrawer?.classList.toggle('open');
}

// --- Funciones de Renderizado ---

/** Renderiza el panel de estado de jugadores. */
function updateJugadoresEstado(jugadores) {
    if (!jugadoresEstadoDisplay || !_mapaColores) return;

    const jugadoresViejos = _estadoJuego.jugadores || [];
    const mapaColores = _mapaColores.value || {};
    
    // Crear un mapa del estado viejo para comparaciones rápidas
    const viejosMap = new Map(jugadoresViejos.map(j => [j.nombre, j]));
    
    (nuevosJugadores || []).forEach((j) => {
        const viejoJ = viejosMap.get(j.nombre);
        const jugadorDOMId = `status-${j.nombre}`;
        const jugadorDOM = document.getElementById(jugadorDOMId);
        
        // Comparar: Si el jugador no existía o sus datos cambiaron...
        if (!viejoJ || !jugadorDOM || JSON.stringify(j) !== JSON.stringify(viejoJ)) {
            let efectosHtml = "";
            if (j.efectos_activos?.length > 0) {
                efectosHtml = '<span class="efectos-icons" style="margin-left: 8px; font-size: 0.9em; vertical-align: middle;">';
                j.efectos_activos.forEach(efecto => {
                    let icono = "?";
                    switch (efecto.tipo) {
                        case "pausa": icono = "⏸️"; break;
                        case "escudo": icono = "🛡️"; break;
                        case "turbo": icono = "⚡"; break;
                        case "multiplicador": icono = "✨"; break;
                        case "invisible": icono = "👻"; break;
                        case "barrera": icono = "🔮"; break;
                        case "doble_dado": icono = "🔄"; break;
                        case "bloqueo_energia": icono = "🚫"; break;
                        case "fase_activa": icono = "💨"; break;
                        case "sobrecarga_pendiente": icono = "🎲"; break;
                    }
                    const duracion = efecto.turnos > 1 ? ` (${efecto.turnos}t)` : "";
                    const tooltip = `${efecto.tipo.charAt(0).toUpperCase() + efecto.tipo.slice(1)}${duracion}`;
                    efectosHtml += `<span title="${tooltip}" style="margin-right: 3px;">${icono}</span>`;
                });
                efectosHtml += "</span>";
            }

            const color = mapaColores[j.nombre] || "#888";
            const colorSwatch = `<span class="color-swatch" style="background-color: ${color};"></span>`;
            
            const nuevoHTML = `
              <div style="display: flex; align-items: center; margin-bottom: 2px;">
                ${colorSwatch}
                <strong>${escapeHTML(j.nombre)}</strong>
                ${efectosHtml}
              </div>
              <div style="font-size: 0.9em;">
                <span style="color: var(--muted);">(Pos: ${j.posicion})</span>
                <span style="margin-left: 10px; color: ${j.puntaje > 200 ? 'var(--success)' : j.puntaje > 0 ? 'var(--warning)' : 'var(--danger)'};">E: ${j.puntaje}</span>
                <span style="margin-left: 10px; color: #f59e0b;">PM: ${j.pm || 0}</span>
                ${j.activo ? '' : '<span style="color: var(--danger); font-weight: bold; margin-left: 10px;">[X]</span>'}
              </div>`;
              
            if (jugadorDOM) {
                // Si el jugador ya existe en el DOM, solo actualiza su contenido
                jugadorDOM.innerHTML = nuevoHTML;
            } else {
                // Si es un jugador nuevo (improbable en mitad de partida, pero seguro)
                const div = document.createElement("div");
                div.id = jugadorDOMId;
                div.className = "player-status-item";
                div.style.cssText = "border-bottom: 1px solid #1f2937; padding: 8px 4px; margin-bottom: 5px;";
                div.innerHTML = nuevoHTML;
                jugadoresEstadoDisplay.appendChild(div);
            }
        }
        // Si no cambió, no hacemos NADA.
    });
}

/** Renderiza el tablero de juego. */
function updateTablero(tableroData) {
    if (!tableroElement || !_mapaColores || !_state || !_state.currentUser) {
        console.warn("updateTablero abortado: Faltan dependencias.");
        return; 
    }
    
    const tableroViejo = _estadoJuego.tablero || {};
    const mapaColores = _mapaColores.value || {};

    // Crear el tablero inicial si está vacío
    if (tableroElement.children.length === 0) {
        console.log("Creando tablero inicial...");
        for (let i = 1; i <= 75; i++) {
            const cell = document.createElement("div");
            cell.className = "casilla";
            cell.setAttribute("data-position", i);
            cell.innerHTML = `<div><small>#${i}</small></div><div class="c-esp"></div><div class="c-ene"></div><div class="fichas-container"></div>`;
            tableroElement.appendChild(cell);
        }
    }

    // Iterar sobre las casillas y actualizar solo las que cambiaron
    for (let pos = 1; pos <= 75; pos++) {
        const dataNueva = nuevoTablero[pos] || { jugadores: [], casilla_especial: null, energia: null };
        const dataVieja = tableroViejo[pos] || { jugadores: [], casilla_especial: null, energia: null };

        // Comparar
        if (JSON.stringify(dataNueva) === JSON.stringify(dataVieja)) {
            continue; // ¡Si la casilla no cambió, no hacer NADA!
        }

        // Si cambió, encontrar el DOM de esa casilla y actualizarla
        const cell = tableroElement.querySelector(`[data-position="${pos}"]`);
        if (!cell) continue; 
        
        // Referencias a los elementos internos de la casilla
        const fichasContainer = cell.querySelector(".fichas-container");
        const esp = cell.querySelector(".c-esp");
        const ene = cell.querySelector(".c-ene");

        // Actualizar Fichas
        if (fichasContainer) {
            fichasContainer.innerHTML = ""; // Limpiar solo las fichas
            if (dataNueva.jugadores?.length > 0) {
                dataNueva.jugadores.forEach((j) => {
                    if (j?.nombre) {
                        const ficha = document.createElement("div");
                        ficha.className = "ficha-jugador";
                        ficha.textContent = escapeHTML(j.nombre[0].toUpperCase());
                        ficha.style.backgroundColor = mapaColores[j.nombre] || "#888";
                        if (_state.currentUser && j.nombre === _state.currentUser.username) {
                            ficha.classList.add("mi-ficha");
                        }
                        fichasContainer.appendChild(ficha);
                    }
                });
            }
        }
        
        // Actualizar Casilla Especial
        if (esp) {
            if (dataNueva.casilla_especial) {
                esp.textContent = dataNueva.casilla_especial.simbolo;
                if (window.GameAnimations) window.GameAnimations.highlightSpecialTile(cell);
            } else {
                esp.textContent = "";
            }
        }

        // Actualizar Energía
        if (ene) {
            if (typeof dataNueva.energia === "number" && dataNueva.energia !== 0) {
                ene.textContent = dataNueva.energia > 0 ? `+${dataNueva.energia}` : `${dataNueva.energia}`;
            } else {
                ene.textContent = "";
            }
        }
    }
}

/** Añade un evento al log del juego. */
export function agregarAlLog(eventoMsg) {
    if (!eventosListaDisplay) return;
    const item = document.createElement("div");
    item.classList.add("log-item");

    let icono = "⚙️";
    const msgLower = String(eventoMsg).toLowerCase(); // Convertir a string por si acaso

    if (msgLower.startsWith("turno de") || msgLower.startsWith("➡️")) icono = "➡️";
    else if (msgLower.includes("usó") || msgLower.includes("habilidad") || msgLower.includes("✨") || msgLower.includes("activó")) icono = "✨";
    else if (msgLower.includes("sacó") || msgLower.includes("avanza") || msgLower.includes("retrocede") || msgLower.includes("mueve") || msgLower.includes("🎲")) icono = "🎲";
    else if (msgLower.includes("pierde") || msgLower.includes("trampa") || msgLower.includes("colisión") || msgLower.includes("peligro") || msgLower.includes("💀") || msgLower.includes("💥") || msgLower.includes("⚠️")) icono = "⚠️";
    else if (msgLower.includes("gana") || msgLower.includes("tesoro") || msgLower.includes("recoge") || msgLower.includes("💰") || msgLower.includes("💚 +")) icono = "💰";
    else if (msgLower.includes("protegido") || msgLower.includes("bloqueó") || msgLower.includes("🛡️") || msgLower.includes("esquivó") || msgLower.includes("invisible") || msgLower.includes("👻")) icono = "🛡️";

    // Asignar clases basadas en icono/palabras clave
    if (icono === "➡️") item.classList.add("log-turno");
    else if (icono === "✨") item.classList.add("log-habilidad");
    else if (icono === "🎲") item.classList.add("log-movimiento");
    else if (icono === "⚠️") item.classList.add("log-peligro");
    else if (icono === "💰") item.classList.add("log-positivo");
    else item.classList.add("log-sistema");

    item.innerHTML = `<span>${icono}</span> ${escapeHTML(eventoMsg)}`;
    eventosListaDisplay.appendChild(item);
    eventosListaDisplay.scrollTop = eventosListaDisplay.scrollHeight;
}

/** Renderiza la lista completa de eventos del turno. */
export function renderEventos(eventos) {
    if (!eventosListaDisplay) return;
    eventosListaDisplay.innerHTML = ""; // Limpiar antes
    (eventos || []).forEach(agregarAlLog);
}

/** Añade un mensaje al chat del juego. */
export function appendGameChatMessage(data) {
    if (!chatMensajesJuegoDisplay) return;
    const texto = `[${data.timestamp}] <strong>${escapeHTML(data.jugador)}</strong>: ${escapeHTML(data.mensaje)}`;
    const div = document.createElement("div");
    div.innerHTML = texto;
    div.style.marginBottom = "4px";
    chatMensajesJuegoDisplay.appendChild(div);
    chatMensajesJuegoDisplay.scrollTop = chatMensajesJuegoDisplay.scrollHeight;
}

/** Función principal que actualiza toda la UI del juego. */
export function actualizarEstadoJuego(estado) {
    // 1. Validar que todo lo necesario exista
    if (!jugadoresEstadoDisplay || !tableroElement || !rondaActualDisplay || !turnoJugadorDisplay || !btnLanzarDado || !btnMostrarHab || 
        !_state || !_state.currentUser || !_state.currentUser.username || 
        !estado
       ) {
        console.warn("actualizarEstadoJuego abortado: elementos DOM o estado no listos.");
        return; 
    }

    // Guardar el turno anterior (para resetear el flag de habilidad)
    const jugadorTurnoAnterior = _estadoJuego ? _estadoJuego.turno_actual : null;

    // RENDERIZAR PRIMERO (Comparar 'estado' (nuevo) con '_estadoJuego' (viejo))
    updateJugadoresEstado(estado.jugadores); 
    updateTablero(estado.tablero || {});

    // ACTUALIZAR EL ESTADO LOCAL DESPUÉS
    Object.assign(_estadoJuego, estado);

    // Renderizar componentes simples (esto siempre es rápido)
    rondaActualDisplay.textContent = estado.ronda ?? "-";
    turnoJugadorDisplay.textContent = escapeHTML(estado.turno_actual ?? "-");

    // Habilitar/deshabilitar botones
    const esMiTurno = estado.turno_actual === _state.currentUser.username;
    const juegoActivo = estado.estado === "jugando";

    // Resetear flag de habilidad si es un nuevo turno para mí
    if (esMiTurno && (estado.turno_actual !== jugadorTurnoAnterior)) {
        _habilidadUsadaTurno.value = false;
    }

    // Habilitar botones de acción
    btnLanzarDado.disabled = !esMiTurno || !juegoActivo;
    btnMostrarHab.disabled = !juegoActivo; 

    // Botón Comprar Perks (con el arreglo para que se re-habilite)
    const controlesTurno = document.querySelector(".controles-turno");
    let btnAbrirPerks = document.getElementById("btn-abrir-perks");
    
    if (esMiTurno && juegoActivo && controlesTurno && _openPerkModalFunc) {
        if (!btnAbrirPerks) {
            btnAbrirPerks = document.createElement("button");
            btnAbrirPerks.id = "btn-abrir-perks";
            btnAbrirPerks.className = "btn-secondary";
            btnAbrirPerks.textContent = "⭐ Comprar Perks";
            btnAbrirPerks.style.marginLeft = "10px";
            btnAbrirPerks.onclick = _openPerkModalFunc;
            btnLanzarDado.insertAdjacentElement('afterend', btnAbrirPerks);
        }
        btnAbrirPerks.style.display = "inline-block";
        // Re-habilita el botón (arreglo del bug anterior)
        btnAbrirPerks.disabled = false; 
    } else if (btnAbrirPerks) {
        // Oculta el botón si no es tu turno
        btnAbrirPerks.style.display = "none";
    }
}

/** Muestra el modal de fin de juego. */
export function mostrarModalFinJuego(data) {
    if (!modalFinalElement || !resultadosFinalesDisplay || !btnNuevaPartida || !btnVolverLobby || !_state || !_state.currentUser) {
        console.error("mostrarModalFinJuego abortado: Elementos DOM o referencia de estado (_state.currentUser) no encontrados.");
        return; 
    }

    const resultados = data.estadisticas_finales || [];
    const ganadorNombre = data.ganador; // Solo el nombre
    const yoSoyGanador = _state.currentUser.username === ganadorNombre;

    // Sonido y Animación
    if (yoSoyGanador) {
        playSound('GameWin', 0.7);
        if (window.GameAnimations && window.GameAnimations.isEnabled) {
            window.GameAnimations.celebrateVictory(_state.currentUser.username);
        }
    } else {
        playSound('GameLost', 0.6);
    }

    // Renderizar Resultados
    resultados.sort((a, b) => (b._puntaje_final_con_bonus || 0) - (a._puntaje_final_con_bonus || 0));
    resultadosFinalesDisplay.innerHTML = "";
    const tituloModal = modalFinalElement.querySelector(".modal-header h3");
    if (tituloModal) tituloModal.textContent = yoSoyGanador ? "🏆 ¡VICTORIA!" : "😥 Juego Terminado";

    resultados.forEach((g, i) => {
        const div = document.createElement("div");
        div.className = "resultado-jugador-final";
        const isWinner = g.nombre === ganadorNombre;
        let rankClass = '', rankIcon = i + 1;
        if (i === 0) { rankClass = 'rank-gold'; rankIcon = '🥇'; }
        else if (i === 1) { rankClass = 'rank-silver'; rankIcon = '🥈'; }
        else if (i === 2) { rankClass = 'rank-bronze'; rankIcon = '🥉'; }

        const puntajeFinal = g._puntaje_final_con_bonus ?? (g.puntaje_final || 0);

        div.innerHTML = `
          <div class="final-rank-row ${rankClass} ${isWinner ? 'winner-row' : ''}" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #374151;">
            <span style="font-weight: bold; font-size: 1.1em;">${rankIcon} ${escapeHTML(g.nombre)}</span>
            <span style="font-size: 1em; font-weight: 500;">
              Puntaje Final: <strong style="color: var(--success);">${puntajeFinal}</strong> (Pos: ${g.posicion || 'N/A'})
            </span>
          </div>`;
        resultadosFinalesDisplay.appendChild(div);
    });

    // Restaurar botones (por si se reabre el modal)
    btnNuevaPartida.disabled = false;
    btnNuevaPartida.textContent = "🎮 Nueva Partida";
    btnVolverLobby.disabled = false;
    const waitingMsg = document.getElementById('rematch-waiting-msg');
    if (waitingMsg) waitingMsg.remove();

    modalFinalElement.style.display = "flex";
}