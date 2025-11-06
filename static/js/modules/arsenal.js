/* ===================================================================
   MÓDULO DE ARSENAL (Maestría de Kit)
   =================================================================== */

import { escapeHTML, playSound } from './utils.js';

// Referencias DOM
let modalArsenal, btnCerrarArsenal, btnShowArsenal;
let arsenalContent, arsenalLockMessage, arsenalKitList;

// Referencias externas
let _socket = null;
let _state = null;

// Configuración de Maestría 
const NIVEL_REQUERIDO_ARSENAL = 5;

// Definimos los niveles y recompensas
const MAESTRIA_XP_POR_NIVEL = 150; 
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

/**
 * Inicializa el módulo de Arsenal.
 * @param {object} socketRef - Instancia de Socket.IO.
 * @param {object} stateRef - Referencia al estado global.
 */
export function initArsenal(socketRef, stateRef) {
    _socket = socketRef;
    _state = stateRef;

    // Cachear elementos DOM
    modalArsenal = document.getElementById("modal-arsenal");
    btnCerrarArsenal = document.getElementById("btn-cerrar-arsenal");
    btnShowArsenal = document.getElementById("btn-show-arsenal");
    arsenalContent = document.getElementById("arsenal-content");
    arsenalLockMessage = document.getElementById("arsenal-lock-message");
    arsenalKitList = document.getElementById("arsenal-kit-list");

    // Listeners
    btnShowArsenal?.addEventListener('click', openArsenalModal);
    btnCerrarArsenal?.addEventListener('click', closeArsenalModal);
    modalArsenal?.addEventListener('click', (e) => { if (e.target === modalArsenal) closeArsenalModal(); });

    console.log("Módulo Arsenal inicializado.");
}

function closeArsenalModal() {
    playSound('OpenCloseModal', 0.2);
    if(modalArsenal) modalArsenal.style.display = 'none';
}

/**
 * Abre el modal de Arsenal.
 * Comprueba el nivel del jugador y solicita los datos de maestría.
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
    
    // Comprobar si el jugador ha desbloqueado el sistema
    const nivelCuenta = _state.currentUser.level || 1;
    
    if (nivelCuenta < NIVEL_REQUERIDO_ARSENAL) {
        // Mostrar mensaje de bloqueo
        if (arsenalLockMessage) arsenalLockMessage.style.display = 'block';
        if (arsenalKitList) arsenalKitList.style.display = 'none';
    } else {
        // Mostrar contenido y cargar datos
        if (arsenalLockMessage) arsenalLockMessage.style.display = 'none';
        if (arsenalKitList) arsenalKitList.style.display = 'block';
        
        // Mostrar "Cargando..." y pedir datos al servidor
        if (arsenalKitList) arsenalKitList.innerHTML = '<p style="text-align:center; color: var(--muted);">Cargando maestría...</p>';
        _socket.emit('arsenal:cargar_maestria');
    }
}

/**
 * Calcula el Nivel y XP requerido para la Maestría.
 * @param {number} xp - XP total del kit.
 * @returns {object} - { level, xpEnNivel, xpParaSiguiente }
 */
function calcularNivelMaestria(xp) {
    let level = 1;
    let xpAcumuladaNivel = 0;
    
    // (Nivel * 150)
    // Nv 1 -> Nv 2 = 1 * 150 = 150 XP
    // Nv 2 -> Nv 3 = 2 * 150 = 300 XP (Total: 450)
    // Nv 3 -> Nv 4 = 3 * 150 = 450 XP (Total: 900)
    
    while (level < MAESTRIA_MAX_NIVEL) {
        const xpParaSiguiente = level * MAESTRIA_XP_POR_NIVEL;
        if (xp >= (xpAcumuladaNivel + xpParaSiguiente)) {
            xpAcumuladaNivel += xpParaSiguiente;
            level++;
        } else {
            break; // No puede subir más
        }
    }

    const xpParaSiguiente = level * MAESTRIA_XP_POR_NIVEL;
    const xpEnNivel = xp - xpAcumuladaNivel;
    
    if (level >= MAESTRIA_MAX_NIVEL) {
        return { level: MAESTRIA_MAX_NIVEL, xpEnNivel: xp, xpParaSiguiente: xp };
    }
    
    return { level, xpEnNivel, xpParaSiguiente };
}

/**
 * Renderiza la lista de maestrías recibida del servidor.
 * Esta función es llamada por socketHandlers.
 * @param {Array} maestriaData - Lista de objetos {kit_id, nombre, xp}
 */
export function handleMaestriaData(maestriaData) {
    if (!arsenalKitList) return;
    
    if (!maestriaData || maestriaData.length === 0) {
        arsenalKitList.innerHTML = '<p style="text-align:center; color: var(--muted);">Aún no tienes progreso de maestría. ¡Juega una partida (Nivel 5+)!</p>';
        return;
    }

    // Ordenar (ej. por XP descendente)
    maestriaData.sort((a, b) => b.xp - a.xp);
    
    arsenalKitList.innerHTML = ""; // Limpiar "Cargando..."

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

        // --- Recompensas ---
        let recompensasHtml = "";
        const recompensasDefinidas = MAESTRIA_RECOMPENSAS[kit.kit_id] || [];
        
        recompensasDefinidas.forEach(rec => {
            const isUnlocked = level >= rec.level;
            const cssClass = isUnlocked ? 'unlocked' : 'locked';
            recompensasHtml += `
                <div class="recompensa-item ${cssClass}" title="Se desbloquea en Maestría Nv. ${rec.level}">
                    ${isUnlocked ? '✓' : '🔒'} ${escapeHTML(rec.nombre)}
                </div>
            `;
        });
        // --- Fin Recompensas ---
        
        item.innerHTML = `
            <div class="kit-maestria-header">
                <h4>${escapeHTML(kit.nombre)}</h4>
                <span>Maestría ${level}</span>
            </div>
            <div class="kit-maestria-progreso">
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