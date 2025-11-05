/* ===================================================================
   MÓDULO LOBBY Y SALA DE ESPERA (lobby.js)
   Maneja la UI y lógica para crear/unirse a salas y la pantalla de espera.
   =================================================================== */

import { showNotification, escapeHTML, playSound } from './utils.js';

// Referencias DOM
let codigoSalaInput, topPlayersContainer, btnCrearSala, btnUnirseSala;
let codigoSalaActualDisplay, btnCopiarCodigo, listaJugadoresDisplay, contadorJugadoresDisplay;
let btnIniciarJuego, btnSalirSala, logEventosDisplay, chatMensajesLobbyDisplay;
let mensajeLobbyInput, btnEnviarMensajeLobby;
let tabRules, tabRanking, rulesContent, rankingContent;
let btnShowGlossary, modalGlossary, btnCerrarGlossary, 
    glossaryAbilitiesList, glossaryPerksList;

// Referencias a funciones/elementos externos
let _setLoadingFunc = null;
let _showFunc = null;
let _screens = null;
let _socket = null;
let _state = null; 

// --- Caché de Top 5 ---
const rankingCache = {
    data: null,
    isLoaded: false,
    isLoading: false,
    lastLoaded: 0 // Timestamp
};
const CACHE_DURATION_MS = 5 * 60 * 1000; // 5 minutos

// --- Caché del Glosario ---
const glossaryCache = {
    abilities: null,
    perks: null,
    isLoaded: false,
    isLoading: false,
};


/**
 * Inicializa el módulo del lobby, cachea elementos y asigna listeners.
 */
export function initLobby(socketRef, screensRef, showFuncRef, setLoadingFuncRef, stateRef) {
    _socket = socketRef;
    _screens = screensRef;
    _showFunc = showFuncRef;
    _setLoadingFunc = setLoadingFuncRef;
    _state = stateRef; 

    // Cachear elementos DOM del Lobby
    codigoSalaInput = document.getElementById("codigo-sala");
    topPlayersContainer = document.getElementById("top-players");
    btnCrearSala = document.getElementById("btn-crear-sala");
    btnUnirseSala = document.getElementById("btn-unirse-sala");
    tabRules = document.getElementById("btn-abrir-reglas");
    tabRanking = document.getElementById("tab-ranking");
    rulesContent = document.getElementById("rules-content");
    rankingContent = document.getElementById("ranking-content");
    
    btnShowGlossary = document.getElementById("btn-show-glossary");
    modalGlossary = document.getElementById("modal-glossary");
    btnCerrarGlossary = document.getElementById("btn-cerrar-glossary");
    glossaryAbilitiesList = document.getElementById("glossary-abilities-list");
    glossaryPerksList = document.getElementById("glossary-perks-list");

    // Cachear elementos DOM de Sala de Espera
    codigoSalaActualDisplay = document.getElementById("codigo-sala-actual");
    btnCopiarCodigo = document.getElementById("btn-copiar-codigo");
    listaJugadoresDisplay = document.getElementById("lista-jugadores");
    contadorJugadoresDisplay = document.getElementById("contador-jugadores");
    btnIniciarJuego = document.getElementById("btn-iniciar-juego");
    btnSalirSala = document.getElementById("btn-salir-sala");
    logEventosDisplay = document.getElementById("log-eventos");
    chatMensajesLobbyDisplay = document.getElementById("chat-mensajes");
    mensajeLobbyInput = document.getElementById("mensaje-input");
    btnEnviarMensajeLobby = document.getElementById("btn-enviar-mensaje");

    // Asignar listeners
    btnCrearSala?.addEventListener("click", handleCrearSala);
    btnUnirseSala?.addEventListener("click", handleUnirseSala);
    codigoSalaInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleUnirseSala(); });
    tabRules?.addEventListener("click", handleLobbyTabClick);
    tabRanking?.addEventListener("click", handleLobbyTabClick);
    
    // --- INICIO DE MODIFICACIÓN (Glosario Modal) ---
    btnShowGlossary?.addEventListener("click", openGlossaryModal);
    btnCerrarGlossary?.addEventListener("click", closeGlossaryModal);
    modalGlossary?.addEventListener('click', (e) => { if (e.target === modalGlossary) closeGlossaryModal(); });
    // --- FIN DE MODIFICACIÓN ---

    btnCopiarCodigo?.addEventListener("click", handleCopiarCodigo);
    btnIniciarJuego?.addEventListener("click", handleIniciarJuego);
    btnSalirSala?.addEventListener("click", handleSalirSala);
    btnEnviarMensajeLobby?.addEventListener("click", handleEnviarMensajeLobby);
    mensajeLobbyInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleEnviarMensajeLobby(); });

    // Cargar Top Players al inicializar 
    if (_screens.lobby?.classList.contains('active')) {
        loadTopPlayers();
    }
}

