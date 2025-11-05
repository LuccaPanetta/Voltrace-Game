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

const soundCache = {};
let _hasInteracted = false;
let _interactionListenerAdded = false;

// Configuración de audio global
const audioSettings = {
    volume: 0.5,       // Volumen Maestro (de 0.0 a 1.0)
    lastVolume: 0.5    // Para guardar el volumen antes de mutear
};

/**
 * Carga las preferencias de audio desde localStorage.
 */
export function loadAudioSettings() {
    try {
        const savedSettings = localStorage.getItem('audio_settings');
        if (savedSettings) {
            const settings = JSON.parse(savedSettings);
            if (settings.volume !== undefined) {
                audioSettings.volume = parseFloat(settings.volume);
            }
            // Guardamos el último volumen conocido si no es cero
            if (audioSettings.volume > 0.01) {
                audioSettings.lastVolume = audioSettings.volume;
            }
        }
    } catch (error) {
        console.warn("Error al cargar audio settings desde localStorage:", error);
    }
    console.log("Audio settings cargados:", audioSettings);
    return audioSettings;
}

/**
 * Guarda las preferencias de audio en localStorage.
 */
function saveAudioSettings() {
    try {
        localStorage.setItem('audio_settings', JSON.stringify(audioSettings));
    } catch (error) {
        console.warn("Error al guardar audio settings en localStorage:", error);
    }
}

/**
 * Establece el volumen maestro.
 * @param {number} newVolume - Nuevo volumen (0.0 a 1.0)
 */
export function setVolume(newVolume) {
    audioSettings.volume = newVolume;
    // Si el volumen es audible, lo guardamos como el "último volumen"
    if (newVolume > 0.01) {
        audioSettings.lastVolume = newVolume;
    }
    saveAudioSettings();
    return audioSettings;
}

/**
 * Activa/Desactiva el sonido.
 */
export function toggleMute() {
    if (audioSettings.volume > 0.01) {
        // Mutear: Guardar volumen actual y poner a 0
        audioSettings.lastVolume = audioSettings.volume; // Guardar
        audioSettings.volume = 0;
    } else {
        // Desmutear: Restaurar al último volumen guardado (o 0.5 si era 0)
        audioSettings.volume = audioSettings.lastVolume > 0.01 ? audioSettings.lastVolume : 0.5;
    }
    saveAudioSettings();
    console.log("Audio settings cambiados:", audioSettings);
    return audioSettings;
}

/**
 * Devuelve la configuración de audio actual.
 */
export function getAudioSettings() {
    return audioSettings;
}


// Función helper para precargar sonidos comunes
function preloadSounds(soundNames) {
    console.log("Precargando sonidos comunes...");
    for (const soundName of soundNames) {
        if (!soundCache[soundName]) {
            try {
                const soundPath = `/static/sounds/${soundName}.mp3`;
                const audio = new Audio(soundPath);
                audio.load(); // Inicia la descarga
                soundCache[soundName] = audio;
            } catch (error) {
                console.warn(`Error precargando sonido ${soundName}:`, error);
            }
        }
    }
}

/**
 * Reproduce un efecto de sonido. Maneja la restricción de interacción del navegador.
 * @param {string} soundName - Nombre del archivo (sin .mp3) en /static/sounds/
 * @param {number} [relativeVolume=0.5] - Volumen relativo del sonido (0.0 a 1.0)
 */
