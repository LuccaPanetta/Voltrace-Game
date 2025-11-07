/* ===================================================================
   MÓDULO DE AUTENTICACIÓN (auth.js)
   Maneja el login, registro y actualización del perfil de usuario.
   =================================================================== */

import { showNotification, playSound, loadAudioSettings, setVolume, toggleMute, getAudioSettings, escapeHTML } from './utils.js';

// --- Variables del Módulo ---
let loginEmailInput, loginPasswordInput, btnLogin;
let registerEmailInput, registerUsernameInput, registerPasswordInput, btnRegister;
let userUsernameDisplay, userLevelText, userXpBar, userXpText;
let statGamesPlayed, statGamesWon, statWinRate;
let statWinStreak, statAbilitiesUsed, statRoomsCreated;
let btnEditAvatar;
let tabLogin, tabRegister, loginForm, registerForm;
let modalAvatar, btnCerrarAvatar;
let currentSelectedAvatarBtn = null;
let _setLoadingFunc = null;
let _showFunc = null;
let _screens = null;
let _loadingElement = null;
let _onLoginSuccessCallback = null; 
let _gameAnimations = null; 
let _state = null;

// La lista de emojis ya no es necesaria aquí, porque está en el HTML
// const AVATAR_LISTA_APROBADA = [ ... ];

/**
 * Inicializa el módulo de autenticación, cachea elementos DOM y asigna listeners.
 */
