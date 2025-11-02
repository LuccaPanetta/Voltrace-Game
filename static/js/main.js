/* ===================================================================
   PUNTO DE ENTRADA PRINCIPAL DEL CLIENTE (main.js)
   Importa módulos, inicializa Socket.IO, gestiona estado global mínimo
   y asigna listeners iniciales. Usa type="module".
   =================================================================== */

// --- Importaciones de Módulos ---
import { show, setLoading, playSound } from './modules/utils.js';
import { initAuth, fetchAndUpdateUserProfile, updateProfileUI } from './modules/auth.js';
import { initLobby, loadTopPlayers } from './modules/lobby.js';
import { initGameUI } from './modules/gameUI.js';
import { initPerks, openPerkModal, loadPerksConfig } from './modules/perks.js'; 
import { initSocial } from './modules/social.js';
import { initAchievements } from './modules/achievements.js';
import { setupSocketHandlers } from './modules/socketHandlers.js';
import { AnimationSystem } from './animations.js';

(function () {
    "use strict";

    // --- Inicialización de Socket.IO ---
    // io() es global porque se carga desde la CDN 
    const socket = io();
    const gameAnimations = new AnimationSystem();

    // --- Referencias DOM Principales (Cache Global) ---
    const screens = {
        auth: document.getElementById("auth-screen"),
        lobby: document.getElementById("lobby-screen"),
        waiting: document.getElementById("waiting-screen"),
        game: document.getElementById("game-screen"),
    };
    const loadingElement = document.getElementById("loading");
    const notificacionesContainer = document.getElementById("notificaciones");
    const modalesCerrables = [ // Para cerrar con ESC
        document.getElementById("modal-habilidades"),
        document.getElementById("modal-social"),
        document.getElementById("modal-private-chat"),
        document.getElementById('modal-reglas'),
        document.getElementById("modal-final"),
        document.getElementById("modal-perks"),
        document.getElementById("modal-achievements")
    ];
    const btnCerrarPerks = document.getElementById("btn-cerrar-perks"); // Necesario para lógica ESC

    // --- Estado Global Mínimo (Mutable) ---
    // Usamos objetos para pasar por referencia a los módulos
    const state = {
        currentUser: null, // Guarda el objeto { username, level, xp } o null
        idSala: { value: null }, // Guarda el ID de la sala o null DENTRO de 'value'
        estadoJuego: {},
        mapaColores: {},
        habilidadUsadaTurno: { value: false }
    };
    /**
     * Función central que maneja el éxito de un login o un logout.
     * Actualiza el estado global, la UI, y muestra la pantalla correcta.
     */
    function handleLoginSuccess(userData) {
        state.currentUser = userData; // Actualiza state.currentUser 
        updateProfileUI(userData);
        if (userData) {
            // LOGIN
            socket.emit('authenticate', { username: userData.username });
            show('lobby', screens);
            loadTopPlayers();
        } else {
            // LOGOUT
            state.idSala.value = null;
            Object.assign(state.estadoJuego, {});
            Object.assign(state.mapaColores, {});
            state.habilidadUsadaTurno.value = false;
        }
    }

    // --- Función Global para Resetear Estado ---
    window.resetAndShowLobby = () => {
        playSound('ClickMouse', 0.3);
        const modalFinal = document.getElementById("modal-final");
        if (modalFinal) modalFinal.style.display = "none";

        // Resetear estado usando .value para idSala
        state.idSala.value = null; // <-- MODIFICADO
        Object.assign(state.estadoJuego, {});
        Object.assign(state.mapaColores, {});
        state.habilidadUsadaTurno.value = false;

        // Limpiar UI
        const codigoSalaActual = document.getElementById("codigo-sala-actual");
        if (codigoSalaActual) codigoSalaActual.textContent = "-";
        const listaJugadores = document.getElementById("lista-jugadores");
        if (listaJugadores) listaJugadores.innerHTML = "";

        show('lobby', screens);
        loadTopPlayers();
    };
    // Función global para show
    window.showScreen = (screenName) => show(screenName, screens);


    // --- Inicialización de Módulos ---
    initAuth(screens, show, setLoading, loadingElement, handleLoginSuccess, gameAnimations);

    // Pasa el objeto 'state' completo a los módulos que necesitan leer currentUser
    initLobby(socket, screens, show, setLoading, state);
    initSocial(socket, state); 
    initAchievements(state); 

    // Pasa las referencias específicas a los módulos que las necesitan/modifican
    initGameUI(socket, state, state.idSala, state.estadoJuego, state.mapaColores, state.habilidadUsadaTurno, openPerkModal);
    initPerks(socket, state, state.idSala, state.estadoJuego); 

    // setupSocketHandlers recibe el objeto 'state' bajo el nombre 'stateRefs'
    setupSocketHandlers(socket, screens, loadingElement, notificacionesContainer, state, gameAnimations);

    // --- Listener Global para Tecla Escape ---
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            modalesCerrables.forEach(modal => {
                if (modal && modal.style.display === "flex") {
                    // Excepción: No cerrar modal de perks si está esperando selección
                    const isPerkModalWaiting = modal.id === 'modal-perks' && btnCerrarPerks && btnCerrarPerks.style.display === 'none';
                    if (!isPerkModalWaiting) {
                        modal.style.display = "none";
                        playSound('OpenCloseModal', 0.2);
                        // Si cerramos el modal de perks, reactivar botones
                        if (modal.id === 'modal-perks') {
                             if (typeof reactivarBotonesPackSiEsPosible === 'function') reactivarBotonesPackSiEsPosible();
                        }
                    } else {
                        showNotification("Debes seleccionar un perk para continuar", notificacionesContainer, "warning");
                    }
                }
            });
        }
    });

    // --- Heartbeat de Presencia ---
    setInterval(() => {
        if (socket.connected && state.currentUser) {
            socket.emit('presence_heartbeat');
        }
    }, 30000); // Cada 30 segundos

    // --- Carga Inicial ---
    const simulatedPerksConfig = {
        // === TIER BÁSICO ===
        "recarga_constante": { "id": "recarga_constante", "nombre": "Recarga Constante", "tier": "basico", "desc": "Ganas +10 de energía al inicio de cada uno de tus turnos." },
        "recompensa_de_mina": { "id": "recompensa_de_mina", "nombre": "Recompensa de Mina", "tier": "basico", "desc": "Si un oponente cae en tu Mina de Energía (💣), ganas la mitad de la energía que pierden.", "requires_habilidad": "Mina de Energía" },
        "impulso_inestable": { "id": "impulso_inestable", "nombre": "Impulso Inestable", "tier": "basico", "desc": "Tras tirar dado, 50% de +1 casilla, 50% de -1 casilla." },
        "chatarrero": { "id": "chatarrero", "nombre": "Chatarrero", "tier": "basico", "desc": "Ganas +1 PM al caer en Trampa o recoger pack negativo." },
        "presencia_intimidante": { "id": "presencia_intimidante", "nombre": "Presencia Intimidante", "tier": "basico", "desc": "Jugadores que colisionan contigo (cuando tú no te mueves) pierden 10 energía extra." },
        "descuento_habilidad": { "id": "descuento_habilidad", "nombre": "Descuento en Habilidad", "tier": "basico", "desc": "Una de tus habilidades (al azar) tiene su cooldown reducido en 1 turno adicional." },
        "maremoto": { "id": "maremoto", "nombre": "Maremoto", "tier": "basico", "desc": "Si tienes 'Tsunami', empuja 5 casillas atrás (vs 3).", "requires_habilidad": "Tsunami" },
        "acumulador_de_pm": { "id": "acumulador_de_pm", "nombre": "Acumulador de PM", "tier": "basico", "desc": "Ganas +1 PM adicional cada vez que obtienes PM de cualquier fuente." },
        "retroceso_brutal": { "id": "retroceso_brutal", "nombre": "Retroceso Brutal", "tier": "basico", "desc": "Si tienes 'Retroceso', empuja 7 casillas atrás (vs 5).", "requires_habilidad": "Retroceso" },

        // === TIER MEDIO ===
        "aislamiento": { "id": "aislamiento", "nombre": "Aislamiento", "tier": "medio", "desc": "Pierdes un 20% menos de energía por trampas y packs negativos." },
        "amortiguacion": { "id": "amortiguacion", "nombre": "Amortiguación", "tier": "medio", "desc": "Reduce la energía perdida por colisiones en un 33% (pierdes 67 vs 100)." },
        "eficiencia_energetica": { "id": "eficiencia_energetica", "nombre": "Eficiencia Energética", "tier": "medio", "desc": "Recoges un 20% más de energía de los packs positivos." },
        "anticipacion": { "id": "anticipacion", "nombre": "Anticipación", "tier": "medio", "desc": "Tienes un 20% de probabilidad de esquivar habilidad ofensiva enemiga." },
        "robo_oportunista": { "id": "robo_oportunista", "nombre": "Robo Oportunista", "tier": "medio", "desc": "Si tienes 'Robo', roba +30 de energía adicional (80-180 vs 50-150).", "requires_habilidad": "Robo" },
        "escudo_duradero": { "id": "escudo_duradero", "nombre": "Escudo Duradero", "tier": "medio", "desc": "Si tienes 'Escudo Total', dura 1 ronda adicional.", "requires_habilidad": "Escudo Total" }, 
        "bomba_fragmentacion": { "id": "bomba_fragmentacion", "nombre": "Bomba de Fragmentación", "tier": "medio", "desc": "Si tienes 'Bomba Energética', además del daño, empuja a los afectados 1 casilla lejos de ti.", "requires_habilidad": "Bomba Energética" },
        "sombra_fugaz": { "id": "sombra_fugaz", "nombre": "Sombra Fugaz", "tier": "medio", "desc": "Si tienes 'Invisibilidad', no causas ni te afectan las colisiones.", "requires_habilidad": "Invisibilidad" },
        "dado_cargado": { "id": "dado_cargado", "nombre": "Dado Cargado", "tier": "medio", "desc": "Si tienes 'Dado Perfecto': eligiendo 1-3 ganas +10 energía, eligiendo 4-6 ganas +1 PM.", "requires_habilidad": "Dado Perfecto" },
        "desvio_cinetico": { "id": "desvio_cinetico", "nombre": "Desvío Cinético", "tier": "medio", "desc": "Reduce a la mitad (redondeado hacia abajo) el movimiento forzado por habilidades de oponentes." },
        "maestro_del_azar": { "id": "maestro_del_azar", "nombre": "Maestro del Azar", "tier": "medio", "desc": "Si tienes 'Caos', tú te mueves el doble de tu resultado aleatorio.", "requires_habilidad": "Caos" },

        // === TIER ALTO ===
        "maestria_habilidad": { "id": "maestria_habilidad", "nombre": "Maestría de Habilidad", "tier": "alto", "desc": "Ganas +3 PM extra al usar una habilidad con éxito." },
        "ultimo_aliento": { "id": "ultimo_aliento", "nombre": "Último Aliento", "tier": "alto", "desc": "La primera vez que tu energía llegaría a 0 o menos, sobrevives con 50 E y ganas Escudo Total (3 rondas). (Una vez por partida)" },
        "enfriamiento_rapido": { "id": "enfriamiento_rapido", "nombre": "Enfriamiento Rápido", "tier": "alto", "desc": "Reduce el cooldown base de todas tus habilidades en 1 turno (mínimo 1)." },
        "drenaje_colision": { "id": "drenaje_colision", "nombre": "Drenaje por Colisión", "tier": "alto", "desc": "Cuando colisionas, robas 50 energía a cada otro jugador involucrado (no protegido)." },
        "sabotaje_persistente": { "id": "sabotaje_persistente", "nombre": "Sabotaje Persistente", "tier": "alto", "desc": "Si tienes 'Sabotaje', hace que el objetivo pierda 2 turnos (vs 1).", "requires_habilidad": "Sabotaje" }
    };
    loadPerksConfig(simulatedPerksConfig);

    // =======================================================
    // --- LÓGICA DE INICIO BASADA EN AUTENTICACIÓN ---
    // =======================================================

    // 1. Leer el estado de autenticación inyectado desde el servidor
    const bodyData = document.body.dataset;
    const isAuthenticated = bodyData.isAuthenticated === 'true';
    const username = bodyData.username;

    if (isAuthenticated && username) {
        // 2. Si el servidor dice que SÍ estamos logueados:
        console.log(`Usuario ya autenticado como: ${username}. Saltando al lobby.`);
        
        handleLoginSuccess({ username: username });
        
    } else {
        // 3. Si NO estamos logueados:
        console.log("Usuario no autenticado. Mostrando pantalla de login.");
        show('auth', screens);
    }
    
    // 4. Ocultar el 'loading' y terminar la inicialización
    setLoading(false, loadingElement);
    console.log("Aplicación inicializada (main.js).");

})();