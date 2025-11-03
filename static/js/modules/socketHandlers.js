/* ===================================================================
   MÓDULO DE MANEJADORES DE SOCKET.IO (socketHandlers.js)
   Define todos los listeners para eventos del servidor.
   =================================================================== */

import { show, setLoading, showNotification, manejarInvitacion, showAchievementNotification, playSound, escapeHTML } from './utils.js';
import { updateProfileUI, fetchAndUpdateUserProfile } from './auth.js';
import { updateWaitingRoomUI, appendLobbyChatMessage, loadTopPlayers } from './lobby.js';
import { actualizarEstadoJuego, renderEventos, agregarAlLog, appendGameChatMessage, mostrarModalFinJuego } from './gameUI.js';
import { displayPerkOffer, handlePerkActivated, updatePerkPrices } from './perks.js';
import { appendPrivateMessage, updateSocialNotificationIndicator } from './social.js';

// Referencias a estado/elementos/funciones que se pasarán desde main.js
// --- DECLARACIONES DE VARIABLES DEL MÓDULO (Solo una vez) ---
let _socket = null;
let _screens = null;
let _loadingElement = null;
let _notificacionesContainer = null;
let _state = null;
let _currentUser = null; 
let _idSala = null;      
let _estadoJuego = null; 
let _mapaColores = null; 
let _habilidadUsadaTurno = null;
let _gameAnimations = null;
let btnLanzarDado = null;
let btnMostrarHab = null;

// Referencias DOM específicas necesarias aquí
let codigoSalaActualDisplay = null;
let resultadoDadoDisplay = null;
let jugadoresEstadoDisplay = null; // Para animaciones
let modalPrivateChatElement = null;
let privateChatSendBtn = null;
let modalSocialElement = null;
let socialFriendsListDisplay = null; // Para reactivar botón de invitar
let modalFinalElement = null;
let btnNuevaPartida = null;
let btnVolverLobby = null;
let rematchWaitingMsg = null;

/**
 * Configura todos los listeners de Socket.IO.
 * @param {object} socketInstance - La instancia de Socket.IO.
 * @param {object} screenElements - Referencias a los elementos de pantalla.
 * @param {HTMLElement} loadingEl - Referencia al elemento loading.
 * @param {HTMLElement} notificationEl - Referencia al contenedor de notificaciones.
 * @param {object} stateRefs - Objeto con referencias mutables { currentUser, idSala, estadoJuego, mapaColores, habilidadUsadaTurno }.
 */
