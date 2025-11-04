/* ===================================================================
   MÓDULO DE AUTENTICACIÓN (auth.js)
   Maneja el login, registro y actualización del perfil de usuario.
   =================================================================== */

import { showNotification, playSound } from './utils.js';

// --- Variables del Módulo ---
let loginEmailInput, loginPasswordInput, btnLogin;
let registerEmailInput, registerUsernameInput, registerPasswordInput, btnRegister;
let userUsernameDisplay, userLevelDisplay, userXpDisplay;
let tabLogin, tabRegister, loginForm, registerForm;
let _setLoadingFunc = null;
let _showFunc = null;
let _screens = null;
let _loadingElement = null;
let _onLoginSuccessCallback = null; 
let _gameAnimations = null; 

/**
 * Inicializa el módulo de autenticación, cachea elementos DOM y asigna listeners.
 */
export function initAuth(screensRef, showFuncRef, setLoadingFuncRef, loadingElementRef, onLoginSuccess, gameAnimationsInstance) {
    _screens = screensRef;
    _showFunc = showFuncRef;
    _setLoadingFunc = setLoadingFuncRef;
    _loadingElement = loadingElementRef;
    _onLoginSuccessCallback = onLoginSuccess;
    _gameAnimations = gameAnimationsInstance; 

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
    userLevelDisplay = document.getElementById("user-level");
    userXpDisplay = document.getElementById("user-xp");
    const btnLogout = document.getElementById("btn-logout");
    const btnToggleAnimations = document.getElementById("btn-toggle-animations"); 

    // --- Asignar Listeners ---
    tabLogin?.addEventListener("click", handleTabClick);
    tabRegister?.addEventListener("click", handleTabClick);
    btnLogin?.addEventListener("click", handleLogin);
    btnRegister?.addEventListener("click", handleRegister);
    loginPasswordInput?.addEventListener("keypress", handleEnterKeyPress);
    registerPasswordInput?.addEventListener("keypress", handleEnterKeyPress);
    btnLogout?.addEventListener("click", handleLogout);

    if (btnToggleAnimations && _gameAnimations) {
        btnToggleAnimations.addEventListener("click", () => {
            playSound('ClickMouse', 0.3);
            _gameAnimations.toggleAnimations(); 
            const isEnabled = _gameAnimations.getSettings().enabled;
            btnToggleAnimations.textContent = isEnabled ? "🎬" : "🚫";
            btnToggleAnimations.title = isEnabled ? "Desactivar animaciones" : "Activar animaciones";
            const notifContainer = document.getElementById("notificaciones"); 
            showNotification(isEnabled ? "✨ Animaciones activadas" : "🚫 Animaciones desactivadas", notifContainer, "info");
        });
        const isEnabledInitial = _gameAnimations.getSettings().enabled;
        btnToggleAnimations.textContent = isEnabledInitial ? "🎬" : "🚫";
        btnToggleAnimations.title = isEnabledInitial ? "Desactivar animaciones" : "Activar animaciones";
    } else {
        console.warn("Botón de animaciones o instancia no encontrados en initAuth.");
    }
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

/** Maneja el intento de inicio de sesión */
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
        // Si el login fue exitoso, llama al callback de main.js
        if (_onLoginSuccessCallback) {
            // Pasamos el objeto user_data completo
            _onLoginSuccessCallback(result.user_data);
        }
    } else {
        showNotification(result.message || "Error desconocido al iniciar sesión", notifContainer, "error");
    }
}

/** Maneja el intento de registro */
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
        // El servidor ya nos dio los datos del usuario, llamamos al callback
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
            _onLoginSuccessCallback(null); // Llama al callback con null
        }
        if (loginEmailInput) loginEmailInput.value = "";
        if (loginPasswordInput) loginPasswordInput.value = "";
        _showFunc('auth', _screens); // Vuelve a la pantalla de login/registro
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
        return await response.json(); // Espera { success: true, user_data: {...} }
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
        return await response.json(); // Espera { success: true, user_data: {...} }
    } catch (error) {
        console.error("Register API error:", error);
        showNotification("Error de conexión al registrar.", notifContainer, "error");
        return { success: false, message: "Error de conexión." }; 
    }
}

// --- Actualización de UI del Perfil ---

export function updateProfileUI(userStats) {
    if (userUsernameDisplay && userLevelDisplay && userXpDisplay) {
        if (userStats && userStats.username) {
            userUsernameDisplay.textContent = `👤 ${userStats.username}`;
            userLevelDisplay.textContent = `Nivel ${userStats.level || 1}`;
            userXpDisplay.textContent = `${userStats.xp || 0} XP`;
        } else {
            userUsernameDisplay.textContent = `👤 Desconectado`;
            userLevelDisplay.textContent = `Nivel -`;
            userXpDisplay.textContent = `- XP`;
        }
    } else {
        console.warn("Elementos de UI del perfil no encontrados al intentar actualizar.");
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