export function playSound(soundName, relativeVolume = 0.5) {
    const masterVolume = audioSettings.volume;
    
    // Si el volumen maestro es 0, no hacer nada.
    if (masterVolume <= 0.01) {
        return;
    }
    
    const finalVolume = relativeVolume * masterVolume;

    // Si el contexto de audio no está listo y no ha habido interacción, esperar.
    if (!_hasInteracted && (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined')) {
        console.log("Sound deferred: User hasn't interacted yet.");
        if (!_interactionListenerAdded) {
            const interactionEvents = ['click', 'keydown', 'touchstart'];
            const enableAudio = () => {
                _hasInteracted = true;
                console.log("User interaction detected, audio enabled.");
                interactionEvents.forEach(event => document.body.removeEventListener(event, enableAudio));

                // Precargar sonidos comunes DESPUÉS de la interacción
                preloadSounds([
                    'ClickMouse', 'Dice', 'GameStart', 'OpenCloseModal', 
                    'LandOnTrap', 'LandOnTreasure', 'Collision', 'Teleport', 
                    'MovementAbility', 'OffensiveAbility', 'DefensiveAbility',
                    'GameWin', 'GameLost' 
                ]);
            };
            interactionEvents.forEach(event => document.body.addEventListener(event, enableAudio, { once: true }));
            _interactionListenerAdded = true;
        }
        return; // No intentar reproducir aún
    }

    // Intentar reproducir el sonido
    try {
        let audio;

        // Revisar el cache
        if (soundCache[soundName]) {
            audio = soundCache[soundName];
        } else {
            // Si no está, crearlo y cachearlo
            console.warn(`Sonido "${soundName}" no estaba precargado. Cargando ahora...`);
            const soundPath = `/static/sounds/${soundName}.mp3`;
            audio = new Audio(soundPath);
            soundCache[soundName] = audio;
        }
        
        audio.volume = Math.max(0, Math.min(1, finalVolume)); // Usar finalVolume

        // Reiniciar el audio si ya está sonando 
        if (audio.readyState > 0) {
             audio.currentTime = 0;
        }
       
        audio.play().catch(error => {
            // Silenciar errores comunes si el usuario no interactuó (aunque intentamos prevenirlo)
            if (error.name !== 'NotAllowedError') {
                console.warn(`Could not play sound "${soundName}":`, error);
            }
        });
    } catch (error) {
        console.error(`Error creating/playing audio for "${soundName}":`, error);
    }
}

/**
 * Muestra una notificación temporal (toast).
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
    setTimeout(() => {
        notification.style.opacity = "1";
        notification.style.transform = "translateX(0)";
    }, 10);
    setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transform = "translateX(100%)";
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

/**
 * Muestra la notificación interactiva de invitación a sala.
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
        if (state.idSala.value && (screenElements.waiting?.classList.contains("active") || screenElements.game?.classList.contains("active"))) {
            if (!confirm("Ya estás en una sala. ¿Quieres salir y unirte a la nueva?")) {
                return;
            }
            socket.emit("salir_sala", { id_sala: state.idSala.value }); // Sale de la actual
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
    };
    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = 'flex';
    buttonContainer.appendChild(joinButton);
    buttonContainer.appendChild(rejectButton);
    notification.appendChild(buttonContainer);
    container.appendChild(notification);
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
 */
export function showAchievementNotification(achievement, container) {
    if (!achievement || !container) return;
    const icon = achievement.icon || "🏆";
    const name = achievement.name || "Logro Desbloqueado";
    const desc = achievement.desc || "¡Sigue así!";
    const xp = achievement.xp_reward || 0;
    const notification = document.createElement("div");
    notification.className = "achievement-notification"; 
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="achievement-icon" style="font-size: 24px;">${icon}</span>
        <div>
          <h4 style="margin: 0 0 4px 0; font-size: 1em;">🏆 ¡Logro Desbloqueado!</h4>
          <p style="margin: 0; font-size: 0.9em;">${escapeHTML(name)}</p>
          <small style="opacity: 0.8; font-size: 0.8em;">${escapeHTML(desc)} (+${xp} XP)</small>
        </div>
      </div>
    `;
    playSound('OpenCloseModal', 0.2);
    container.appendChild(notification);
    setTimeout(() => notification.classList.add("show"), 100);
    setTimeout(() => {
        notification.classList.add("hide");
        setTimeout(() => notification.remove(), 500); 
    }, 4000);
}

/**
 * Escapa caracteres HTML para evitar XSS.
 */
export function escapeHTML(str) {
    if (typeof str !== "string") return "";
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}