// --- Manejadores de Eventos ---

function handleCrearSala() {
    playSound('ClickMouse', 0.3);
    if (!_state.currentUser || !_state.currentUser.username) {
        return showNotification("Debes iniciar sesión para crear una sala.", document.getElementById('notificaciones'), "warning");
    }
    _setLoadingFunc(true);
    _socket.emit("crear_sala", {});
}

function handleUnirseSala() {
    playSound('ClickMouse', 0.3);
    const codigo = (codigoSalaInput?.value || "").trim().toUpperCase();
    if (!_state.currentUser || !_state.currentUser.username) {
        return showNotification("Debes iniciar sesión para unirte.", document.getElementById('notificaciones'), "warning");
    }
    if (!codigo) {
        return showNotification("Ingresa el código de sala", document.getElementById('notificaciones'), "warning");
    }
    _setLoadingFunc(true);
    _socket.emit("unirse_sala", { id_sala: codigo });
}

function handleLobbyTabClick(event) {
    playSound('ClickMouse', 0.3);
    const target = event.currentTarget;

    // Desactivar todos los botones y contenidos
    [tabRules, tabRanking].forEach(tab => tab?.classList.remove('active'));
    [rulesContent, rankingContent].forEach(content => content?.classList.remove('active'));

    // Activar el botón y contenido correctos
    if (target === tabRules) {
        rulesContent?.classList.add('active');
    } else if (target === tabRanking) {
        rankingContent?.classList.add('active');
        loadTopPlayers(); // Carga ranking (ahora usa caché)
    }

    target?.classList.add('active'); // Activa la pestaña clickeada
}

function handleCopiarCodigo() {
    playSound('ClickMouse', 0.3);
    const codigo = codigoSalaActualDisplay?.textContent;
    if (!codigo) return;
    navigator.clipboard.writeText(codigo)
        .then(() => showNotification("Código copiado.", document.getElementById('notificaciones'), "success"))
        .catch(() => showNotification("No se pudo copiar.", document.getElementById('notificaciones'), "error"));
}
function handleIniciarJuego() {
    playSound('ClickMouse', 0.3);
    const idSala = codigoSalaActualDisplay?.textContent;
    if (idSala) {
        _socket.emit("iniciar_juego", { id_sala: idSala });
    }
}
function handleSalirSala() {
    playSound('ClickMouse', 0.3);
    const idSala = codigoSalaActualDisplay?.textContent;
    if (!idSala) return;
    if (confirm("¿Estás seguro de que quieres salir de la sala?")) {
        _setLoadingFunc(true);
        _socket.emit("salir_sala", { id_sala: idSala });
    }
}
function handleEnviarMensajeLobby() {
    playSound('ClickMouse', 0.3);
    const msg = mensajeLobbyInput?.value.trim();
    const idSalaActual = codigoSalaActualDisplay?.textContent; 
    if (!msg || !idSalaActual) return;
    _socket.emit("enviar_mensaje", { id_sala: idSalaActual, mensaje: msg });
    if(mensajeLobbyInput) mensajeLobbyInput.value = "";
}


// --- Funciones de API (fetch) y Renderizado ---

/** Carga y muestra el top 5 de jugadores. */
export async function loadTopPlayers() {
    if (!topPlayersContainer) return;

    const now = Date.now();
    // Usar caché si está cargado y no ha expirado (5 min)
    if (rankingCache.isLoaded && rankingCache.data && (now - rankingCache.lastLoaded < CACHE_DURATION_MS)) {
        console.log("Cargando Top 5 desde caché...");
        _displayTopPlayers(rankingCache.data);
        return;
    }
    
    // Evitar cargas múltiples si ya hay una en curso
    if (rankingCache.isLoading) return;

    rankingCache.isLoading = true;
    topPlayersContainer.innerHTML = '<div class="loading-rankings">Cargando rankings...</div>';
    
    try {
        const response = await fetch("/leaderboard");
        if (!response.ok) throw new Error('Network response was not ok');
        const rankings = await response.json();
        
        const top5 = rankings.slice(0, 5);
        rankingCache.data = top5; // Guardar en caché
        rankingCache.isLoaded = true;
        rankingCache.lastLoaded = Date.now();
        
        _displayTopPlayers(top5); // Mostrar los datos frescos
    } catch (error) {
        console.error("Error loading rankings:", error);
        topPlayersContainer.innerHTML = '<div class="loading-rankings">Error al cargar rankings</div>';
        rankingCache.isLoaded = false; // Permitir reintento
    } finally {
        rankingCache.isLoading = false;
    }
}

