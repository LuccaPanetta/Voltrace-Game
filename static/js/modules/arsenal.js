/* ===================================================================
   MÓDULO DE ARSENAL (Maestría de Kit) (arsenal.js)
   Maneja la UI y lógica del modal de Maestría.
   =================================================================== */

import { escapeHTML, playSound } from './utils.js';

// Referencias DOM
let modalArsenal, btnCerrarArsenal, btnShowArsenal;
let arsenalContent, arsenalLockMessage, arsenalKitList;

// Referencias externas
let _socket = null;
let _state = null;

const arsenalCache = {
    data: null,
    isLoaded: false,
    isLoading: false,
};

// Configuración de Maestría
const NIVEL_REQUERIDO_ARSENAL = 5;
const MAESTRIA_XP_POR_NIVEL_BASE = 150; 
const MAESTRIA_MAX_NIVEL = 10;

const MAESTRIA_RECOMPENSAS = {
    "tactico": [
        { level: 5, nombre: "Título: 'Táctico'" },
        { level: 10, nombre: "Animación: 'Sabotaje Sónico'" }
    ],
    "ingeniero": [
        { level: 5, nombre: "Título: 'Ingeniero'" },
        { level: 10, nombre: "Animación: 'Bomba de Pulso'" }
    ],
    "espectro": [
        { level: 5, nombre: "Título: 'Fantasma'" },
        { level: 10, nombre: "Animación: 'Fase Sombría'" }
    ],
    "guardian": [
        { level: 5, nombre: "Título: 'Guardián'" },
        { level: 10, nombre: "Animación: 'Escudo Reforzado'" }
    ],
    "estratega": [
        { level: 5, nombre: "Título: 'Estratega'" },
        { level: 10, nombre: "Animación: 'Doble Turno Etéreo'" }
    ]
};

export function initArsenal(socketRef, stateRef) {
    _socket = socketRef;
    _state = stateRef;
    modalArsenal = document.getElementById("modal-arsenal");
    btnCerrarArsenal = document.getElementById("btn-cerrar-arsenal");
    btnShowArsenal = document.getElementById("btn-show-arsenal");
    arsenalContent = document.getElementById("arsenal-content");
    arsenalLockMessage = document.getElementById("arsenal-lock-message");
    arsenalKitList = document.getElementById("arsenal-kit-list");
    btnShowArsenal?.addEventListener('click', openArsenalModal);
    btnCerrarArsenal?.addEventListener('click', closeArsenalModal);
    modalArsenal?.addEventListener('click', (e) => { if (e.target === modalArsenal) closeArsenalModal(); });
    arsenalKitList?.addEventListener('click', handleEquipTitleClick);
    console.log("Módulo Arsenal inicializado.");
}

function closeArsenalModal() {
    playSound('OpenCloseModal', 0.2);
    if(modalArsenal) modalArsenal.style.display = 'none';
}

/**
 * Abre el modal de Arsenal.
 */
function openArsenalModal() {
    playSound('OpenCloseModal', 0.3);
    const notifContainer = document.getElementById('notificaciones'); 
    if (!modalArsenal || !_state || !_state.currentUser || !_state.currentUser.username) {
         if (!_state || !_state.currentUser) {
            showNotification("Debes iniciar sesión para ver tu arsenal.", notifContainer, "warning");
         }
        return; 
    }
    modalArsenal.style.display = 'flex';
    const nivelCuenta = _state.currentUser.level || 1;
    
    if (nivelCuenta < NIVEL_REQUERIDO_ARSENAL) {
        if (arsenalLockMessage) arsenalLockMessage.style.display = 'block';
        if (arsenalKitList) arsenalKitList.style.display = 'none';
    } else {
        if (arsenalLockMessage) arsenalLockMessage.style.display = 'none';
        if (arsenalKitList) arsenalKitList.style.display = 'block';
        
        if (arsenalCache.isLoaded && arsenalCache.data) {
            // Cargar desde caché 
            console.log("Cargando Arsenal desde caché...");
            renderArsenal(arsenalCache.data);
        } else {
            // Cargar desde servidor 
            if (arsenalKitList) arsenalKitList.innerHTML = '<p style="text-align:center; color: var(--muted);">Cargando maestría...</p>';
            if (!arsenalCache.isLoading) {
                loadArsenalData(); // Usar la nueva función de precarga
            }
        }
    }
}

/**
 * Inicia la carga de datos de maestría (generalmente en la precarga).
 */
export function loadArsenalData() {
    if (arsenalCache.isLoading || arsenalCache.isLoaded) return;
    if (!_state.currentUser || _state.currentUser.level < NIVEL_REQUERIDO_ARSENAL) {
        // console.log("Precarga de Arsenal omitida (Nivel bajo).");
        return; 
    }
    console.log("Iniciando precarga de datos de Arsenal...");
    arsenalCache.isLoading = true;
    _socket.emit('arsenal:cargar_maestria');
}

/**
 * Invalida el caché. Se llama cuando el usuario gana XP de maestría.
 */
export function invalidateArsenalCache() {
    console.log("Invalidando caché de Arsenal...");
    arsenalCache.isLoaded = false;
    arsenalCache.data = null;
    arsenalCache.isLoading = false;
}

