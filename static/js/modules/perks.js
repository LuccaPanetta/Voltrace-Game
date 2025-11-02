/* ===================================================================
   MÓDULO DE PERKS (perks.js)
   Maneja la UI y lógica del modal de compra y selección de perks.
   =================================================================== */

import { escapeHTML, playSound, showNotification } from './utils.js';

// Referencias DOM
let modalPerksElement, pmActualDisplay, perksActivosListDisplay;
let packBasicoBtn, packIntermedioBtn, packAvanzadoBtn;
let perkOfferContainerDisplay, btnCerrarPerks;

// Referencias a estado/funciones externas
let _socket = null;
let _state = null;   
let _estadoJuego = null;
let _idSala = null; 

// Variable global simulada para PERKS_INFO (debe cargarse desde algún lado)
let PERKS_INFO = {}; // Inicialmente vacío

/**
 * Carga la configuración de perks (simulado).
 * En una app real, esto podría ser un fetch al servidor.
 */
export function loadPerksConfig(config) {
    PERKS_INFO = config;
    console.log("Perks config loaded into perks.js");
}

/**
 * Inicializa el módulo de perks.
 * @param {object} socketRef - Instancia de Socket.IO.
 * @param {object} stateRef - Referencia al usuario actual.
 * @param {object} idSalaRef - Referencia al ID de la sala.
 * @param {object} estadoJuegoRef - Referencia al estado del juego.
 */
export function initPerks(socketRef, stateRef, idSalaRef, estadoJuegoRef) {
    _socket = socketRef;
    _state = stateRef; 
    _idSala = idSalaRef; 
    _estadoJuego = estadoJuegoRef; 

    // Cachear elementos DOM
    modalPerksElement = document.getElementById("modal-perks");
    btnCerrarPerks = document.getElementById("btn-cerrar-perks");
    pmActualDisplay = document.getElementById("pm-actual");
    perksActivosListDisplay = document.getElementById("perks-activos-list");
    packBasicoBtn = document.getElementById("btn-pack-basico");
    packIntermedioBtn = document.getElementById("btn-pack-intermedio");
    packAvanzadoBtn = document.getElementById("btn-pack-avanzado");
    perkOfferContainerDisplay = document.getElementById("perk-offer-container");

    // Asignar listeners
    btnCerrarPerks?.addEventListener("click", closePerkModal);
    packBasicoBtn?.addEventListener("click", handleBuyPerkPack);
    packIntermedioBtn?.addEventListener("click", handleBuyPerkPack);
    packAvanzadoBtn?.addEventListener("click", handleBuyPerkPack);
}

/** Abre el modal de perks y actualiza su contenido. */
export function openPerkModal() {
    playSound('OpenCloseModal', 0.3);
    if (!_estadoJuego || !_state.currentUser || !modalPerksElement || !pmActualDisplay || !perksActivosListDisplay) {
        console.warn("Se intentó abrir perks sin estado de juego, usuario o elementos DOM.");
        return;
    }

    const miEstado = _estadoJuego.jugadores?.find((j) => j.nombre === _state.currentUser.username);

    if (!miEstado) {
        const notifContainer = document.getElementById('notificaciones');
        showNotification("Error: No se puede cargar tu estado actual para perks.", notifContainer, "error");
        console.error("No se encontró el estado del jugador actual para perks.");
        return; 
    }
    const misPM = miEstado.pm || 0;

    pmActualDisplay.textContent = misPM;

    // Renderizar Perks Activos
    const activos = miEstado.perks_activos || [];
    perksActivosListDisplay.innerHTML = "";
    if (activos.length === 0) {
        perksActivosListDisplay.textContent = "Ninguno";
    } else {
        const perksPorTier = { alto: [], medio: [], basico: [] };
        activos.forEach(perkId => {
            const perkInfo = PERKS_INFO ? PERKS_INFO[perkId] : { nombre: perkId, tier: 'basico' };
            const tier = perkInfo.tier || 'basico';
            if (perksPorTier[tier]) {
                perksPorTier[tier].push(perkInfo);
            } else {
                perksPorTier.basico.push(perkInfo); // Fallback
            }
        });

        ['alto', 'medio', 'basico'].forEach(tier => {
            if (perksPorTier[tier].length > 0) {
                const tierContainer = document.createElement('div');
                tierContainer.className = `active-perks-tier tier-${tier}`;
                tierContainer.innerHTML = `<strong class="tier-title">${tier.charAt(0).toUpperCase() + tier.slice(1)}:</strong> `;
                perksPorTier[tier].forEach(p => {
                    const perkSpan = document.createElement('span');
                    perkSpan.className = `active-perk-tag perk-tier-${p.tier || 'basico'}`;
                    perkSpan.textContent = p.nombre || perkId;
                    tierContainer.appendChild(perkSpan);
                });
                perksActivosListDisplay.appendChild(tierContainer);
            }
        });
    }

    // Actualizar estado de botones de compra
    reactivarBotonesPackSiEsPosible(misPM);

    // Limpiar oferta anterior y mostrar modal
    if(perkOfferContainerDisplay) perkOfferContainerDisplay.innerHTML = "";
    if (btnCerrarPerks) btnCerrarPerks.style.display = 'block';
    modalPerksElement.style.display = "flex";

    if (_socket && _idSala && _idSala.value) {
        _socket.emit("solicitar_precios_perks", { id_sala: _idSala.value });
    }
}