export function setupSocketHandlers(socketInstance, screenElements, loadingEl, notificationEl, stateRefs, gameAnimationsInstance) {
    _socket = socketInstance;
    _screens = screenElements;
    _loadingElement = loadingEl;
    _notificacionesContainer = notificationEl;

    // Asignar referencias mutables
    _state = stateRefs;
    _currentUser = stateRefs.currentUser;
    _idSala = stateRefs.idSala;
    _estadoJuego = stateRefs.estadoJuego;
    _mapaColores = stateRefs.mapaColores;
    _habilidadUsadaTurno = stateRefs.habilidadUsadaTurno;
    _gameAnimations = gameAnimationsInstance;

    // Cachear elementos DOM necesarios para los handlers
    codigoSalaActualDisplay = document.getElementById("codigo-sala-actual");
    resultadoDadoDisplay = document.getElementById("resultado-dado");
    jugadoresEstadoDisplay = document.getElementById("jugadores-estado");
    btnLanzarDado = document.getElementById("btn-lanzar-dado"); 
    btnMostrarHab = document.getElementById("btn-mostrar-habilidades");
    modalPrivateChatElement = document.getElementById("modal-private-chat");
    privateChatSendBtn = document.getElementById("private-chat-send");
    modalSocialElement = document.getElementById("modal-social");
    socialFriendsListDisplay = document.getElementById("social-friends-list");
    modalFinalElement = document.getElementById("modal-final");
    btnNuevaPartida = document.getElementById("btn-nueva-partida");
    btnVolverLobby = document.getElementById("btn-volver-lobby");
    rematchWaitingMsg = document.getElementById('rematch-waiting-msg');


    // --- Log General ---
    _socket.onAny((eventName, ...args) => {
        // Evitar log excesivo de pings/heartbeats
        if (!['pong', 'ping', 'presence_heartbeat'].includes(eventName)) {
            console.log(`---> Evento Socket Recibido: ${eventName}`, args);
        }
    });

    // --- Conexión y Errores ---
    _socket.on("connect", () => {
        setLoading(false, _loadingElement);
        console.log("Socket conectado.");
        if (_state.currentUser && _state.currentUser.username) { 
            console.log(`Reconectado como ${_state.currentUser.username}. Re-autenticando socket...`); 
            _socket.emit('authenticate', { username: _state.currentUser.username });
        } else {
            console.log("Conectado, esperando autenticación (login).");
        }
    });

    _socket.on("disconnect", (reason) => {
        setLoading(true, _loadingElement);
        showNotification(`Desconectado: ${reason}. Intentando reconectar...`, _notificacionesContainer, "error", 10000);
        // Podrías intentar limpiar el estado del juego aquí si es necesario
    });

    _socket.on("conectado", () => { // Confirmación inicial del servidor
        setLoading(false, _loadingElement);
        console.log("Conexión con servidor establecida.");
    });

     _socket.on('authenticated', (data) => {
        console.log(`Socket autenticado como: ${data.username}`);
        // Podríamos pedir estado social aquí si es necesario al (re)conectar
    });

    _socket.on("error", (data) => {
        setLoading(false, _loadingElement);
        showNotification(data.mensaje || "Error del servidor", _notificacionesContainer, "error");
    });

    _socket.on("precios_perks_actualizados", (costos) => {
        updatePerkPrices(costos);
    });

    // --- Lobby y Sala de Espera ---
    _socket.on("sala_creada", (data) => {
        setLoading(false, _loadingElement);
        _idSala.value = data.id_sala; // Actualiza el estado global
        if(codigoSalaActualDisplay) codigoSalaActualDisplay.textContent = data.id_sala;
        show('waiting', _screens);
        _socket.emit("obtener_estado_sala", { id_sala: data.id_sala }); // Pedir estado inicial
    });

    _socket.on("unido_exitoso", (data) => {
        setLoading(false, _loadingElement);
        _idSala.value = data.id_sala;
        if(codigoSalaActualDisplay) codigoSalaActualDisplay.textContent = data.id_sala;
        show('waiting', _screens);
        _socket.emit("obtener_estado_sala", { id_sala: data.id_sala });
    });

    _socket.on("jugador_unido", (data) => {
        updateWaitingRoomUI(data); // Actualiza contador, lista, botón iniciar, log
    });

    _socket.on("jugador_desconectado", (data) => {
        updateWaitingRoomUI(data); // Actualiza UI
        showNotification(data.mensaje_desconexion || `${escapeHTML(data.jugador_nombre)} se desconectó.`, _notificacionesContainer, "warning");
        // No necesita pedir estado, updateWaitingRoomUI ya lo hace
    });

    _socket.on("sala_abandonada", (data) => {
        setLoading(false, _loadingElement);
        _idSala.value = null; // Limpia estado global
        // _currentUser sigue siendo el mismo
        Object.assign(_estadoJuego, {}); // Limpia estado del juego
        _habilidadUsadaTurno.value = false;
        show("lobby", _screens); // Vuelve al lobby
        loadTopPlayers(); // Recarga top players por si acaso
        if (data.message) showNotification(data.message, _notificacionesContainer, data.success ? "info" : "error");
    });

    _socket.on("estado_sala", (data) => { // Respuesta a 'obtener_estado_sala'
        updateWaitingRoomUI(data);
    });

    _socket.on("nuevo_mensaje", (data) => { // Chat de lobby o juego
        const isInWaiting = _screens.waiting?.classList.contains("active");
        if (isInWaiting) {
            appendLobbyChatMessage(data);
        } else {
            appendGameChatMessage(data);
        }
    });

    // --- Juego Activo ---
    _socket.on("juego_iniciado", (estadoInicial) => {
        playSound('GameStart', 0.5);
        if (modalSocialElement) modalSocialElement.style.display = "none"; // Cierra modal social
        show("game", _screens);
        _mapaColores.value = estadoInicial.colores_jugadores || {}; // Guarda mapa de colores
        console.log("Mapa de colores recibido:", _mapaColores.value);
        actualizarEstadoJuego(estadoInicial); 
        showNotification("¡La partida ha comenzado!", _notificacionesContainer, "success");
    });

    _socket.on("paso_1_resultado_movimiento", (data) => {
        try {
            if (btnLanzarDado) btnLanzarDado.disabled = true;
            if (btnMostrarHab) btnMostrarHab.disabled = true;
            const btnPerks = document.getElementById('btn-abrir-perks');
            if (btnPerks) btnPerks.disabled = true;

            const jugadorNombre = data.jugador;
            const res = data.resultado;
            const eventosPaso1 = res.eventos || [];
            
            renderEventos(eventosPaso1); 
            
            // Lógica del dado 
            if (res.dado !== undefined) {
                if (_gameAnimations && _gameAnimations.isEnabled) { 
                    _gameAnimations.animateDiceRoll(resultadoDadoDisplay, res.dado, () => { 
                        if (resultadoDadoDisplay) resultadoDadoDisplay.textContent = `🎲 ${res.dado}`;
                    });
                } else {
                    if (resultadoDadoDisplay) resultadoDadoDisplay.textContent = `🎲 ${res.dado}`;
                }
            } else {
                if (resultadoDadoDisplay) resultadoDadoDisplay.textContent = ""; 
            }
            
            if (res.meta_alcanzada) {
                console.log("Animación Paso 1: Meta alcanzada. No se envía Paso 2.");
                if (_gameAnimations && _gameAnimations.isEnabled) { 
                    _gameAnimations.animatePlayerMove(res.pos_inicial, res.pos_final, jugadorNombre, () => {});
                }
                return; 
            }

            if (_gameAnimations && _gameAnimations.isEnabled) {
                _gameAnimations.animatePlayerMove(
                    res.pos_inicial,
                    res.pos_final,
                    jugadorNombre,
                    () => {
                        // La animación SÓLO reproduce el sonido al terminar
                        playOptimisticSound(res.pos_final, _estadoJuego);
                    } 
                );
            } else {  
                // Si no hay animaciones, actualiza el tablero manualmente
                playOptimisticSound(res.pos_final, _estadoJuego);
            }

            if (_state.currentUser && jugadorNombre === _state.currentUser.username) {
                console.log("Soy yo (el que movió), avisando al servidor (paso_2_terminar_movimiento) INMEDIATAMENTE...");
                _socket.emit('paso_2_terminar_movimiento', { id_sala: _idSala.value });
            }

        } catch (error) {
            console.error("!!! ERROR DENTRO DEL LISTENER 'paso_1_resultado_movimiento':", error);
            agregarAlLog(`Error del cliente: ${error.message}`);
        }
    });

    _socket.on("paso_2_resultado_casilla", (data) => {
        try {
        const estado_nuevo = data.estado_juego;
        const eventos_paso_2 = data.eventos || [];

        // Encontrar al jugador que acaba de terminar su Paso 1
        const jugador_nombre_actual = _estadoJuego.turno_actual;
        
        if (!jugador_nombre_actual || !estado_nuevo) {
            // No hay turno actual o estado, solo actualizar y salir
            actualizarEstadoJuego(estado_nuevo);
            renderEventos(eventos_paso_2);
            return;
        }

        // Encontrar la posición 'vieja' (donde aterrizó el dado) y 'nueva' (después del teleporter)
        const jugador_viejo = _estadoJuego.jugadores.find(j => j.nombre === jugador_nombre_actual);
        const jugador_nuevo = estado_nuevo.jugadores.find(j => j.nombre === jugador_nombre_actual);

        if (!jugador_viejo || !jugador_nuevo) {
            // No se encontró al jugador, solo actualizar
            actualizarEstadoJuego(estado_nuevo);
            renderEventos(eventos_paso_2);
            return;
        }

        const pos_vieja = jugador_viejo.posicion;
        const pos_nueva = jugador_nuevo.posicion;
        
        // Reproducir efectos visuales (shake) y sonidos de colisión
        eventos_paso_2.forEach(evento => {
            if (typeof evento !== 'string') return;
            const lowerEvent = evento.toLowerCase();
            if (lowerEvent.includes("trampa") || lowerEvent.includes("💀")) { 
                if(_gameAnimations) _gameAnimations.shakeBoard(); 
            }
            else if (lowerEvent.includes("colisión") || lowerEvent.includes("💥")) { 
                playSound('Collision', 0.2); 
                if(_gameAnimations) _gameAnimations.shakeBoard(); 
            }
        });
        
        // Comprobar si hubo un movimiento forzado (Teleport, Rebote, Intercambio, etc.)
        if (pos_vieja !== pos_nueva && pos_nueva < 75) {
            console.log(`--- Movimiento encadenado detectado (Paso 2): ${pos_vieja} -> ${pos_nueva}. Animando...`);
            
            // Reproducir sonido optimista para la *nueva* casilla
            playOptimisticSound(pos_nueva, estado_nuevo); 

            if (_gameAnimations && _gameAnimations.isEnabled) {
                // ¡Animar el "salto"!
                _gameAnimations.animatePlayerMove(
                    pos_vieja,
                    pos_nueva,
                    jugador_nombre_actual,
                    () => {
                        // Cuando la animación del teleporter TERMINA,
                        // actualizar la UI al estado final.
                        actualizarEstadoJuego(estado_nuevo);
                        renderEventos(eventos_paso_2);
                    }
                );
            } else {
                // Animaciones desactivadas, solo actualizar
                actualizarEstadoJuego(estado_nuevo);
                renderEventos(eventos_paso_2);
            }
        } else {
            // No hubo movimiento extra (ej. cayó en +70), solo actualizar.
            actualizarEstadoJuego(estado_nuevo);
            renderEventos(eventos_paso_2);
        }

    } catch (error) {
        console.error("!!! ERROR DENTRO DEL LISTENER 'paso_2_resultado_casilla':", error);
        agregarAlLog(`Error del cliente: ${error.message}`);
    }
});

    _socket.on("habilidad_usada", (data) => { // Habilidades públicas
        if (!_state || !_state.currentUser || !_state.currentUser.username) {
            console.warn("Habilidad usada ignorada: Estado del usuario no disponible.");
            return; 
        }

        if (data.resultado?.exito) {
            _habilidadUsadaTurno.value = (data.jugador === _state.currentUser.username); 
        }

        actualizarEstadoJuego(data.estado_juego);
        renderEventos(data.resultado?.eventos);

        // Animación 
        if (window.GameAnimations && data.habilidad && data.resultado?.exito && jugadoresEstadoDisplay) {
            const playerElement = Array.from(jugadoresEstadoDisplay.children).find(el => el.textContent.includes(data.jugador));
            if (playerElement) window.GameAnimations.animateAbilityUse(data.habilidad.tipo || "magic", playerElement);
        }
    });

     _socket.on("habilidad_usada_privada", (data) => { 
        if (data.resultado?.exito) {
            _habilidadUsadaTurno.value = (data.jugador === _state.currentUser?.username);
        }
        actualizarEstadoJuego(data.estado_juego);
        renderEventos(data.resultado?.eventos); // Muestra el evento solo a mí

         // Animación (tipo 'stealth')
        if (window.GameAnimations && data.habilidad && data.resultado?.exito && jugadoresEstadoDisplay) {
            const playerElement = Array.from(jugadoresEstadoDisplay.children).find(el => el.textContent.includes(data.jugador));
            if (playerElement) window.GameAnimations.animateAbilityUse("stealth", playerElement);
        }
    });

    _socket.on("estado_juego_actualizado", (data) => { // Forzar actualización (ej. post-perk)
        if (data.estado_juego) {
            actualizarEstadoJuego(data.estado_juego);
        }
        if (data.eventos_recientes) {
            renderEventos(data.eventos_recientes);
        }
    });

    // --- Perks y Logros ---
    _socket.on("oferta_perk", (data) => {
        if (document.getElementById("modal-perks")?.style.display === 'flex') {
            displayPerkOffer(data);
        } else {
             console.warn("Oferta de perk recibida pero modal cerrado.");
             // Podríamos guardar la oferta pendiente aquí si fuera necesario reabrirla
        }
    });

    _socket.on("perk_activado", (data) => {
        handlePerkActivated(data); // Llama a la función del módulo perks
    });

    _socket.on("achievements_unlocked", (data) => {
        if (data.achievements?.length > 0) {
            data.achievements.forEach(ach => {
                if(ach) showAchievementNotification(ach, _notificacionesContainer);
            });
            // Actualizar perfil en segundo plano para reflejar XP/Nivel
            if (_currentUser.value) fetchAndUpdateUserProfile(_currentUser.value.username);
        }
    });

    // --- Fin de Juego y Revancha ---
    _socket.on("juego_terminado", (data) => {
        mostrarModalFinJuego(data);
        Object.assign(_estadoJuego, {}); // Limpia estado del juego local
        if (_habilidadUsadaTurno) _habilidadUsadaTurno.value = false;
    });

    _socket.on('revancha_lista', (data) => {
        console.log("Revancha lista, uniéndose a nueva sala:", data.nueva_id_sala);
        if (modalFinalElement) modalFinalElement.style.display = 'none'; // Ocultar modal final

        // Restaurar botones del modal final
        if (btnNuevaPartida) { btnNuevaPartida.disabled = false; btnNuevaPartida.textContent = "🎮 Nueva Partida"; }
        if (btnVolverLobby) btnVolverLobby.disabled = false;
        const waitingMsg = document.getElementById('rematch-waiting-msg');
        if(waitingMsg) waitingMsg.remove();

        // Verifica que _state y _state.idSala existan antes de asignar el nuevo ID
        if (_state && _state.idSala) {
            _state.idSala.value = data.nueva_id_sala; // Actualiza el valor dentro del objeto 'state'
            console.log(`ID de sala (revancha) actualizado a: ${_state.idSala.value}`);
        } else {
            // Informa si algo anda mal
            console.error("Error en 'revancha_lista': _state o _state.idSala no están definidos correctamente. No se pudo actualizar idSala.");
            showNotification("Error al procesar la revancha.", _notificacionesContainer, "error");
            return; // Salir si no podemos actualizar el ID
        }

        // Actualiza la UI con el nuevo ID
        if(codigoSalaActualDisplay) codigoSalaActualDisplay.textContent = data.nueva_id_sala;

        // Muestra la pantalla de espera
        show("waiting", _screens);

        // Pide el estado de la nueva sala
        _socket.emit("obtener_estado_sala", { id_sala: data.nueva_id_sala });

        // Muestra notificación de éxito
        showNotification("¡Revancha lista! Esperando jugadores...", _notificacionesContainer, "success");
    });

    _socket.on('revancha_cancelada', (data) => {
        let currentSalaId = null;
        if (_state && _state.idSala) {
            currentSalaId = _state.idSala.value; 
        } else {
            console.warn("Revancha cancelada recibida, pero _state o _state.idSala no están definidos.");
        }

        // Notificación y limpieza de UI
        showNotification(data.mensaje || "La revancha fue cancelada.", _notificacionesContainer, "warning");
        console.log("Revancha cancelada:", data.mensaje);

        // Habilitar botones de nuevo
        if (btnNuevaPartida) { btnNuevaPartida.disabled = false; btnNuevaPartida.textContent = "🎮 Nueva Partida"; }
        if (btnVolverLobby) btnVolverLobby.disabled = false;

        // Busca el mensaje de espera por ID
        const waitingMsg = document.getElementById('rematch-waiting-msg');
        if(waitingMsg) waitingMsg.remove();
    });

    // --- Social y Chat ---
    _socket.on("new_friend_request", (data) => {
        showNotification(`👥 ${escapeHTML(data.from_user)} te envió una solicitud.`, _notificacionesContainer, "info", 5000);
        updateSocialNotificationIndicator(true);
        // Podríamos recargar la tab de requests si está abierta
    });

    _socket.on("friend_status_update", (data) => {
        const friendName = escapeHTML(data.username || data.friend);
        let message = `👤 Estado de ${friendName} actualizado.`;
        if (data.type === "accepted") { message = `🎉 ¡Ahora eres amigo de ${friendName}!`; }
        showNotification(message, _notificacionesContainer, "info");
        // Podríamos recargar la tab de amigos si está abierta
    });

    _socket.on("new_private_message", (data) => {
        if (!data) return;
        const privateChatIsOpen = modalPrivateChatElement?.style.display === 'flex';
        const isChattingWithSender = document.getElementById('chat-with-username')?.textContent === data.sender;

        if (privateChatIsOpen && isChattingWithSender) {
            appendPrivateMessage(data); // Añade al chat abierto
            _socket.emit('mark_chat_as_read', { sender: data.sender });
        } else {
            showNotification(`💬 Nuevo mensaje de ${escapeHTML(data.sender)}`, _notificacionesContainer, "info", 5000);
            updateSocialNotificationIndicator(true); // Marca botón social
        }
    });

    _socket.on("message_sent_confirm", (data) => { // Confirmación de MI mensaje enviado
        const privateChatIsOpen = modalPrivateChatElement?.style.display === 'flex';
        const isChattingWithRecipient = document.getElementById('chat-with-username')?.textContent === data.recipient;

        if (privateChatIsOpen && isChattingWithRecipient) {
            appendPrivateMessage(data); // Añade mi mensaje a mi ventana
        }
        if (privateChatSendBtn) { // Reactiva botón
            privateChatSendBtn.disabled = false;
            privateChatSendBtn.textContent = "Enviar";
        }
    });

    _socket.on("invite_sent_confirm", (data) => {
        showNotification(`Invitación enviada a ${escapeHTML(data.to)}.`, _notificacionesContainer, "success");
        // Reactivar botón de invitar en modal social si está abierto
        if (modalSocialElement?.style.display === 'flex' && socialFriendsListDisplay) {
            const inviteButton = socialFriendsListDisplay.querySelector(`.social-list-item[data-username="${data.to}"] .btn-invite-friend`);
            if (inviteButton) {
                inviteButton.disabled = false;
                inviteButton.textContent = "🎮"; // Restaurar icono
            }
        }
    });

    _socket.on('room_invite', (data) => { // Recibo una invitación
        if (!_state) {
        console.warn("Invitación ignorada: Objeto de estado (_state) no inicializado.");
        return;
        }   
        // Pasamos todas las dependencias necesarias a manejarInvitacion
        manejarInvitacion(data, _notificacionesContainer, _socket,
                        _state, // Pasa la referencia al objeto _state
                        setLoading, show, _screens);
    });


    console.log("Socket handlers configurados.");
} 
// Fin de setupSocketHandlers
/**
 * Reproduce un sonido "optimista" basado en el contenido de la casilla
 * ANTES de que el servidor confirme el efecto.
 */
function playOptimisticSound(posFinal, estadoJuego) {
    if (!estadoJuego || !estadoJuego.tablero) return;

    const casillaData = estadoJuego.tablero[posFinal];
    if (!casillaData) return; // Casilla vacía

    const tipoCasilla = casillaData.casilla_especial?.tipo;
    const valorEnergia = casillaData.energia;

    // Prioridad 1: Casillas Especiales
    if (tipoCasilla === 'trampa') {
        playSound('LandOnTrap', 0.2);
    } else if (tipoCasilla === 'tesoro') {
        playSound('LandOnTreasure', 0.2);
    } else if (tipoCasilla === 'teletransporte' || tipoCasilla === 'intercambio' || tipoCasilla === 'retroceso_estrategico') {
        playSound('Teleport', 0.3);
    }
    // Prioridad 2: Packs de Energía
    else if (valorEnergia > 0) {
        playSound('LandOnTreasure', 0.2); // Sonido positivo
    } else if (valorEnergia < 0) {
        playSound('LandOnTrap', 0.2); // Sonido negativo
    }
    // (No reproducir sonido si la casilla está vacía)
}