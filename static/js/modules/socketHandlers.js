/* ===================================================================
   MÓDULO DE MANEJADORES DE SOCKET.IO (socketHandlers.js)
   =================================================================== */

import { show, setLoading, showNotification, manejarInvitacion, showAchievementNotification, playSound, escapeHTML } from './utils.js';
import { updateProfileUI, fetchAndUpdateUserProfile } from './auth.js';
import { updateWaitingRoomUI, appendLobbyChatMessage, loadTopPlayers } from './lobby.js';
import { actualizarEstadoJuego, renderEventos, agregarAlLog, appendGameChatMessage, mostrarModalFinJuego, actualizarCooldownsUI, actualizarEstadoParcial, actualizarEstadoRevancha } from './gameUI.js';
import { displayPerkOffer, handlePerkActivated, updatePerkPrices } from './perks.js';
import { appendPrivateMessage, updateSocialNotificationIndicator, invalidateSocialCache } from './social.js';
import { invalidateAchievementsCache } from './achievements.js'; 

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
let _intermediatePosition = {};
let codigoSalaActualDisplay = null;
let resultadoDadoDisplay = null;
let jugadoresEstadoDisplay = null;
let modalPrivateChatElement = null;
let privateChatSendBtn = null;
let modalSocialElement = null;
let socialFriendsListDisplay = null;
let modalFinalElement = null;
let btnNuevaPartida = null;
let btnVolverLobby = null;
let rematchWaitingMsg = null;


