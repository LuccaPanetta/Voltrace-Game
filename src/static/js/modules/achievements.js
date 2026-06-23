/* ===================================================================
   MÓDULO DE LOGROS (achievements.js)
   Maneja la UI del modal de logros.
   =================================================================== */

import { escapeHTML, playSound, showNotification } from './utils.js';

// Referencias DOM
let modalAchievementsElement, btnCerrarAchievements, achievementsListDisplay, achievementsSummaryDisplay;
let btnShowAchievements; // Botón para abrir el modal

// Referencias externas
let _state = null;

const achievementsCache = {
    data: null,       // Aquí guardaremos los datos de progreso
    isLoaded: false,  // Se vuelve 'true' después de la primera carga
    isLoading: false, // Previene cargas múltiples
};

/**
 * Inicializa el módulo de logros.
 * @param {object} stateRef - Referencia al estado global.
 */
export function initAchievements(stateRef) { 
    _state = stateRef; 

    // Cachear elementos DOM
    modalAchievementsElement = document.getElementById("modal-achievements");
    btnCerrarAchievements = document.getElementById("btn-cerrar-achievements");
    achievementsListDisplay = document.getElementById("achievements-list");
    achievementsSummaryDisplay = document.getElementById("achievements-summary");
    btnShowAchievements = document.getElementById("btn-show-achievements");

    // Listeners
    btnShowAchievements?.addEventListener('click', openAchievementsModal);
    btnCerrarAchievements?.addEventListener('click', closeAchievementsModal);
    modalAchievementsElement?.addEventListener('click', (e) => { if (e.target === modalAchievementsElement) closeAchievementsModal(); });

    console.log("Módulo Achievements inicializado."); 
}

function closeAchievementsModal() {
    playSound('OpenCloseModal', 0.2);
    if(modalAchievementsElement) modalAchievementsElement.style.display = 'none';
}

/**
 * Abre el modal de logros. Ahora solo lee del caché.
 */
function openAchievementsModal() {
    playSound('OpenCloseModal', 0.3);
    const notifContainer = document.getElementById('notificaciones'); 

    if (!modalAchievementsElement || !_state || !_state.currentUser || !_state.currentUser.username) {
         if (!_state || !_state.currentUser) {
            showNotification("Debes iniciar sesión para ver los logros.", notifContainer, "warning");
         }
        return; 
    }

    modalAchievementsElement.style.display = 'flex';
    
    if (achievementsCache.isLoaded && achievementsCache.data) {
        console.log("Cargando logros desde caché...");
        renderAchievements(achievementsCache.data);
    } else {
        // Si no está cargado (precarga en curso o fallida), muestra 'Cargando...'
        console.log("Renderizando estado 'Cargando...' para logros.");
        if(achievementsListDisplay) achievementsListDisplay.innerHTML = '<p style="text-align:center; color: var(--muted);">Cargando logros...</p>';
        if (achievementsSummaryDisplay) achievementsSummaryDisplay.textContent = 'Cargando resumen...';
        
        if (!achievementsCache.isLoading) {
            loadAchievementsData();
        }
    }
}

/**
 * Función para cargar los datos de logros.
 * Llamada por 'main.js' durante la precarga.
 */
export async function loadAchievementsData() {
    if (achievementsCache.isLoading || achievementsCache.isLoaded) return;
    if (!_state.currentUser || !_state.currentUser.username) return;

    console.log("Iniciando precarga de datos de logros...");
    achievementsCache.isLoading = true;

    try {
        const response = await fetch(`/profile/${_state.currentUser.username}`);
        if (!response.ok) throw new Error("Error al cargar datos del perfil/logros");
        const data = await response.json();

        if (data.achievements && !data.achievements.error) {
            achievementsCache.data = data.achievements; // Guardar en caché
            achievementsCache.isLoaded = true;
            console.log("Caché de logros cargado exitosamente.");
            
            // Si el modal está abierto, renderizarlo
            if (modalAchievementsElement?.style.display === 'flex') {
                renderAchievements(achievementsCache.data);
            }
        } else {
            throw new Error(data.achievements?.error || "No se pudieron cargar los logros.");
        }
    } catch (error) {
        console.error("Error al cargar logros:", error);
        achievementsCache.isLoaded = false; // Permitir reintentar
        if (modalAchievementsElement?.style.display === 'flex') {
            if(achievementsListDisplay) achievementsListDisplay.innerHTML = `<p style="text-align:center; color: var(--danger);">Error al cargar: ${error.message}</p>`;
            if (achievementsSummaryDisplay) achievementsSummaryDisplay.textContent = 'Error al cargar';
        }
    } finally {
        achievementsCache.isLoading = false;
    }
}

/** Renderiza la lista de logros en el modal. */
function renderAchievements(progressData) {
    if (!achievementsListDisplay || !progressData || !progressData.achievements) return;
    if (achievementsSummaryDisplay) {
        achievementsSummaryDisplay.textContent = `Completado: ${progressData.unlocked}/${progressData.total} (${progressData.percentage.toFixed(1)}%)`;
    }
    achievementsListDisplay.innerHTML = ""; 
    progressData.achievements.forEach(ach => {
        const item = document.createElement("div");
        item.className = `achievement-item ${ach.unlocked ? 'unlocked' : 'locked'}`;
        const progressPercent = ach.target_value > 0 ? (ach.current_value / ach.target_value) * 100 : (ach.unlocked ? 100 : 0);
        const progressBarWidth = Math.min(100, progressPercent); 
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

/**
 * Invalida (borra) el caché de logros.
 * Se debe llamar cuando el usuario desbloquea un logro o sube de nivel.
 */
export function invalidateAchievementsCache() {
    console.log("Invalidando caché de logros...");
    achievementsCache.isLoaded = false;
    achievementsCache.data = null;
    
    // Si el modal está abierto, recargarlo
    if (modalAchievementsElement?.style.display === 'flex') {
        console.log("Modal de logros abierto, forzando recarga de datos...");
        loadAchievementsData(); 
    }
}