/** Cierra el modal de perks. */
function closePerkModal() {
    playSound('OpenCloseModal', 0.2);
    if (modalPerksElement) modalPerksElement.style.display = "none";
    reactivarBotonesPackSiEsPosible(); // Reactiva botones al cerrar
}

/** Maneja el clic en un botón de compra de pack. */
function handleBuyPerkPack(event) {
    if (!_state.idSala.value) return;
    playSound('ClickMouse', 0.4);

    const packType = event.currentTarget.dataset.packType;
    // Asignar costes base (podrían venir de config)
    const costs = { basico: 4, intermedio: 8, avanzado: 12 };
    const packCost = costs[packType] || 999; // Coste default alto

    const miEstado = _estadoJuego?.jugadores?.find((j) => j.nombre === _state.currentUser?.username);
    if (!miEstado || (miEstado.pm || 0) < packCost) {
        showNotification("No tienes suficientes PM para este pack.", document.getElementById('notificaciones'), "error");
        return;
    }

    if (perkOfferContainerDisplay) {
        perkOfferContainerDisplay.innerHTML = '<p style="text-align:center; color: var(--muted);">Obteniendo oferta...</p>';
    }
    _socket.emit("comprar_perk", { id_sala: _state.idSala.value, tipo_pack: packType });
}

/** Muestra la oferta de perks recibida del servidor. */
export function displayPerkOffer(data) {
    if (!perkOfferContainerDisplay || !pmActualDisplay || !modalPerksElement) return;

     // Siempre actualiza los PM mostrados
    if (data.pm_restantes !== undefined) {
        pmActualDisplay.textContent = data.pm_restantes;
        reactivarBotonesPackSiEsPosible(data.pm_restantes);
    }

    // Limpiar contenedor de oferta
    perkOfferContainerDisplay.innerHTML = "";

    if (!data.exito) {
        showNotification(data.mensaje || "Error al comprar pack.", document.getElementById('notificaciones'), "error");
        perkOfferContainerDisplay.innerHTML = `<p style="text-align:center; color: var(--danger);">${escapeHTML(data.mensaje || "Error.")}</p>`;
        // Como falló la compra inicial, no hay oferta pendiente, reactivar botones y mostrar X
        reactivarBotonesPackSiEsPosible();
        if (btnCerrarPerks) btnCerrarPerks.style.display = 'block';
        return;
    }

    // Deshabilitar botones de pack y ocultar 'X' porque hay oferta pendiente
    if (packBasicoBtn) packBasicoBtn.disabled = true;
    if (packIntermedioBtn) packIntermedioBtn.disabled = true;
    if (packAvanzadoBtn) packAvanzadoBtn.disabled = true;
    if (btnCerrarPerks) btnCerrarPerks.style.display = 'none';

    const offerTitle = document.createElement("h4");
    offerTitle.textContent = data.mensaje || "Elige un Perk:";
    perkOfferContainerDisplay.appendChild(offerTitle);

    if (!data.oferta || data.oferta.length === 0) {
        perkOfferContainerDisplay.innerHTML += '<p style="text-align:center; color: var(--muted);">No hay perks disponibles en este pack.</p>';
        // No hay nada que elegir, reactivar botones y mostrar 'X'
        reactivarBotonesPackSiEsPosible();
        if (btnCerrarPerks) btnCerrarPerks.style.display = 'block';
        return;
    }

    // Crear botones para cada perk ofrecido
    data.oferta.forEach((perk) => {
        const perkButton = document.createElement("button");
        perkButton.className = "perk-offer-item";
        perkButton.dataset.perkId = perk.id;
        perkButton.dataset.coste = data.coste; // Guardar coste original del pack
        perkButton.classList.add(`perk-tier-${perk.tier || 'basico'}`);

        perkButton.innerHTML = `
          <div>
              <strong>${escapeHTML(perk.nombre || perk.id)}</strong>
              <span class="perk-tier">${escapeHTML(perk.tier || 'basico')}</span>
          </div>
          <small>${escapeHTML(perk.desc || 'Descripción no disponible.')}</small>
        `;
        perkButton.onclick = handleSelectPerk; // Asignar handler
        perkOfferContainerDisplay.appendChild(perkButton);
    });
}