export function initAuth(screensRef, showFuncRef, setLoadingFuncRef, loadingElementRef, onLoginSuccess, gameAnimationsInstance, stateRef) {
    _screens = screensRef;
    _showFunc = showFuncRef;
    _setLoadingFunc = setLoadingFuncRef;
    _loadingElement = loadingElementRef;
    _onLoginSuccessCallback = onLoginSuccess;
    _gameAnimations = gameAnimationsInstance; 
    _state = stateRef; 

    // --- Cachear Elementos DOM ---
    tabLogin = document.getElementById("tab-login");
    tabRegister = document.getElementById("tab-register");
    loginForm = document.getElementById("login-form");
    registerForm = document.getElementById("register-form");
    loginEmailInput = document.getElementById("login-email");
    loginPasswordInput = document.getElementById("login-password");
    btnLogin = document.getElementById("btn-login");
    registerEmailInput = document.getElementById("register-email");
    registerUsernameInput = document.getElementById("register-username");
    registerPasswordInput = document.getElementById("register-password");
    btnRegister = document.getElementById("btn-register");
    userUsernameDisplay = document.getElementById("user-username");
    userLevelText = document.getElementById("user-level-text");
    userXpBar = document.getElementById("user-xp-bar");
    userXpText = document.getElementById("user-xp-text");
    btnEditAvatar = document.getElementById("btn-edit-avatar");
    statGamesPlayed = document.getElementById("stat-games-played");
    statGamesWon = document.getElementById("stat-games-won");
    statWinRate = document.getElementById("stat-win-rate");
    statWinStreak = document.getElementById("stat-win-streak");
    statAbilitiesUsed = document.getElementById("stat-abilities-used");
    statRoomsCreated = document.getElementById("stat-rooms-created");
    const btnLogout = document.getElementById("btn-logout");
    
    // Controles (Lobby)
    const btnToggleAnimationsLobby = document.getElementById("btn-toggle-animations"); 
    const volumeIconLobby = document.getElementById("volume-icon"); 
    const volumeSliderLobby = document.getElementById("volume-slider");
    
    // Controles (Juego)
    const btnToggleAnimationsGame = document.getElementById("btn-toggle-animations-game");
    const volumeIconGame = document.getElementById("volume-icon-game");
    const volumeSliderGame = document.getElementById("volume-slider-game");

    modalAvatar = document.getElementById("modal-avatar");
    btnCerrarAvatar = document.getElementById("btn-cerrar-avatar");

    // --- Asignar Listeners ---
    tabLogin?.addEventListener("click", handleTabClick);
    tabRegister?.addEventListener("click", handleTabClick);
    btnLogin?.addEventListener("click", handleLogin);
    btnRegister?.addEventListener("click", handleRegister);
    loginPasswordInput?.addEventListener("keypress", handleEnterKeyPress);
    registerPasswordInput?.addEventListener("keypress", handleEnterKeyPress);
    btnLogout?.addEventListener("click", handleLogout);

    // --- Lógica de Control de Animaciones (Refactorizada) ---
    const setupAnimationToggle = (buttonEl) => {
        if (buttonEl && _gameAnimations) {
            const isEnabledInitial = _gameAnimations.getSettings().enabled;
            buttonEl.textContent = isEnabledInitial ? "🎬" : "🚫";
            buttonEl.title = isEnabledInitial ? "Desactivar animaciones" : "Activar animaciones";

            buttonEl.addEventListener("click", () => {
                playSound('ClickMouse', 0.3);
                _gameAnimations.toggleAnimations(); 
                const isEnabled = _gameAnimations.getSettings().enabled;
                const notifContainer = document.getElementById("notificaciones"); 
                showNotification(isEnabled ? "✨ Animaciones activadas" : "🚫 Animaciones desactivadas", notifContainer, "info");
                // Actualizar AMBOS botones
                [btnToggleAnimationsLobby, btnToggleAnimationsGame].forEach(btn => {
                    if(btn) {
                        btn.textContent = isEnabled ? "🎬" : "🚫";
                        btn.title = isEnabled ? "Desactivar animaciones" : "Activar animaciones";
                    }
                });
            });
        }
    };
    
    // Configurar ambos botones
    setupAnimationToggle(btnToggleAnimationsLobby);
    setupAnimationToggle(btnToggleAnimationsGame);
    
    // --- Lógica de Control de Volumen (Refactorizada) ---
    const setupVolumeControls = (iconEl, sliderEl) => {
        if (iconEl && sliderEl) {
            const initialAudioSettings = loadAudioSettings();
            sliderEl.value = initialAudioSettings.volume;
            iconEl.textContent = initialAudioSettings.volume <= 0.01 ? "🔇" : "🔊";
            iconEl.title = initialAudioSettings.volume <= 0.01 ? "Activar sonido" : "Silenciar";

            sliderEl.addEventListener("input", (e) => {
                const newVolume = parseFloat(e.target.value);
                setVolume(newVolume); 
                // Actualizar AMBOS iconos
                [volumeIconLobby, volumeIconGame].forEach(icon => {
                    if(icon) {
                        icon.textContent = newVolume <= 0.01 ? "🔇" : "🔊";
                        icon.title = newVolume <= 0.01 ? "Activar sonido" : "Silenciar";
                    }
                });
                // Sincronizar AMBOS sliders
                if (volumeSliderLobby) volumeSliderLobby.value = newVolume;
                if (volumeSliderGame) volumeSliderGame.value = newVolume;
            });

            iconEl.addEventListener("click", () => {
                const newSettings = toggleMute(); 
                if (newSettings.volume > 0.01) playSound('ClickMouse', 0.3);
                // Actualizar AMBOS iconos y sliders
                [volumeIconLobby, volumeIconGame].forEach(icon => {
                    if(icon) {
                        icon.textContent = newSettings.volume <= 0.01 ? "🔇" : "🔊";
                        icon.title = newSettings.volume <= 0.01 ? "Activar sonido" : "Silenciar";
                    }
                });
                if (volumeSliderLobby) volumeSliderLobby.value = newSettings.volume;
                if (volumeSliderGame) volumeSliderGame.value = newSettings.volume;
            });
        }
    };
    
    // Configurar ambos sets de controles
    setupVolumeControls(volumeIconLobby, volumeSliderLobby);
    setupVolumeControls(volumeIconGame, volumeSliderGame);
    
    // --- Listeners de Avatar ---
    if (btnEditAvatar) {
        btnEditAvatar.addEventListener('click', openAvatarModal);
    }
    btnCerrarAvatar?.addEventListener('click', closeAvatarModal);
    modalAvatar?.addEventListener('click', (e) => {
        if (e.target === modalAvatar) closeAvatarModal();
    });
    const avatarButtons = document.querySelectorAll('#modal-avatar .avatar-btn');
    avatarButtons.forEach(button => {
        button.addEventListener('click', handleAvatarSelection);
    });
    
    console.log("Módulo Auth inicializado.");
}