function _displayTopPlayers(players) {
    if (!topPlayersContainer) return;
    if (!players || players.length === 0) {
        topPlayersContainer.innerHTML = '<div class="loading-rankings">No hay jugadores registrados</div>';
        return;
    }
    topPlayersContainer.innerHTML = ""; // Limpiar
    players.forEach((player, index) => {
        const position = index + 1;
        let positionClass = "", trophy = "";
        if (position === 1) { positionClass = "gold"; trophy = "🥇"; }
        else if (position === 2) { positionClass = "silver"; trophy = "🥈"; }
        else if (position === 3) { positionClass = "bronze"; trophy = "🥉"; }
        else { trophy = `${position}`; }
        const gamesPlayed = player.games_played || 0;
        const gamesWon = player.games_won || 0;
        const winRate = gamesPlayed > 0 ? ((gamesWon / gamesPlayed) * 100).toFixed(1) : "0.0";
        const playerDiv = document.createElement("div");
        playerDiv.className = "player-rank";
        playerDiv.innerHTML = `
          <div class="rank-position ${positionClass}">${trophy}</div>
          <div class="player-info">
            <div class="player-name">${escapeHTML(player.username)} (Nvl ${player.level || 1})</div>
            <div class="player-stats">
              <div class="stat-item" title="Victorias">🏆<span>${gamesWon}</span></div>
              <div class="stat-item" title="Partidas">🎲<span>${gamesPlayed}</span></div>
              <div class="stat-item" title="Win Rate">📊<span>${winRate}%</span></div>
            </div>
          </div>
        `;
        topPlayersContainer.appendChild(playerDiv);
    });
}

/** Actualiza la UI de la sala de espera. */
export function updateWaitingRoomUI(data) {
    if (contadorJugadoresDisplay) contadorJugadoresDisplay.textContent = data.jugadores ?? '-';
    if (listaJugadoresDisplay) {
        listaJugadoresDisplay.innerHTML = "";
        (data.lista_jugadores || []).forEach(nombre => {
            const li = document.createElement("li");
            li.textContent = escapeHTML(nombre);
            listaJugadoresDisplay.appendChild(li);
        });
    }
    if (btnIniciarJuego) btnIniciarJuego.disabled = !data.puede_iniciar;
    if (logEventosDisplay && data.log_eventos) {
        logEventosDisplay.innerHTML = "";
        data.log_eventos.slice(-10).forEach(e => { 
            const li = document.createElement("li");
            li.textContent = escapeHTML(e);
            logEventosDisplay.appendChild(li);
        });
        logEventosDisplay.scrollTop = logEventosDisplay.scrollHeight;
    }
    if (codigoSalaActualDisplay && data.id_sala) {
         codigoSalaActualDisplay.textContent = data.id_sala;
    }
}

/** Añade un mensaje al chat del lobby/espera. */
export function appendLobbyChatMessage(data) {
    if (!chatMensajesLobbyDisplay) return;
    const texto = `[${data.timestamp}] <strong>${escapeHTML(data.jugador)}</strong>: ${escapeHTML(data.mensaje)}`;
    const div = document.createElement("div");
    div.innerHTML = texto;
    div.style.marginBottom = "4px";
    chatMensajesLobbyDisplay.appendChild(div);
    chatMensajesLobbyDisplay.scrollTop = chatMensajesLobbyDisplay.scrollHeight;
}


/**
 * Abre el modal de Glosario y carga los datos si es necesario.
 */
function openGlossaryModal() {
    playSound('OpenCloseModal', 0.3);
    if (!modalGlossary) return;

    modalGlossary.style.display = 'flex';
    
    // Cargar datos (usará caché si ya está cargado)
    loadGlossaryData();
}

/**
 * Cierra el modal de Glosario.
 */
function closeGlossaryModal() {
    playSound('OpenCloseModal', 0.2);
    if (modalGlossary) modalGlossary.style.display = 'none';
}


/**
 * Carga los datos de habilidades y perks desde la API (con caché).
 */
