/* ===================================================================
   MÓDULO DE UTILIDADES (utils.js)
   Funciones helper reutilizables para UI y lógica general.
   =================================================================== */

/**
 * Muestra una pantalla específica y oculta las demás.
 * @param {string} screenName - El nombre de la pantalla (auth, lobby, waiting, game).
 * @param {object} screenElements - Objeto con referencias a los elementos de pantalla.
 */
export function show(screenName, screenElements) {
    Object.values(screenElements).forEach((s) => s?.classList.remove("active"));
    if (screenElements[screenName]) {
        screenElements[screenName].classList.add("active");
    } else {
        console.error("Pantalla no encontrada:", screenName);
    }
}

/**
 * Muestra u oculta el indicador de carga global.
 * @param {boolean} v - True para mostrar, false para ocultar.
 * @param {HTMLElement} loadingElement - Referencia al elemento de carga.
 */
export function setLoading(v, loadingElement) {
    if (!loadingElement) return;
    loadingElement.style.display = v ? "flex" : "none";
}

// Estado para manejo de audio
let _hasInteracted = false;
let _interactionListenerAdded = false;

/**
 * Reproduce un efecto de sonido. Maneja la restricción de interacción del navegador.
 * @param {string} soundName - Nombre del archivo (sin .mp3) en /static/sounds/
 * @param {number} [volume=0.5] - Volumen (0.0 a 1.0)
 */
export function playSound(soundName, volume = 0.5) {
    // Si el contexto de audio no está listo y no ha habido interacción, esperar.
    if (!_hasInteracted && (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined')) {
        console.log("Sound deferred: User hasn't interacted yet.");
        if (!_interactionListenerAdded) {
            const interactionEvents = ['click', 'keydown', 'touchstart'];
            const enableAudio = () => {
                _hasInteracted = true;
                console.log("User interaction detected, audio enabled.");
                interactionEvents.forEach(event => document.body.removeEventListener(event, enableAudio));
            };
            interactionEvents.forEach(event => document.body.addEventListener(event, enableAudio, { once: true }));
            _interactionListenerAdded = true;
        }
        return; // No intentar reproducir aún
    }

    // Intentar reproducir el sonido
    try {
        const soundPath = `/static/sounds/${soundName}.mp3`;
        const audio = new Audio(soundPath);
        audio.volume = Math.max(0, Math.min(1, volume));

        audio.play().catch(error => {
            // Silenciar errores comunes si el usuario no interactuó (aunque intentamos prevenirlo)
            if (error.name !== 'NotAllowedError') {
                console.warn(`Could not play sound "${soundName}":`, error);
            }
        });
    } catch (error) {
        console.error(`Error creating audio for "${soundName}":`, error);
    }
}

/**
 * Muestra una notificación temporal (toast).
 * @param {string} message - El mensaje a mostrar.
 * @param {HTMLElement} container - El elemento contenedor de notificaciones.
 * @param {string} [type="info"] - Tipo (info, success, error, warning).
 * @param {number} [duration=3000] - Duración en milisegundos.
 */
export function showNotification(message, container, type = "info", duration = 3000) {
    if (!container) {
        console.error("Notification container not provided!");
        alert(message); // Fallback
        return;
    }

    const notification = document.createElement("div");
    notification.className = `toast toast-${type}`;
    notification.textContent = message;

    notification.style.cssText = `
      background: ${
        type === "error" ? "var(--danger)" :
        type === "success" ? "var(--success)" :
        type === "warning" ? "var(--warning)" :
        "var(--panel)"
      };
      color: white;
      padding: 10px 15px;
      border-radius: 6px;
      margin-bottom: 8px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.2);
      opacity: 0;
      transition: opacity 0.3s ease, transform 0.3s ease;
      transform: translateX(100%);
      max-width: 350px;
      word-wrap: break-word;
    `;

    container.appendChild(notification);

    // Animar entrada
    setTimeout(() => {
        notification.style.opacity = "1";
        notification.style.transform = "translateX(0)";
    }, 10);

    // Animar salida y eliminar
    setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transform = "translateX(100%)";
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

/**
 * Muestra la notificación interactiva de invitación a sala.
 * @param {object} data - Datos de la invitación {id, sender, room_id, recipient}.
 * @param {HTMLElement} container - Contenedor de notificaciones.
 * @param {object} socket - Instancia de Socket.IO.
 * @param {object} state - Objeto de estado global (para leer idSala actual, currentUser).
 * @param {function} setLoadingFunc - Referencia a la función setLoading.
 * @param {function} showFunc - Referencia a la función show.
 * @param {object} screenElements - Referencias a las pantallas.
 */
export function manejarInvitacion(data, container, socket, state, setLoadingFunc, showFunc, screenElements) {
    if (!container || !data || !socket || !state) return;

    const notification = document.createElement("div");
    notification.className = "toast toast-info";
    notification.style.cssText = `
        /* ... (mismos estilos que showNotification, ajustados) ... */
        background: var(--panel); color: var(--text); padding: 10px 15px; border-radius: 6px; margin-bottom: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2); opacity: 0; transition: opacity 0.3s ease, transform 0.3s ease;
        transform: translateX(100%); display: flex; align-items: center; justify-content: space-between;
        max-width: 350px; word-wrap: break-word;
    `;

    notification.innerHTML = `<span>🎮 ${escapeHTML(data.sender)} te invita a la sala ${escapeHTML(data.room_id)}</span>`;

    const joinButton = document.createElement("button");
    joinButton.textContent = "Unirse";
    joinButton.className = "btn-success";
    joinButton.style.cssText = "margin-left: 10px; padding: 4px 8px; font-size: 0.9em; flex-shrink: 0;";

    joinButton.onclick = (e) => {
        e.stopPropagation();
        playSound('ClickMouse', 0.3);

        if (!state.currentUser || !state.currentUser.username) {
            showNotification("Debes iniciar sesión para unirte.", container, "error");
            return;
        }

        // Lógica de confirmación si ya está en sala
        if (state.idSala && (screenElements.waiting?.classList.contains("active") || screenElements.game?.classList.contains("active"))) {
            if (!confirm("Ya estás en una sala. ¿Quieres salir y unirte a la nueva?")) {
                return;
            }
            socket.emit("salir_sala", { id_sala: state.idSala }); // Sale de la actual
        }

        setLoadingFunc(true);
        socket.emit("unirse_sala", { id_sala: data.room_id }); // Intenta unirse a la nueva
        notification.remove();
    };

    const rejectButton = document.createElement("button");
    rejectButton.textContent = "Rechazar";
    rejectButton.className = "btn-danger";
    rejectButton.style.cssText = "margin-left: 5px; padding: 4px 8px; font-size: 0.9em; flex-shrink: 0;";
    rejectButton.onclick = () => {
        playSound('ClickMouse', 0.2);
        notification.remove();
        // Opcional: Notificar al servidor del rechazo (si implementado)
        // socket.emit('respond_to_invitation', { invitation_id: data.id, response: 'reject' });
    };

    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = 'flex';
    buttonContainer.appendChild(joinButton);
    buttonContainer.appendChild(rejectButton);
    notification.appendChild(buttonContainer);

    container.appendChild(notification);

    // Animar entrada y cierre automático
    setTimeout(() => {
        notification.style.opacity = "1";
        notification.style.transform = "translateX(0)";
    }, 10);
    setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transform = "translateX(100%)";
        setTimeout(() => notification.remove(), 300);
    }, 15000); // 15 segundos
}