// --- Manejadores de Eventos ---

function handleTabClick(event) {
    playSound('ClickMouse', 0.3);
    const isLoginTab = event.currentTarget === tabLogin;
    tabLogin?.classList.toggle("active", isLoginTab);
    tabRegister?.classList.toggle("active", !isLoginTab);
    loginForm?.classList.toggle("active", isLoginTab);
    registerForm?.classList.toggle("active", !isLoginTab);
}

async function handleLogin() {
    playSound('ClickMouse', 0.3);
    const email = loginEmailInput?.value.trim();
    const password = loginPasswordInput?.value;
    const notifContainer = document.getElementById('notificaciones');
    if (!email || !password) {
        return showNotification("Por favor, completa todos los campos", notifContainer, "error");
    }
    _setLoadingFunc(true, _loadingElement); 
    const result = await loginAPI(email, password); 
    _setLoadingFunc(false, _loadingElement); 
    if (result.success && result.user_data) {
        if (_onLoginSuccessCallback) {
            _onLoginSuccessCallback(result.user_data);
        }
    } else {
        showNotification(result.message || "Error desconocido al iniciar sesión", notifContainer, "error");
    }
}

async function handleRegister() {
    playSound('ClickMouse', 0.3);
    const email = registerEmailInput?.value.trim();
    const username = registerUsernameInput?.value.trim();
    const password = registerPasswordInput?.value;
    const notifContainer = document.getElementById('notificaciones');
    if (!email || !username || !password) {
        return showNotification("Por favor, completa todos los campos", notifContainer, "error");
    }
    if (username.length < 3) {
         return showNotification("El nombre de usuario debe tener al menos 3 caracteres", notifContainer, "warning");
    }
     if (password.length < 6) {
         return showNotification("La contraseña debe tener al menos 6 caracteres", notifContainer, "warning");
    }
    _setLoadingFunc(true, _loadingElement);
    const result = await registerAPI(email, username, password); 
    _setLoadingFunc(false, _loadingElement);
    if (result.success && result.user_data) {
        showNotification("¡Cuenta creada! Iniciando sesión...", notifContainer, "success");
        if (_onLoginSuccessCallback) {
            _onLoginSuccessCallback(result.user_data);
        }
    } else {
        showNotification(result.message || "Error desconocido al registrar", notifContainer, "error");
    }
}

function handleEnterKeyPress(event) {
    if (event.key === "Enter") {
        if (event.target === loginPasswordInput) {
            btnLogin?.click(); 
        } else if (event.target === registerPasswordInput) {
            btnRegister?.click(); 
        }
    }
}

async function handleLogout() {
    playSound('ClickMouse', 0.3);
    const notifContainer = document.getElementById('notificaciones');
    try {
        await fetch("/logout", { method: "POST" }); 
    } catch (error) {
        console.error("Error al cerrar sesión:", error);
    } finally {
        if (_onLoginSuccessCallback) {
            _onLoginSuccessCallback(null); 
        }
        if (loginEmailInput) loginEmailInput.value = "";
        if (loginPasswordInput) loginPasswordInput.value = "";
        document.getElementById("btn-crear-sala").disabled = true;
        document.getElementById("btn-unirse-sala").disabled = true;
        _showFunc('auth', _screens); 
    }
}

// --- Funciones de API (fetch) ---