function calcularNivelMaestria(xp) {
    let level = 1;
    let xpAcumuladaNivel = 0;
    while (level < MAESTRIA_MAX_NIVEL) {
        const xpParaSiguiente = level * MAESTRIA_XP_POR_NIVEL_BASE;
        if (xp >= (xpAcumuladaNivel + xpParaSiguiente)) {
            xpAcumuladaNivel += xpParaSiguiente;
            level++;
        } else {
            break; 
        }
    }
    const xpParaSiguiente = level * MAESTRIA_XP_POR_NIVEL_BASE;
    const xpEnNivel = xp - xpAcumuladaNivel;
    if (level >= MAESTRIA_MAX_NIVEL) {
        return { level: MAESTRIA_MAX_NIVEL, xpEnNivel: xp, xpParaSiguiente: xp };
    }
    return { level, xpEnNivel, xpParaSiguiente };
}

/**
 * 
 * Recibe datos del socket, los GUARDA EN CACHÉ y llama al render.
 */
export function handleMaestriaData(maestriaData) {
    // Guardar en caché
    arsenalCache.data = maestriaData;
    arsenalCache.isLoaded = true;
    arsenalCache.isLoading = false;
    console.log("Caché de Arsenal recibido y guardado.");

    // Renderizar
    if (modalArsenal?.style.display === 'flex') {
        renderArsenal(maestriaData);
    }
}

/**
 * Función Pura de Renderizado.
 */
function renderArsenal(maestriaData) {
    if (!arsenalKitList) return;
    
    if (!maestriaData || maestriaData.length === 0) {
        arsenalKitList.innerHTML = '<p style="text-align:center; color: var(--muted);">Aún no tienes progreso de maestría. ¡Juega una partida (Nivel 5+)!</p>';
        return;
    }

    maestriaData.sort((a, b) => b.xp - a.xp);
    arsenalKitList.innerHTML = ""; 

    maestriaData.forEach(kit => {
        const { level, xpEnNivel, xpParaSiguiente } = calcularNivelMaestria(kit.xp);
        const item = document.createElement("div");
        item.className = "arsenal-kit-item";
        let xpTexto;
        if (level >= MAESTRIA_MAX_NIVEL) {
            xpTexto = `NIVEL MÁXIMO (${kit.xp} XP)`;
        } else {
            xpTexto = `${xpEnNivel} / ${xpParaSiguiente} XP`;
        }
        let recompensasHtml = "";
        const recompensasDefinidas = MAESTRIA_RECOMPENSAS[kit.kit_id] || [];
        
        recompensasDefinidas.forEach(rec => {
            const isUnlocked = level >= rec.level;
            const cssClass = isUnlocked ? 'unlocked' : 'locked';
            const isTitle = rec.nombre.startsWith("Título:");
            
            // Comprobar si este título es el que está equipado actualmente
            const isEquipped = isTitle && isUnlocked && _state.currentUser.equipped_title === rec.nombre;

            if (isTitle && isUnlocked) {
                // Es un Título y está desbloqueado: hacerlo un BOTÓN
                recompensasHtml += `
                    <button class="recompensa-item btn-equip-title ${cssClass}" 
                            title="Haz clic para equipar este título"
                            data-title-name="${escapeHTML(rec.nombre)}"
                            ${isEquipped ? 'disabled' : ''}>
                        ${isEquipped ? '✓ Equipado' : `Equipar ${escapeHTML(rec.nombre)}`}
                    </button>
                `;
            } else {
                // Es una Animación, o un Título bloqueado: hacerlo un DIV
                recompensasHtml += `
                    <div class="recompensa-item ${cssClass}" title="Se desbloquea en Maestría Nv. ${rec.level}">
                        ${isUnlocked ? '✓' : '🔒'} ${escapeHTML(rec.nombre)}
                    </div>
                `;
            }
        });
        
        item.innerHTML = `
            <div class="kit-maestria-header">
                <h4>${escapeHTML(kit.nombre)}</h4>
                <span>Maestría ${level}</span>
            </div>
            <div class.kit-maestria-progreso">
                <progress value="${xpEnNivel}" max="${xpParaSiguiente}"></progress>
                <p>${xpTexto}</p>
            </div>
            ${recompensasHtml ? `
            <div class="kit-recompensas">
                <h5>Recompensas de Maestría</h5>
                <div class="kit-recompensas-lista">
                    ${recompensasHtml}
                </div>
            </div>
            ` : ''}
        `;
        arsenalKitList.appendChild(item);
    });
}

/**
 * Maneja el clic en un botón de "equipar título".
 */
function handleEquipTitleClick(event) {
    const target = event.target.closest('.btn-equip-title');
    if (!target || target.disabled) return;

    const titleName = target.dataset.titleName;
    if (!titleName) return;
    
    playSound('ClickMouse', 0.4);

    // Deshabilitar todos los botones mientras se procesa
    document.querySelectorAll('.btn-equip-title').forEach(btn => {
        btn.disabled = true;
        if (btn === target) {
            btn.textContent = 'Equipando...';
        }
    });

    // Enviar al servidor
    _socket.emit('arsenal:equip_title', { title: titleName });
}