/**
 * Muestra una notificación de logro desbloqueado.
 * @param {object} achievement - El objeto del logro { name, description, icon, xp_reward }.
 * @param {HTMLElement} container - El contenedor de notificaciones.
 */
export function showAchievementNotification(achievement, container) {
    if (!achievement || !container) return;

    const notification = document.createElement("div");
    notification.className = "achievement-notification"; // Usa la clase CSS existente
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="achievement-icon" style="font-size: 24px;">${achievement.icon || "🏆"}</span>
        <div>
          <h4 style="margin: 0 0 4px 0; font-size: 1em;">🏆 ¡Logro Desbloqueado!</h4>
          <p style="margin: 0; font-size: 0.9em;">${escapeHTML(achievement.name)}</p>
          <small style="opacity: 0.8; font-size: 0.8em;">${escapeHTML(achievement.desc)} (+${achievement.xp_reward || 0} XP)</small>
        </div>
      </div>
    `;

    playSound('OpenCloseModal', 0.2);
    container.appendChild(notification);

    // Animar entrada usando la clase CSS
    setTimeout(() => notification.classList.add("show"), 100);

    // Configurar cierre usando la clase CSS
    setTimeout(() => {
        notification.classList.add("hide");
        setTimeout(() => notification.remove(), 500); // Esperar animación de salida
    }, 4000); // Duración
}

/**
 * Escapa caracteres HTML para evitar XSS.
 * @param {string} str - El string a escapar.
 * @returns {string} El string seguro.
 */
export function escapeHTML(str) {
    if (typeof str !== "string") return "";
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}