async function loginAPI(email, password) {
    const notifContainer = document.getElementById('notificaciones');
    try {
        const response = await fetch("/login", { 
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            return { success: false, message: errorData.message || `Error ${response.status}` };
        }
        return await response.json(); 
    } catch (error) { 
        console.error("Login API error:", error); 
        showNotification("Error de conexión al iniciar sesión.", notifContainer, "error");
        return { success: false, message: "Error de conexión." };
    }
}

async function registerAPI(email, username, password) {
    const notifContainer = document.getElementById('notificaciones'); 
    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, username, password }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            return { success: false, message: errorData.message || `Error ${response.status}` };
        }
        return await response.json(); 
    } catch (error) {
        console.error("Register API error:", error);
        showNotification("Error de conexión al registrar.", notifContainer, "error");
        return { success: false, message: "Error de conexión." }; 
    }
}

// --- Actualización de UI del Perfil ---

/**
 * Prepara y abre el modal de selección de avatar (OPTIMIZADO).
 */
function openAvatarModal() {
    playSound('OpenCloseModal', 0.3);
    if (!_state || !_state.currentUser || !modalAvatar) {
        console.error("No se puede abrir el modal de avatar. Estado o modal no encontrado.");
        return;
    }

    const currentAvatar = _state.currentUser.avatar_emoji || '👤';

    // Quitar la clase al botón seleccionado anteriormente (si existe)
    if (currentSelectedAvatarBtn) {
        currentSelectedAvatarBtn.classList.remove('seleccionado');
    }

    // Encontrar y marcar el nuevo botón seleccionado
    const newSelectedBtn = document.querySelector(`#modal-avatar .avatar-btn[data-emoji="${currentAvatar}"]`);
    if (newSelectedBtn) {
        newSelectedBtn.classList.add('seleccionado');
        currentSelectedAvatarBtn = newSelectedBtn; // Guardar referencia
    }

    modalAvatar.style.display = 'flex';
}

/**
 * Cierra el modal de selección de avatar.
 */
function closeAvatarModal() {
    playSound('OpenCloseModal', 0.2);
    if (modalAvatar) modalAvatar.style.display = 'none';
}

/**
 * Se ejecuta al hacer clic en un botón de emoji.
 */
async function handleAvatarSelection(event) {
    const nuevoEmoji = event.currentTarget.dataset.emoji;

    // Si hace clic en el que ya tiene, solo cerrar
    if (!nuevoEmoji || !_state || !_state.currentUser || nuevoEmoji === _state.currentUser.avatar_emoji) {
        closeAvatarModal();
        return;
    }
    
    // Guardar el emoji anterior por si falla el guardado
    const emojiAnterior = _state.currentUser.avatar_emoji;

    // Actualizar la UI y el estado local INMEDIATAMENTE
    _state.currentUser.avatar_emoji = nuevoEmoji;
    updateProfileUI(_state.currentUser);
    showNotification("¡Avatar actualizado!", document.getElementById('notificaciones'), "success");
    closeAvatarModal(); // Cerrar modal al instante

    // Intentar guardar en el servidor en segundo plano

    try {
        const response = await fetch('/api/set_avatar', {
            method: 'POST',
            headers: { 'Content-Type': "application/json" },
            body: JSON.stringify({ avatar_emoji: nuevoEmoji })
        });
        const data = await response.json();

        if (!data.success) {
            // Si falla, revertir el cambio y notificar
            console.error("Error del servidor al guardar avatar:", data.message);
            showNotification(data.message || "Error al guardar el avatar.", document.getElementById('notificaciones'), "error");
            _state.currentUser.avatar_emoji = emojiAnterior; // Revertir
            updateProfileUI(_state.currentUser); // Actualizar UI a la versión anterior
        }
        // Si tiene éxito, no hacer nada (ya lo actualizamos)
    } catch (error) {
        // Si falla por conexión, revertir el cambio y notificar
        console.error("Error en fetch /api/set_avatar:", error);
        showNotification("Error de conexión. Revirtiendo avatar.", document.getElementById('notificaciones'), "error");
        _state.currentUser.avatar_emoji = emojiAnterior; // Revertir
        updateProfileUI(_state.currentUser); // Actualizar UI a la versión anterior
    }
}

