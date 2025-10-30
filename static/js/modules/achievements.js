/* ===================================================================
   MÓDULO DE LOGROS (achievements.js)
   Maneja la UI del modal de logros.
   =================================================================== */

import { escapeHTML, playSound, showNotification } from './utils.js';

// Referencias DOM
let modalAchievementsElement, btnCerrarAchievements, achievementsListDisplay, achievementsSummaryDisplay;
let btnShowAchievements; // Botón para abrir el modal

// Referencias externas
let _currentUser = null;
let _state = null;

/**
 * Inicializa el módulo de logros.
 * @param {object} currentUserRef - Referencia al usuario actual.
 */
export function initAchievements(stateRef) { 
    _state = stateRef; 

    // Cachear elementos DOM (asegúrate que estas líneas estén DESPUÉS de _state = stateRef;)
    modalAchievementsElement = document.getElementById("modal-achievements");
    btnCerrarAchievements = document.getElementById("btn-cerrar-achievements");
    achievementsListDisplay = document.getElementById("achievements-list");
    achievementsSummaryDisplay = document.getElementById("achievements-summary");
    btnShowAchievements = document.getElementById("btn-show-achievements");

    // Listeners (asegúrate que estén DESPUÉS de _state = stateRef;)
    btnShowAchievements?.addEventListener('click', openAchievementsModal);
    btnCerrarAchievements?.addEventListener('click', closeAchievementsModal);
    modalAchievementsElement?.addEventListener('click', (e) => { if (e.target === modalAchievementsElement) closeAchievementsModal(); });

    console.log("Módulo Achievements inicializado."); 
}

function closeAchievementsModal() {
    playSound('OpenCloseModal', 0.2);
    if(modalAchievementsElement) modalAchievementsElement.style.display = 'none';
}

/** Abre el modal de logros y carga los datos del usuario. */
async function openAchievementsModal() {
    playSound('OpenCloseModal', 0.3);
    const notifContainer = document.getElementById('notificaciones'); // Necesario para showNotification

    if (!modalAchievementsElement || !_state || !_state.currentUser || !_state.currentUser.username) {
         if (!_state || !_state.currentUser) {
            showNotification("Debes iniciar sesión para ver los logros.", notifContainer, "warning");
         }
        return; // Salir si no hay usuario o elementos
    }

    modalAchievementsElement.style.display = 'flex';
    achievementsListDisplay.innerHTML = '<p style="text-align:center; color: var(--muted);">Cargando logros...</p>';
    if (achievementsSummaryDisplay) achievementsSummaryDisplay.textContent = 'Cargando resumen...';

    try {
        const response = await fetch(`/profile/${_state.currentUser.username}`);
        if (!response.ok) throw new Error("Error al cargar datos del perfil/logros");
        const data = await response.json();

        if (data.achievements && !data.achievements.error) {
            renderAchievements(data.achievements);
        } else {
            throw new Error(data.achievements?.error || "No se pudieron cargar los logros.");
        }
    } catch (error) {
        console.error("Error al cargar logros:", error);
        achievementsListDisplay.innerHTML = `<p style="text-align:center; color: var(--danger);">Error al cargar: ${error.message}</p>`;
        if (achievementsSummaryDisplay) achievementsSummaryDisplay.textContent = 'Error al cargar';
    }
}

/** Renderiza la lista de logros en el modal. */
function renderAchievements(progressData) {
    if (!achievementsListDisplay || !progressData || !progressData.achievements) return;

    // Actualizar resumen
    if (achievementsSummaryDisplay) {
        achievementsSummaryDisplay.textContent = `Completado: ${progressData.unlocked}/${progressData.total} (${progressData.percentage.toFixed(1)}%)`;
    }

    achievementsListDisplay.innerHTML = ""; // Limpiar

    progressData.achievements.forEach(ach => {
        const item = document.createElement("div");
        item.className = `achievement-item ${ach.unlocked ? 'unlocked' : 'locked'}`;

        const progressPercent = ach.target_value > 0 ? (ach.current_value / ach.target_value) * 100 : (ach.unlocked ? 100 : 0);
        const progressBarWidth = Math.min(100, progressPercent); // Asegurar que no pase de 100

        item.innerHTML = `
            <div class="achievement-header">
                <div class="achievement-icon">${ach.icon || '🏆'}</div>
                <div class="achievement-info">
                    <h4 class="achievement-name">${escapeHTML(ach.name)}</h4>
                    <p class="achievement-desc">${escapeHTML(ach.desc)}</p>
                </div>
                <div class="achievement-xp">+${ach.xp_reward || 0} XP</div>
            </div>
            ${ach.target_value > 1 ? `
            <div class="achievement-progress">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progressBarWidth}%;"></div>
                </div>
                <div class="progress-text">${ach.current_value}/${ach.target_value}</div>
            </div>
            ` : ''}
            ${ach.unlocked && ach.unlocked_at ? `
            <div class="unlocked-date">
                Desbloqueado: ${new Date(ach.unlocked_at).toLocaleDateString()}
            </div>
            ` : ''}
        `;
        achievementsListDisplay.appendChild(item);
    });
}