export function setupSocketHandlers(socketInstance, screenElements, loadingEl, notificationEl, stateRefs, gameAnimationsInstance) {
    _socket = socketInstance;
    _screens = screenElements;
    _loadingElement = loadingEl;
    _notificacionesContainer = notificationEl;
    _state = stateRefs;
    _currentUser = stateRefs.currentUser;
    _idSala = stateRefs.idSala;
    _estadoJuego = stateRefs.estadoJuego;
    _mapaColores = stateRefs.mapaColores;
    _habilidadUsadaTurno = stateRefs.habilidadUsadaTurno;
    _gameAnimations = gameAnimationsInstance;
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
    });
    _socket.on("conectado", () => { 
        setLoading(false, _loadingElement);
        console.log("Conexión con servidor establecida.");
    });
     _socket.on('authenticated', (data) => {
        console.log(`Socket autenticado como: ${data.username}`);
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
        _idSala.value = data.id_sala; 
        if(codigoSalaActualDisplay) codigoSalaActualDisplay.textContent = data.id_sala;
        show('waiting', _screens);
        _socket.emit("obtener_estado_sala", { id_sala: data.id_sala }); 
    });
    _socket.on("unido_exitoso", (data) => {
        setLoading(false, _loadingElement);
        _idSala.value = data.id_sala;
        if(codigoSalaActualDisplay) codigoSalaActualDisplay.textContent = data.id_sala;
        show('waiting', _screens);
        _socket.emit("obtener_estado_sala", { id_sala: data.id_sala });
    });
    _socket.on("jugador_unido", (data) => {
        updateWaitingRoomUI(data); 
    });
    _socket.on("jugador_desconectado", (data) => {
        updateWaitingRoomUI(data); 
        showNotification(data.mensaje_desconexion || `${escapeHTML(data.jugador_nombre)} se desconectó.`, _notificacionesContainer, "warning");
    });
    _socket.on("sala_abandonada", (data) => {
        setLoading(false, _loadingElement);
        _idSala.value = null; 
        Object.assign(_estadoJuego, {}); 
        _habilidadUsadaTurno.value = false;
        show("lobby", _screens); 
        loadTopPlayers(); 
        if (data.message) showNotification(data.message, _notificacionesContainer, data.success ? "info" : "error");
    });
    _socket.on("estado_sala", (data) => { 
        updateWaitingRoomUI(data);
    });
    _socket.on("nuevo_mensaje", (data) => { 
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
        if (modalSocialElement) modalSocialElement.style.display = "none"; 
        show("game", _screens);
        _mapaColores.value = estadoInicial.colores_jugadores || {}; 
        console.log("Mapa de colores recibido:", _mapaColores.value);
        actualizarEstadoJuego(estadoInicial); 
        const eventosLista = document.getElementById("eventos-lista");
        if (eventosLista) eventosLista.innerHTML = ''; 
        agregarAlLog("¡La partida ha comenzado!");
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
            const habilidad_usada = data.habilidad_usada; 
            renderEventos(eventosPaso1); 
            if (res.dado !== undefined && !habilidad_usada) {
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
            if (habilidad_usada && jugadorNombre === _state.currentUser.username) {
                actualizarCooldownsUI(jugadorNombre, habilidad_usada);
            }
            _intermediatePosition[jugadorNombre] = res.pos_final;
            if (_gameAnimations && _gameAnimations.isEnabled) {
                _gameAnimations.animatePlayerMove( res.pos_inicial, res.pos_final, jugadorNombre, () => { playOptimisticSound(res.pos_final, _estadoJuego); } );
            } else {
                playOptimisticSound(res.pos_final, _estadoJuego);
            }
            if (jugadorNombre === _state.currentUser.username) {
                _socket.emit('paso_2_terminar_movimiento', {  id_sala: _idSala.value, jugador_que_termino: jugadorNombre });
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
            if (estado_nuevo && _state.currentUser) {
                const nuevoTurnoDe = estado_nuevo.turno_actual;
                const miNombre = _state.currentUser.username;
                
                if (nuevoTurnoDe === miNombre && _estadoJuego.turno_actual !== miNombre) {
                    _habilidadUsadaTurno.value = false;
                    console.log("¡Comienzo de mi turno! Habilidades reseteadas.");
                }
            }
            let jugador_movido_nombre = null;
            let pos_vieja_real = -1;
            let pos_nueva_real = -1;
            if (estado_nuevo && _estadoJuego.jugadores) {
                for (const j_nuevo of estado_nuevo.jugadores) {
                    const j_viejo = _estadoJuego.jugadores.find(j => j.nombre === j_nuevo.nombre);
                    if (j_viejo && j_nuevo.posicion !== j_viejo.posicion) {
                        jugador_movido_nombre = j_nuevo.nombre;
                        pos_vieja_real = _intermediatePosition[j_nuevo.nombre] || j_viejo.posicion;
                        pos_nueva_real = j_nuevo.posicion;
                        delete _intermediatePosition[j_nuevo.nombre];
                        break; 
                    }
                }
            }
            eventos_paso_2.forEach(evento => {
                if (typeof evento !== 'string') return;
                const lowerEvent = evento.toLowerCase();
                if (lowerEvent.includes("trampa") || lowerEvent.includes("💀")) { if(_gameAnimations) _gameAnimations.shakeBoard(); }
                else if (lowerEvent.includes("colisión") || lowerEvent.includes("💥")) { playSound('Collision', 0.2); if(_gameAnimations) _gameAnimations.shakeBoard(); }
            });
            actualizarEstadoJuego(estado_nuevo);
            renderEventos(eventos_paso_2); 
            if (jugador_movido_nombre && pos_vieja_real !== pos_nueva_real && pos_nueva_real < 75) {
                console.log(`--- Movimiento encadenado (Paso 2): ${pos_vieja_real} -> ${pos_nueva_real}. Animando...`);
                playOptimisticSound(pos_nueva_real, estado_nuevo); 
                if (_gameAnimations && _gameAnimations.isEnabled) {
                    _gameAnimations.animatePlayerMove( pos_vieja_real, pos_nueva_real, jugador_movido_nombre, null );
                }
            }
        } catch (error) {
            console.error("!!! ERROR DENTRO DEL LISTENER 'paso_2_resultado_casilla':", error);
            agregarAlLog(`Error del cliente: ${error.message}`);
        }
    });

    _socket.on("habilidad_usada_full", (data) => {
        if (!_state || !_state.currentUser || !_state.currentUser.username) {
            console.warn("Habilidad (full) ignorada: Estado del usuario no disponible.");
            return; 
        }
        if (data.resultado?.exito) {
            _habilidadUsadaTurno.value = (data.jugador === _state.currentUser.username); 
        }
        actualizarEstadoJuego(data.estado_juego);
        renderEventos(data.resultado?.eventos);
        if (window.GameAnimations && data.habilidad && data.resultado?.exito && jugadoresEstadoDisplay) {
            const playerElement = Array.from(jugadoresEstadoDisplay.children).find(el => el.textContent.includes(data.jugador));
            if (playerElement) window.GameAnimations.animateAbilityUse(data.habilidad.tipo || "magic", playerElement);
        }
    });
    _socket.on("habilidad_usada_parcial", (data) => {
        if (!_state || !_state.currentUser || !_state.currentUser.username) {
            console.warn("Habilidad (parcial) ignorada: Estado del usuario no disponible.");
            return; 
        }
        if (data.resultado?.exito) {
            _habilidadUsadaTurno.value = (data.jugador === _state.currentUser.username); 
        }
        actualizarEstadoParcial(data.estado_juego_parcial);
        renderEventos(data.resultado?.eventos);
        if (window.GameAnimations && data.habilidad && data.resultado?.exito && jugadoresEstadoDisplay) {
            const playerElement = Array.from(jugadoresEstadoDisplay.children).find(el => el.textContent.includes(data.jugador));
            if (playerElement) window.GameAnimations.animateAbilityUse(data.habilidad.tipo || "magic", playerElement);
        }
    });
     _socket.on("habilidad_usada_privada", (data) => { 
        if (data.resultado?.exito) {
            _habilidadUsadaTurno.value = (data.jugador === _state.currentUser?.username);
        }
        actualizarEstadoParcial(data.estado_juego_parcial);
        renderEventos(data.resultado?.eventos); 
        if (window.GameAnimations && data.habilidad && data.resultado?.exito && jugadoresEstadoDisplay) {
            const playerElement = Array.from(jugadoresEstadoDisplay.children).find(el => el.textContent.includes(data.jugador));
            if (playerElement) window.GameAnimations.animateAbilityUse("stealth", playerElement);
        }
    });
    _socket.on("estado_juego_actualizado", (data) => { 
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
        }
    });
    _socket.on("perk_activado", (data) => {
        handlePerkActivated(data); 
    });

    _socket.on("achievements_unlocked", (data) => {
        if (data.achievements?.length > 0) {
            data.achievements.forEach(ach => {
                if(ach) showAchievementNotification(ach, _notificacionesContainer);
            });
            if (_currentUser.value) fetchAndUpdateUserProfile(_currentUser.value.username);
            invalidateAchievementsCache(); // Borra el caché
        }
    });
    _socket.on("level_up", (data) => {
        if (!data) return;
        showNotification( `🎉 ¡Subiste de Nivel! Eres Nivel ${data.new_level}`, _notificacionesContainer, "success", 5000 );
        const userLevelDisplay = document.getElementById("user-level");
        const userXpDisplay = document.getElementById("user-xp");
        if (userLevelDisplay) userLevelDisplay.textContent = `⭐ Nivel ${data.new_level}`;
        if (userXpDisplay) userXpDisplay.textContent = `${data.xp} XP`;
        if (_state.currentUser && _state.currentUser.username) {
             fetchAndUpdateUserProfile(_state.currentUser.username);
        }
        invalidateAchievementsCache(); // Borra el caché
    });

    _socket.on("profile_stats_updated", (data) => {
        if (!_state.currentUser) return; 
        
        console.log("Recibidas estadísticas actualizadas:", data);
        let updated = false;
        
        // Actualizar los valores en el estado local
        if (data.games_played !== undefined) {
            _state.currentUser.games_played = data.games_played;
            updated = true;
        }
        if (data.games_won !== undefined) {
            _state.currentUser.games_won = data.games_won;
            updated = true;
        }
        if (data.consecutive_wins !== undefined) {
            _state.currentUser.consecutive_wins = data.consecutive_wins;
            updated = true;
        }
        if (data.rooms_created !== undefined) {
            _state.currentUser.rooms_created = data.rooms_created;
            updated = true;
        }
        if (data.abilities_used !== undefined) {
            _state.currentUser.abilities_used = data.abilities_used;
            updated = true;
        }
        if (data.xp !== undefined) {
            _state.currentUser.xp = data.xp;
            updated = true;
        }
            if (data.level !== undefined) {
            _state.currentUser.level = data.level;
            updated = true;
        }
        if (data.xp_next_level !== undefined) {
            _state.currentUser.xp_next_level = data.xp_next_level;
            updated = true;
        }
        if (updated) {
            // Volver a renderizar la UI del perfil con los nuevos datos
            updateProfileUI(_state.currentUser);
        }
    });
    // --- Fin de Juego y Revancha ---
    _socket.on("juego_terminado", (data) => {
        mostrarModalFinJuego(data);
        Object.assign(_estadoJuego, {}); 
        if (_habilidadUsadaTurno) _habilidadUsadaTurno.value = false;
    });
    _socket.on('revancha_lista', (data) => {
        console.log("Revancha lista, uniéndose a nueva sala:", data.nueva_id_sala);
        if (modalFinalElement) modalFinalElement.style.display = 'none'; 
        if (btnNuevaPartida) { btnNuevaPartida.disabled = false; btnNuevaPartida.textContent = "🎮 Nueva Partida"; }
        if (btnVolverLobby) btnVolverLobby.disabled = false;
        const waitingMsg = document.getElementById('rematch-waiting-msg');
        if(waitingMsg) waitingMsg.remove();
        if (_state && _state.idSala) {
            _state.idSala.value = data.nueva_id_sala; 
            console.log(`ID de sala (revancha) actualizado a: ${_state.idSala.value}`);
        } else {
            console.error("Error en 'revancha_lista': _state o _state.idSala no están definidos correctamente. No se pudo actualizar idSala.");
            showNotification("Error al procesar la revancha.", _notificacionesContainer, "error");
            return; 
        }
        if(codigoSalaActualDisplay) codigoSalaActualDisplay.textContent = data.nueva_id_sala;
        show("waiting", _screens);
        _socket.emit("obtener_estado_sala", { id_sala: data.nueva_id_sala });
        showNotification("¡Revancha lista! Esperando jugadores...", _notificacionesContainer, "success");
    });
    _socket.on('revancha_cancelada', (data) => {
        let currentSalaId = null;
        if (_state && _state.idSala) {
            currentSalaId = _state.idSala.value; 
        } else {
            console.warn("Revancha cancelada recibida, pero _state o _state.idSala no están definidos.");
        }
        showNotification(data.mensaje || "La revancha fue cancelada.", _notificacionesContainer, "warning");
        console.log("Revancha cancelada:", data.mensaje);
        if (btnNuevaPartida) { btnNuevaPartida.disabled = false; btnNuevaPartida.textContent = "🎮 Nueva Partida"; }
        if (btnVolverLobby) btnVolverLobby.disabled = false;
        const waitingMsg = document.getElementById('rematch-waiting-msg');
        if(waitingMsg) waitingMsg.remove();
    });

    _socket.on('revancha_actualizada', (data) => {
        console.log("Estado de revancha actualizado:", data);
        actualizarEstadoRevancha(data);
    });

    // --- Social y Chat ---
    _socket.on("new_friend_request", (data) => {
        showNotification(`👥 ${escapeHTML(data.from_user)} te envió una solicitud.`, _notificacionesContainer, "info", 5000);
        updateSocialNotificationIndicator(true);
        invalidateSocialCache(); // Invalida el caché social
    });
    _socket.on("friend_status_update", (data) => {
        const friendName = escapeHTML(data.username || data.friend);
        let message = `👤 Estado de ${friendName} actualizado.`; // Mensaje por defecto

        // Comprobar el tipo de actualización para mensajes más claros
        if (data.type === "accepted") {
            message = `🎉 ¡Ahora eres amigo de ${friendName}!`;
        } else if (data.status === 'online') {
            message = `✅ ${friendName} se ha conectado.`;
        } else if (data.status === 'offline') {
            message = `🔌 ${friendName} se ha desconectado.`;
        } else if (data.status === 'in_game') {
            message = `⚔️ ${friendName} ha entrado en una partida.`;
        } else if (data.status === 'in_lobby') {
            message = `🚪 ${friendName} está en una sala de espera.`;
        }

        showNotification(message, _notificacionesContainer, "info");
        invalidateSocialCache(); // Invalida el caché social
    });
    _socket.on("new_private_message", (data) => {
        if (!data) return;
        const privateChatIsOpen = modalPrivateChatElement?.style.display === 'flex';
        const isChattingWithSender = document.getElementById('chat-with-username')?.textContent === data.sender;
        if (privateChatIsOpen && isChattingWithSender) {
            appendPrivateMessage(data); 
            _socket.emit('mark_chat_as_read', { sender: data.sender });
        } else {
            showNotification(`💬 Nuevo mensaje de ${escapeHTML(data.sender)}`, _notificacionesContainer, "info", 5000);
            updateSocialNotificationIndicator(true); 
        }
    });
    _socket.on("message_sent_confirm", (data) => { 
        const privateChatIsOpen = modalPrivateChatElement?.style.display === 'flex';
        const isChattingWithRecipient = document.getElementById('chat-with-username')?.textContent === data.recipient;
        if (privateChatIsOpen && isChattingWithRecipient) {
            appendPrivateMessage(data); 
        }
        if (privateChatSendBtn) { 
            privateChatSendBtn.disabled = false;
            privateChatSendBtn.textContent = "Enviar";
        }
    });
    _socket.on("invite_sent_confirm", (data) => {
        showNotification(`Invitación enviada a ${escapeHTML(data.to)}.`, _notificacionesContainer, "success");
        if (modalSocialElement?.style.display === 'flex' && socialFriendsListDisplay) {
            const inviteButton = socialFriendsListDisplay.querySelector(`.social-list-item[data-username="${data.to}"] .btn-invite-friend`);
            if (inviteButton) {
                inviteButton.disabled = false;
                inviteButton.textContent = "🎮"; 
            }
        }
    });
    _socket.on('room_invite', (data) => { 
        if (!_state) {
        console.warn("Invitación ignorada: Objeto de estado (_state) no inicializado.");
        return;
        }   
        manejarInvitacion(data, _notificacionesContainer, _socket,
                        _state, 
                        setLoading, show, _screens);
    });

    console.log("Socket handlers configurados.");
} 
// Fin de setupSocketHandlers

function playOptimisticSound(posFinal, estadoJuego) {
    if (!estadoJuego || !estadoJuego.tablero) return;
    const casillaData = estadoJuego.tablero[posFinal];
    if (!casillaData) return;
    const tipoCasilla = casillaData.casilla_especial?.tipo;
    const valorEnergia = casillaData.energia;
    if (tipoCasilla === 'trampa') {
        playSound('LandOnTrap', 0.2);
    } else if (tipoCasilla === 'tesoro') {
        playSound('LandOnTreasure', 0.2);
    } else if (tipoCasilla === 'teletransporte' || tipoCasilla === 'intercambio' || tipoCasilla === 'retroceso_estrategico') {
        playSound('Teleport', 0.3);
    }
    else if (valorEnergia > 0) {
        playSound('LandOnTreasure', 0.2); 
    } else if (valorEnergia < 0) {
        playSound('LandOnTrap', 0.2); 
    }
}