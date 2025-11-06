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
import { initSocial, loadSocialData } from './modules/social.js';
import { initAchievements, loadAchievementsData } from './modules/achievements.js';
import { setupSocketHandlers } from './modules/socketHandlers.js';
import { AnimationSystem } from './animations.js';
import { initArsenal, loadArsenalData } from './modules/arsenal.js';

(function () {
    "use strict";

    // --- Inicialización de Socket.IO ---
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
    
    const modalesCerrables = [ 
        document.getElementById("modal-habilidades"),
        document.getElementById("modal-social"),
        document.getElementById("modal-private-chat"),
        document.getElementById('modal-reglas'), 
        document.getElementById("modal-final"),
        document.getElementById("modal-perks"),
        document.getElementById("modal-achievements"),
        document.getElementById("modal-glossary")
    ];
    
    const btnCerrarPerks = document.getElementById("btn-cerrar-perks"); 

    // --- Estado Global Mínimo ---
    const state = {
        currentUser: null, 
        idSala: { value: null }, 
        estadoJuego: {},
        mapaColores: {},
        habilidadUsadaTurno: { value: false },
        kitSeleccionado: { value: 'tactico' },
        cosmeticsUnlocked: []
    };
    
    /**
     * Función central que maneja el éxito de un login o un logout.
     * Actualiza el estado global, la UI, y muestra la pantalla correcta.
     */
    // ===== LOGIN RÁPIDO =====
    async function handleLoginSuccess(user_data) {
        
        if (user_data && user_data.username) {
            // Autenticar el socket inmediatamente
            socket.emit('authenticate', { username: user_data.username });

            // Guardar el estado
            state.currentUser = user_data; 
            
            // Actualizar la UI del header (
            updateProfileUI(state.currentUser);
            
            if (user_data.kit_id) {
                actualizarKitUI(user_data.kit_id); 
            }

            // Mostrar el lobby
            show('lobby', screens);
            loadTopPlayers(); 
            
            // Iniciar la precarga de datos sociales y de logros en segundo plano
            console.log("Iniciando precarga de datos sociales y de logros...");
            loadSocialData();
            loadAchievementsData();
            loadArsenalData();
            document.getElementById("btn-crear-sala").disabled = false;
            document.getElementById("btn-unirse-sala").disabled = false;

        } else {
            // --- Caso de Logout ---
            state.currentUser = null; 
            updateProfileUI(null); // Limpiar la UI del header
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
        
        if (state.idSala.value) {
            socket.emit("abandonar_revancha", { id_sala_original: state.idSala.value });
        }

        state.idSala.value = null; 
        Object.assign(state.estadoJuego, {});
        Object.assign(state.mapaColores, {});
        state.habilidadUsadaTurno.value = false;

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
    initAuth(screens, show, setLoading, loadingElement, handleLoginSuccess, gameAnimations, state);
    initLobby(socket, screens, show, setLoading, state);
    initSocial(socket, state); 
    initAchievements(state); 
    initGameUI(socket, state, state.idSala, state.estadoJuego, state.mapaColores, state.habilidadUsadaTurno, openPerkModal);
    initPerks(socket, state, state.idSala, state.estadoJuego); 
    setupSocketHandlers(socket, screens, loadingElement, notificacionesContainer, state, gameAnimations);
    initArsenal(socket, state);

    // --- Listeners para Kits ---
    const modalKits = document.getElementById('modal-kits');
    const btnAbrirKits = document.getElementById('btn-abrir-kits');
    const btnCerrarKits = document.getElementById('close-modal-kits');
    const kitCards = document.querySelectorAll('.kit-card');

    // Función para actualizar la UI del Kit
    function actualizarKitUI(kitId) {
        if (!kitId) kitId = 'tactico';
        state.kitSeleccionado.value = kitId;
        kitCards.forEach(card => {
            card.classList.toggle('seleccionado', card.dataset.kit === kitId);
        });
        console.log(`UI actualizada al kit: ${kitId}`);
    }

    // Abrir modal
    btnAbrirKits?.addEventListener('click', () => {
        playSound('OpenCloseModal', 0.3);
        actualizarKitUI(state.kitSeleccionado.value); // Asegurarse que muestre el correcto
        if (modalKits) modalKits.style.display = 'flex';
    });

    // Cerrar modal
    btnCerrarKits?.addEventListener('click', () => {
        playSound('OpenCloseModal', 0.2);
        if (modalKits) modalKits.style.display = 'none';
    });
    modalKits?.addEventListener('click', (e) => {
        if (e.target === modalKits) {
            playSound('OpenCloseModal', 0.2);
            if (modalKits) modalKits.style.display = 'none';
        }
    });

    // Seleccionar un kit
    kitCards.forEach(card => {
        card.addEventListener('click', (e) => {
            const kitId = e.currentTarget.dataset.kit;
            if (kitId && kitId !== state.kitSeleccionado.value) {
                playSound('ClickMouse', 0.3);
                // Guardar en servidor
                socket.emit('guardar_kit', { kit_id: kitId });
                // Actualizar estado local 
                state.kitSeleccionado.value = kitId;
                // Actualizar UI
                actualizarKitUI(kitId);
            }
        });
    });

    // --- Listener Global para Tecla Escape ---
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            modalesCerrables.forEach(modal => {
                if (modal && modal.style.display === "flex") {
                    const isPerkModalWaiting = modal.id === 'modal-perks' && btnCerrarPerks && btnCerrarPerks.style.display === 'none';
                    if (!isPerkModalWaiting) {
                        modal.style.display = "none";
                        playSound('OpenCloseModal', 0.2);
                        if (modal.id === 'modal-perks') {
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

    // --- Carga Inicial de Configs ---
    const simulatedPerksConfig = {
        "recarga_constante": { "id": "recarga_constante", "nombre": "Recarga Constante", "tier": "basico", "desc": "Ganas +10 de energía al inicio de cada uno de tus turnos." },
        "recompensa_de_mina": { "id": "recompensa_de_mina", "nombre": "Recompensa de Mina", "tier": "basico", "desc": "Si un oponente cae en tu Mina de Energía (💣), ganas la mitad de la energía que pierden.", "requires_habilidad": "Mina de Energía" },
        "impulso_inestable": { "id": "impulso_inestable", "nombre": "Impulso Inestable", "tier": "basico", "desc": "Tras tirar dado, 50% de +2 casillas, 50% de -1 casilla." },
        "chatarrero": { "id": "chatarrero", "nombre": "Chatarrero", "tier": "basico", "desc": "Ganas +1 PM al caer en Trampa o recoger pack negativo." },
        "presencia_intimidante": { "id": "presencia_intimidante", "nombre": "Presencia Intimidante", "tier": "basico", "desc": "Jugadores que colisionan contigo (cuando tú no te mueves) pierden 25 energía extra." },
        "descuento_habilidad": { "id": "descuento_habilidad", "nombre": "Descuento en Habilidad", "tier": "basico", "desc": "Una de tus habilidades (al azar) tiene su cooldown reducido en 1 turno adicional." },
        "maremoto": { "id": "maremoto", "nombre": "Maremoto", "tier": "basico", "desc": "Si tienes 'Tsunami', empuja 5 casillas atrás (vs 3).", "requires_habilidad": "Tsunami" },
        "acumulador_de_pm": { "id": "acumulador_de_pm", "nombre": "Acumulador de PM", "tier": "basico", "desc": "Ganas +1 PM adicional cada vez que obtienes PM de casillas especiales (Pozo/Chatarrería)." },
        "retroceso_brutal": { "id": "retroceso_brutal", "nombre": "Retroceso Brutal", "tier": "basico", "desc": "Si tienes 'Retroceso', empuja 7 casillas atrás (vs 5).", "requires_habilidad": "Retroceso" },
        "aislamiento": { "id": "aislamiento", "nombre": "Aislamiento", "tier": "medio", "desc": "Pierdes un 20% menos de energía por trampas y packs negativos." },
        "amortiguacion": { "id": "amortiguacion", "nombre": "Amortiguación", "tier": "medio", "desc": "Reduce la energía perdida por colisiones en un 33% (pierdes 67 vs 100)." },
        "eficiencia_energetica": { "id": "eficiencia_energetica", "nombre": "Eficiencia Energética", "tier": "medio", "desc": "Recoges un 20% más de energía de los packs positivos." },
        "anticipacion": { "id": "anticipacion", "nombre": "Anticipación", "tier": "medio", "desc": "Tienes un 20% de probabilidad de esquivar habilidad ofensiva enemiga." },
        "robo_oportunista": { "id": "robo_oportunista", "nombre": "Robo Oportunista", "tier": "medio", "desc": "Si tienes 'Robo', roba +30 de energía adicional (80-180 vs 50-150).", "requires_habilidad": "Robo" },
        "escudo_duradero": { "id": "escudo_duradero", "nombre": "Escudo Duradero", "tier": "medio", "desc": "Si tienes 'Escudo Total', dura 1 turno adicional (4 total).", "requires_habilidad": "Escudo Total" }, 
        "bomba_fragmentacion": { "id": "bomba_fragmentacion", "nombre": "Bomba de Fragmentación", "tier": "medio", "desc": "Si tienes 'Bomba Energética', su rango aumenta de 3 a 5 casillas y, además del daño, empuja a los afectados 1 casilla.", "requires_habilidad": "Bomba Energética" }, 
        "sombra_fugaz": { "id": "sombra_fugaz", "nombre": "Sombra Fugaz", "tier": "medio", "desc": "Si tienes 'Invisibilidad', no causas ni te afectan las colisiones.", "requires_habilidad": "Invisibilidad" },
        "dado_cargado": { "id": "dado_cargado", "nombre": "Dado Cargado", "tier": "medio", "desc": "Si tienes 'Dado Perfecto': eligiendo 1-3 ganas +10 energía, eligiendo 4-6 ganas +1 PM.", "requires_habilidad": "Dado Perfecto" },
        "desvio_cinetico": { "id": "desvio_cinetico", "nombre": "Desvío Cinético", "tier": "medio", "desc": "Reduce a la mitad (redondeado hacia abajo) el movimiento forzado por habilidades de oponentes." },
        "maestro_del_azar": { "id": "maestro_del_azar", "nombre": "Maestro del Azar", "tier": "medio", "desc": "Si tienes 'Caos', tú te mueces el doble de tu resultado aleatorio.", "requires_habilidad": "Caos" },
        "maestria_habilidad": { "id": "maestria_habilidad", "nombre": "Maestría de Habilidad", "tier": "alto", "desc": "Ganas +2 PM extra al usar una habilidad con éxito." }, 
        "ultimo_aliento": { "id": "ultimo_aliento", "nombre": "Último Aliento", "tier": "alto", "desc": "Al llegar a 0 E por primera vez, sobrevive con 50 E y gana Escudo Total (3 rondas)." },
        "enfriamiento_rapido": { "id": "enfriamiento_rapido", "nombre": "Enfriamiento Rápido", "tier": "alto", "desc": "Reduce el cooldown base de todas tus habilidades en 1 turno (mínimo 1)." },
        "drenaje_colision": { "id": "drenaje_colision", "nombre": "Drenaje por Colisión", "tier": "alto", "desc": "Cuando colisionas, robas 50 energía a cada otro jugador involucrado." },
        "sabotaje_persistente": { "id": "sabotaje_persistente", "nombre": "Sabotaje Persistente", "tier": "alto", "desc": "Si tienes 'Sabotaje', hace que el objetivo pierda 2 turnos (vs 1).", "requires_habilidad": "Sabotaje" }
    };
    loadPerksConfig(simulatedPerksConfig);

    // =======================================================
    // --- LÓGICA DE INICIO BASADA EN AUTENTICACIÓN ---
    // =======================================================

    // Leer los datos de usuario inyectados desde el servidor
    const userData = window.VOLTRACE_USER_DATA || null;

    if (userData) {
        // Si el servidor SÍ proveyó datos (login automático exitoso):
        console.log(`Usuario ya autenticado como: ${userData.username}. Saltando al lobby.`);
        handleLoginSuccess(userData);
        
    } else {
        // Si NO estamos logueados (userData es "null"):
        console.log("Usuario no autenticado. Mostrando pantalla de login.");
        show('auth', screens);
    }
    
    // Ocultar el 'loading' y terminar la inicialización
    setLoading(false, loadingElement);
    console.log("Aplicación inicializada (main.js).");

})();