async function loadGlossaryData() {
    // Usar caché si ya está cargado
    if (glossaryCache.isLoaded) {
        _displayGlossaryAbilities(glossaryCache.abilities);
        _displayGlossaryPerks(glossaryCache.perks);
        return;
    }
    
    // Evitar cargas múltiples
    if (glossaryCache.isLoading) return;

    console.log("Cargando datos del glosario...");
    glossaryCache.isLoading = true;
    if (glossaryAbilitiesList) glossaryAbilitiesList.innerHTML = '<p>Cargando habilidades...</p>';
    if (glossaryPerksList) glossaryPerksList.innerHTML = '<p>Cargando perks...</p>';

    try {
        const [abilitiesResponse, perksResponse] = await Promise.all([
            fetch('/api/get_all_abilities'),
            fetch('/api/get_all_perks')
        ]);

        if (!abilitiesResponse.ok || !perksResponse.ok) {
            throw new Error('No se pudo conectar con la API del glosario.');
        }

        const abilitiesData = await abilitiesResponse.json();
        const perksData = await perksResponse.json();

        glossaryCache.abilities = abilitiesData;
        glossaryCache.perks = perksData;
        glossaryCache.isLoaded = true;

        _displayGlossaryAbilities(abilitiesData);
        _displayGlossaryPerks(perksData);

    } catch (error) {
        console.error("Error al cargar glosario:", error);
        if (glossaryAbilitiesList) glossaryAbilitiesList.innerHTML = `<p style="color: var(--danger);">Error al cargar habilidades.</p>`;
        if (glossaryPerksList) glossaryPerksList.innerHTML = `<p style="color: var(--danger);">Error al cargar perks.</p>`;
        glossaryCache.isLoaded = false; // Permitir reintento
    } finally {
        glossaryCache.isLoading = false;
    }
}

/**
 * Renderiza la lista de habilidades en el glosario.
 * @param {object} data - Datos de habilidades (ej. {ofensiva: [], ...})
 */
function _displayGlossaryAbilities(data) {
    if (!glossaryAbilitiesList || !data) return;
    glossaryAbilitiesList.innerHTML = "";

    const categorias = ['ofensiva', 'defensiva', 'movimiento', 'control'];

    for (const categoria of categorias) {
        const habilidades = data[categoria];
        if (!habilidades || habilidades.length === 0) continue;

        const categoriaTitle = document.createElement('h4');
        categoriaTitle.textContent = categoria.charAt(0).toUpperCase() + categoria.slice(1);
        categoriaTitle.style.cssText = "color: var(--text); border-bottom: 1px solid #374151; padding-bottom: 5px; margin-top: 10px;";
        glossaryAbilitiesList.appendChild(categoriaTitle);

        habilidades.forEach(hab => {
            const item = document.createElement("div");
            item.className = "glossary-item";
            item.innerHTML = `
                <div class="glossary-item-header">
                    <h4><span class="simbolo">${hab.simbolo}</span>${escapeHTML(hab.nombre)}</h4>
                    <span class="glossary-item-tag">CD: ${hab.cooldown_base}</span>
                </div>
                <p>${escapeHTML(hab.descripcion)}</p>
            `;
            glossaryAbilitiesList.appendChild(item);
        });
    }
}

/**
 * Renderiza la lista de perks en el glosario.
 * @param {object} data - Datos de perks (ej. {recarga_constante: {...}, ...})
 */
function _displayGlossaryPerks(data) {
    if (!glossaryPerksList || !data) return;
    glossaryPerksList.innerHTML = "";

    // Convertir el objeto en un array y clasificar por tier
    const perksPorTier = {
        basico: [],
        medio: [],
        alto: []
    };
    
    for (const perk of Object.values(data)) {
        if (perksPorTier[perk.tier]) {
            perksPorTier[perk.tier].push(perk);
        }
    }

    // Renderizar por tier
    for (const [tier, perks] of Object.entries(perksPorTier)) {
        if (!perks || perks.length === 0) continue;

        const tierTitle = document.createElement('h4');
        tierTitle.textContent = `Tier ${tier.charAt(0).toUpperCase() + tier.slice(1)}`;
        tierTitle.style.cssText = "color: var(--text); border-bottom: 1px solid #374151; padding-bottom: 5px; margin-top: 10px;";
        glossaryPerksList.appendChild(tierTitle);

        perks.forEach(perk => {
            const item = document.createElement("div");
            item.className = "glossary-item";
            const requiresHtml = perk.requires_habilidad 
                ? `<p class="requires">Requiere: ${escapeHTML(perk.requires_habilidad)}</p>` 
                : '';
                
            item.innerHTML = `
                <div class="glossary-item-header">
                    <h4>${escapeHTML(perk.nombre)}</h4>
                    <span class="glossary-item-tag">${escapeHTML(perk.tier)}</span>
                </div>
                <p>${escapeHTML(perk.desc)}</p>
                ${requiresHtml}
            `;
            glossaryPerksList.appendChild(item);
        });
    }
}
