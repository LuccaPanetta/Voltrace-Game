/* ===================================================================
   MÓDULO DE MANEJADORES DE SOCKET.IO (socketHandlers.js)
   Define todos los listeners para eventos del servidor.
   =================================================================== */

import { show, setLoading, showNotification, manejarInvitacion, showAchievementNotification, playSound, escapeHTML } from './utils.js';
import { updateProfileUI, fetchAndUpdateUserProfile } from './auth.js';
import { updateWaitingRoomUI, appendLobbyChatMessage, loadTopPlayers } from './lobby.js';
import { actualizarEstadoJuego, renderEventos, agregarAlLog, appendGameChatMessage, mostrarModalFinJuego, actualizarCooldownsUI } from './gameUI.js';
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
let _intermediatePosition = {};

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
            
            // Actualizar UI de Cooldown si fue una habilidad
            if (habilidad_usada && jugadorNombre === _state.currentUser.username) {
                actualizarCooldownsUI(jugadorNombre, habilidad_usada);
            }
            
            if (res.meta_alcanzada) {
                if (_gameAnimations && _gameAnimations.isEnabled) { 
                    _gameAnimations.animatePlayerMove(res.pos_inicial, res.pos_final, jugadorNombre, () => {});
                }
                return; 
            }

            // Almacena la posición intermedia
            _intermediatePosition[jugadorNombre] = res.pos_final;
            
            // Iniciar animación 
            if (_gameAnimations && _gameAnimations.isEnabled) {
                _gameAnimations.animatePlayerMove(
                    res.pos_inicial,
                    res.pos_final,
                    jugadorNombre,
                    () => {
                        playOptimisticSound(res.pos_final, _estadoJuego);
                    } 
                );
            } else {
                playOptimisticSound(res.pos_final, _estadoJuego);
            }

            const jugadorDelTurno = _estadoJuego.turno_actual;
            if (jugadorDelTurno === _state.currentUser.username) {
                _socket.emit('paso_2_terminar_movimiento', { 
                    id_sala: _idSala.value,
                    jugador_movido: jugadorNombre 
                });
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

            // Encontrar al jugador que REALMENTE cambió de posición
            let jugador_movido_nombre = null;
            let pos_vieja_real = -1;
            let pos_nueva_real = -1;

            if (estado_nuevo && _estadoJuego.jugadores) {
                for (const j_nuevo of estado_nuevo.jugadores) {
                    const j_viejo = _estadoJuego.jugadores.find(j => j.nombre === j_nuevo.nombre);
                    
                    if (j_viejo && j_nuevo.posicion !== j_viejo.posicion) {
                        jugador_movido_nombre = j_nuevo.nombre;
                        
                        // Usar la posición intermedia
                        pos_vieja_real = _intermediatePosition[j_nuevo.nombre] || j_viejo.posicion;
                        pos_nueva_real = j_nuevo.posicion;
                        
                        delete _intermediatePosition[j_nuevo.nombre];
                        break; 
                    }
                }
            }

            // Reproducir efectos visuales (shake) y sonidos
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
            
            // Comprobar si hubo un movimiento forzado (Teleport, etc.)
            if (jugador_movido_nombre && pos_vieja_real !== pos_nueva_real && pos_nueva_real < 75) {
                console.log(`--- Movimiento encadenado (Paso 2): ${pos_vieja_real} -> ${pos_nueva_real}. Animando...`);
                
                playOptimisticSound(pos_nueva_real, estado_nuevo); 

                if (_gameAnimations && _gameAnimations.isEnabled) {
                    // ¡Animar el "salto"!
                    _gameAnimations.animatePlayerMove(
                        pos_vieja_real,
                        pos_nueva_real,
                        jugador_movido_nombre,
                        () => {
                            // Cuando la animación del teleporter TERMINA,
                            // actualizar la UI al estado final.
                            actualizarEstadoJuego(estado_nuevo);
                            renderEventos(eventos_paso_2);
                        }
                    );
                } else {
                    actualizarEstadoJuego(estado_nuevo);
                    renderEventos(eventos_paso_2);
                }
            } else {
                // No hubo movimiento extra, solo actualizar.
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