export function updateProfileUI(user) {
    if (user) {
        // --- Header ---
        const avatar = user.avatar_emoji || '👤';
        const level = user.level || 1;
        const xp = user.xp || 0;
        const xpNextLevel = user.xp_next_level || (level * 500);
        
        const title = user.equipped_title ? `<span class="user-title">[${escapeHTML(user.equipped_title)}]</span>` : '';
        if (userUsernameDisplay) userUsernameDisplay.innerHTML = `${avatar} ${escapeHTML(user.username)} ${title}`; 
        
        // Actualizar barra de XP
        if (userLevelText) userLevelText.textContent = `⭐ Nivel ${level}`;
        if (userXpBar) {
            userXpBar.value = xp;
            userXpBar.max = xpNextLevel;
        }
        if (userXpText) userXpText.textContent = `${xp} / ${xpNextLevel} XP`;

        const btnArsenal = document.getElementById("btn-show-arsenal");
        if (btnArsenal) {
            const nivelRequerido = 5; // Nivel 5 para desbloquear
            if (level < nivelRequerido) {
                btnArsenal.disabled = true;
                btnArsenal.title = `Se desbloquea en Nivel ${nivelRequerido}`;
                btnArsenal.style.opacity = "0.5";
            } else {
                btnArsenal.disabled = false;
                btnArsenal.title = "Ver Maestría de Kits";
                btnArsenal.style.opacity = "1";
            }
        }

        // --- Panel de Estadísticas del Lobby ---
        const gamesPlayed = user.games_played || 0;
        const gamesWon = user.games_won || 0;
        
        let winRate = 0;
        if (gamesPlayed > 0) {
            winRate = ((gamesWon / gamesPlayed) * 100).toFixed(1);
        }

        if (statGamesPlayed) statGamesPlayed.textContent = gamesPlayed;
        if (statGamesWon) statGamesWon.textContent = gamesWon;
        if (statWinRate) statWinRate.textContent = `${winRate}%`;
        if (statWinStreak) statWinStreak.textContent = user.consecutive_wins || 0;
        if (statAbilitiesUsed) statAbilitiesUsed.textContent = user.abilities_used || 0;
        if (statRoomsCreated) statRoomsCreated.textContent = user.rooms_created || 0;

    } else {
        // --- Logout  ---
        if (userUsernameDisplay) userUsernameDisplay.textContent = "👤 Usuario";
        
        // Resetear barra de XP
        if (userLevelText) userLevelText.textContent = `⭐ Nivel 1`;
        if (userXpBar) {
            userXpBar.value = 0;
            userXpBar.max = 500; 
        }
        if (userXpText) userXpText.textContent = `0 / 500 XP`;

        const btnArsenal = document.getElementById("btn-show-arsenal");
        if (btnArsenal) {
            btnArsenal.disabled = true;
            btnArsenal.title = "Inicia sesión para ver tu Arsenal";
            btnArsenal.style.opacity = "0.5";
        }

        if (statGamesPlayed) statGamesPlayed.textContent = "0";
        if (statGamesWon) statGamesWon.textContent = "0";
        if (statWinRate) statWinRate.textContent = "0%";
        if (statWinStreak) statWinStreak.textContent = "0";
        if (statAbilitiesUsed) statAbilitiesUsed.textContent = "0";
        if (statRoomsCreated) statRoomsCreated.textContent = "0";
    }
}

export async function fetchAndUpdateUserProfile(username) {
    const notifContainer = document.getElementById('notificaciones'); 
    if (!username) {
        updateProfileUI(null); 
        return null; 
    }
    try {
        const response = await fetch(`/profile/${username}`); 
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error ${response.status} al cargar perfil`);
        }
        const profileData = await response.json(); 
        if (profileData.stats) {
            updateProfileUI(profileData.stats); 
            return profileData.stats; 
        } else {
            throw new Error("Datos de perfil incompletos recibidos del servidor.");
        }
    } catch (error) {
        console.error("Error al cargar/actualizar perfil:", error);
        showNotification(`Error al cargar perfil: ${error.message}`, notifContainer, "error");
        updateProfileUI(null); 
        return null; 
    }
}