/** Maneja el clic en un botón de perk ofrecido. */
function handleSelectPerk(event) {
    if (!_idSala || !_state.currentUser) return;
    playSound('ClickMouse', 0.3);

    const perkId = event.currentTarget.dataset.perkId;
    const costeOriginalPack = parseInt(event.currentTarget.dataset.coste);

    if (!perkId || isNaN(costeOriginalPack)) {
        showNotification("Error interno al seleccionar perk.", document.getElementById('notificaciones'), "error");
        return;
    }

    if (perkOfferContainerDisplay) {
        perkOfferContainerDisplay.innerHTML = '<p style="text-align:center; color: var(--muted);">Activando perk...</p>';
    }

    _socket.emit("seleccionar_perk", {
        id_sala: _idSala.value,
        perk_id: perkId,
        coste: costeOriginalPack,
    });
}

/** Callback que se llama cuando el servidor confirma la activación (o fallo). */
export function handlePerkActivated(data) {
    // Actualizar PM si el servidor los envía
    if (data.pm_restantes !== undefined && pmActualDisplay) {
        pmActualDisplay.textContent = data.pm_restantes;
    }
    const notifContainer = document.getElementById('notificaciones');

    if (data.exito) {
        playSound('PerkActivate', 0.4);
        showNotification(data.mensaje || "Perk activado.", notifContainer, "success");
        if (modalPerksElement) modalPerksElement.style.display = "none"; // Cerrar modal
    } else {
        playSound('Error', 0.3);
        showNotification(data.mensaje || "No se pudo activar el perk.", notifContainer, "error");
        if (perkOfferContainerDisplay) perkOfferContainerDisplay.innerHTML = ""; // Limpiar oferta fallida
    }

    // Siempre reactivar botones y mostrar 'X' después de la respuesta
    reactivarBotonesPackSiEsPosible();
    if (btnCerrarPerks) btnCerrarPerks.style.display = 'block';
}

/** Reactiva los botones de compra de pack según los PM. */
function reactivarBotonesPackSiEsPosible(pmForzado) {
    let misPM;
    if (pmForzado !== undefined) {
        misPM = pmForzado;
    } else {
        const miEstado = _estadoJuego?.jugadores?.find((j) => j.nombre === _state.currentUser?.username);
        misPM = miEstado?.pm ?? parseInt(pmActualDisplay?.textContent || '0');
    }

    if (packBasicoBtn) {
        const cost = parseInt(packBasicoBtn.dataset.cost) || 4; 
        packBasicoBtn.disabled = misPM < cost;
        packBasicoBtn.classList.toggle('affordable', misPM >= cost);
    }
    if (packIntermedioBtn) {
        const cost = parseInt(packIntermedioBtn.dataset.cost) || 8; 
        packIntermedioBtn.disabled = misPM < cost;
        packIntermedioBtn.classList.toggle('affordable', misPM >= cost);
    }
    if (packAvanzadoBtn) {
        const cost = parseInt(packAvanzadoBtn.dataset.cost) || 12; 
        packAvanzadoBtn.disabled = misPM < cost;
        packAvanzadoBtn.classList.toggle('affordable', misPM >= cost);
    }

}
/**
 * Actualiza el texto y data-cost de los precios en los botones del modal.
 * @param {object} costos - Objeto {basico: 4, intermedio: 8, avanzado: 12}
 */
export function updatePerkPrices(costos) {
    if (!costos) return;

    if (packBasicoBtn) {
        // Busca el <small> que contiene el coste
        const small = packBasicoBtn.querySelector('small');
        if (small) small.textContent = `Coste: ${costos.basico} PM`;
        packBasicoBtn.dataset.cost = costos.basico;
    }
    if (packIntermedioBtn) {
        const small = packIntermedioBtn.querySelector('small');
        if (small) small.textContent = `Coste: ${costos.intermedio} PM`;
        packIntermedioBtn.dataset.cost = costos.intermedio;
    }
    if (packAvanzadoBtn) {
        const smallCost = packAvanzadoBtn.querySelector('small');
        if (smallCost) smallCost.textContent = `Coste: ${costos.avanzado} PM`;
        packAvanzadoBtn.dataset.cost = costos.avanzado;
    }

    // Volver a-evaluar si los botones están habilitados con los nuevos precios
    reactivarBotonesPackSiEsPosible();
}