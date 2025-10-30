/* ===================================================================
   MÓDULO DE AUTENTICACIÓN (auth.js)
   Maneja el login, registro y actualización del perfil de usuario.
   =================================================================== */

// Importar utilidades necesarias (showNotification, playSound)
import { showNotification, playSound } from './utils.js';

// --- Variables del Módulo ---

// Referencias DOM (se cachearán en initAuth)
let loginEmailInput, loginPasswordInput, btnLogin;
let registerEmailInput, registerUsernameInput, registerPasswordInput, btnRegister;
let userUsernameDisplay, userLevelDisplay, userXpDisplay;
let tabLogin, tabRegister, loginForm, registerForm;

// Referencias a funciones/elementos externos (pasadas en initAuth)
let _setLoadingFunc = null;
let _showFunc = null;
let _screens = null;
let _loadingElement = null;
let _onLoginSuccessCallback = null; // Callback para notificar a main.js del login/logout
let _gameAnimations = null; // Variable local para guardar la instancia de AnimationSystem

/**
 * Inicializa el módulo de autenticación, cachea elementos DOM y asigna listeners.
 * @param {object} screensRef - Referencias a los elementos de pantalla (auth, lobby, etc.).
 * @param {function} showFuncRef - Referencia a la función show() de utils.js.
 * @param {function} setLoadingFuncRef - Referencia a la función setLoading() de utils.js.
 * @param {HTMLElement} loadingElementRef - Referencia al elemento DOM del overlay de carga.
 * @param {function} onLoginSuccess - Callback a llamar con datos del usuario (o null) al loguearse/desloguearse.
 * @param {object} gameAnimationsInstance - Instancia de AnimationSystem creada en main.js.
 */
export function initAuth(screensRef, showFuncRef, setLoadingFuncRef, loadingElementRef, onLoginSuccess, gameAnimationsInstance) {
    // Guardar referencias externas
    _screens = screensRef;
    _showFunc = showFuncRef;
    _setLoadingFunc = setLoadingFuncRef;
    _loadingElement = loadingElementRef;
    _onLoginSuccessCallback = onLoginSuccess;
    _gameAnimations = gameAnimationsInstance; // Guardar la instancia de animaciones

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
    const btnToggleAnimations = document.getElementById("btn-toggle-animations"); // Botón de animaciones

    // --- Asignar Listeners ---
    tabLogin?.addEventListener("click", handleTabClick);
    tabRegister?.addEventListener("click", handleTabClick);
    btnLogin?.addEventListener("click", handleLogin);
    btnRegister?.addEventListener("click", handleRegister);
    loginPasswordInput?.addEventListener("keypress", handleEnterKeyPress);
    registerPasswordInput?.addEventListener("keypress", handleEnterKeyPress);
    btnLogout?.addEventListener("click", handleLogout);

    // Listener para el botón de activar/desactivar animaciones
    if (btnToggleAnimations && _gameAnimations) {
        btnToggleAnimations.addEventListener("click", () => {
            playSound('ClickMouse', 0.3);
            _gameAnimations.toggleAnimations(); // Usa la instancia guardada
            const isEnabled = _gameAnimations.getSettings().enabled;
            btnToggleAnimations.textContent = isEnabled ? "🎬" : "🚫";
            btnToggleAnimations.title = isEnabled ? "Desactivar animaciones" : "Activar animaciones";
            const notifContainer = document.getElementById("notificaciones"); // Necesario para showNotification
            // Llama a showNotification pasándole el contenedor
            showNotification(isEnabled ? "✨ Animaciones activadas" : "🚫 Animaciones desactivadas", notifContainer, "info");
        });
        // Establecer estado inicial del botón al cargar
        const isEnabledInitial = _gameAnimations.getSettings().enabled;
        btnToggleAnimations.textContent = isEnabledInitial ? "🎬" : "🚫";
        btnToggleAnimations.title = isEnabledInitial ? "Desactivar animaciones" : "Activar animaciones";
    } else {
        console.warn("Botón de animaciones o instancia no encontrados en initAuth.");
    }
}

// --- Manejadores de Eventos ---

/** Maneja el clic en las pestañas de Login/Registro */
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

    _setLoadingFunc(true, _loadingElement); // Muestra el loading
    const result = await loginAPI(email, password); // Llama a la API
    _setLoadingFunc(false, _loadingElement); // Oculta el loading

    if (result.success && result.username) {
        // Si el login fue exitoso, llama al callback de main.js
        if (_onLoginSuccessCallback) {
            // Pasamos solo el nombre de usuario, main.js se encargará de buscar el perfil completo
            _onLoginSuccessCallback({ username: result.username });
        }
    } else {
        // Muestra error si falló
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

    // Validaciones básicas
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
    const result = await registerAPI(email, username, password); // Llama a la API de registro
    _setLoadingFunc(false, _loadingElement);

    if (result.success) {
        showNotification("¡Cuenta creada! Iniciando sesión automáticamente...", notifContainer, "success");
        // Intenta hacer login automáticamente después del registro
        const loginResult = await loginAPI(email, password);
        if (loginResult.success && loginResult.username) {
            // Si el auto-login funciona, llama al callback de main.js
            if (_onLoginSuccessCallback) {
                _onLoginSuccessCallback({ username: loginResult.username });
            }
        } else {
            // Si el auto-login falla, muestra la pantalla de auth y un error
            _showFunc('auth', _screens);
            showNotification(loginResult.message || "Error al iniciar sesión tras registro", notifContainer, "error");
        }
    } else {
        // Muestra error si el registro falló
        showNotification(result.message || "Error desconocido al registrar", notifContainer, "error");
    }
}

/** Maneja la tecla Enter en los campos de contraseña */
function handleEnterKeyPress(event) {
    if (event.key === "Enter") {
        if (event.target === loginPasswordInput) {
            btnLogin?.click(); // Simula clic en botón login
        } else if (event.target === registerPasswordInput) {
            btnRegister?.click(); // Simula clic en botón registro
        }
    }
}

/** Maneja el cierre de sesión */
async function handleLogout() {
    playSound('ClickMouse', 0.3);
    const notifContainer = document.getElementById('notificaciones');
    try {
        await fetch("/logout", { method: "POST" }); // Llama a la API de logout
    } catch (error) {
        console.error("Error al cerrar sesión:", error);
        // Opcional: Mostrar notificación de error de red
        // showNotification("Error de red al cerrar sesión", notifContainer, "error");
    } finally {
        // Llama al callback de main.js pasándole null para indicar logout
        if (_onLoginSuccessCallback) {
            _onLoginSuccessCallback(null);
        }
        // Limpia los campos y muestra la pantalla de autenticación
        if (loginEmailInput) loginEmailInput.value = "";
        if (loginPasswordInput) loginPasswordInput.value = "";
        _showFunc('auth', _screens); // Vuelve a la pantalla de login/registro
    }
}

// --- Funciones de API (fetch) ---

/** Llama a la API de login del servidor */
async function loginAPI(email, password) {
    const notifContainer = document.getElementById('notificaciones'); // Necesario por si hay error
    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
        // Si la respuesta no es OK (ej. 401 Unauthorized), lee el JSON de error
        if (!response.ok) {
            const errorData = await response.json();
            return { success: false, message: errorData.message || `Error ${response.status}` };
        }
        return await response.json(); // Devuelve { success: true, username: ... }
    } catch (error) {
        console.error("Login API error:", error);
        // Usa showNotification aquí en lugar del return para que se muestre
        showNotification("Error de conexión al iniciar sesión.", notifContainer, "error");
        return { success: false, message: "Error de conexión." }; // Devuelve un objeto de error
    }
}

/** Llama a la API de registro del servidor */
async function registerAPI(email, username, password) {
    const notifContainer = document.getElementById('notificaciones'); // Necesario por si hay error
    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, username, password }),
        });
        // Si la respuesta no es OK (ej. 400 Bad Request), lee el JSON de error
        if (!response.ok) {
            const errorData = await response.json();
            return { success: false, message: errorData.message || `Error ${response.status}` };
        }
        return await response.json(); // Devuelve { success: true, username: ... }
    } catch (error) {
        console.error("Register API error:", error);
        // Usa showNotification aquí
        showNotification("Error de conexión al registrar.", notifContainer, "error");
        return { success: false, message: "Error de conexión." }; // Devuelve objeto de error
    }
}

// --- Actualización de UI del Perfil ---

/**
 * Actualiza la UI del perfil de usuario en el panel superior (header).
 * @param {object | null} userStats - Objeto con { username, level, xp } o null si se hace logout.
 */
export function updateProfileUI(userStats) {
    // Verificar que los elementos DOM existan
    if (userUsernameDisplay && userLevelDisplay && userXpDisplay) {
        if (userStats && userStats.username) {
            // Actualizar con datos del usuario
            userUsernameDisplay.textContent = `👤 ${userStats.username}`;
            userLevelDisplay.textContent = `Nivel ${userStats.level || 1}`;
            userXpDisplay.textContent = `${userStats.xp || 0} XP`;
        } else {
            // Resetear UI si no hay datos (logout)
            userUsernameDisplay.textContent = `👤 Desconectado`;
            userLevelDisplay.textContent = `Nivel -`;
            userXpDisplay.textContent = `- XP`;
        }
    } else {
        // Advertir si los elementos no se encontraron (puede pasar si initAuth se llama muy pronto)
        console.warn("Elementos de UI del perfil no encontrados al intentar actualizar.");
    }
}

/**
 * Busca los datos completos del perfil de un usuario (incluyendo stats de DB) y llama a updateProfileUI.
 * Esta función es llamada por main.js después de un login exitoso.
 * @param {string} username - El nombre de usuario a buscar.
 * @returns {Promise<object|null>} - Promesa que resuelve con los stats del usuario o null si hay error.
 */
export async function fetchAndUpdateUserProfile(username) {
    const notifContainer = document.getElementById('notificaciones'); // Para mostrar errores
    if (!username) {
        updateProfileUI(null); // Limpia la UI si no hay nombre de usuario
        return null; // Devuelve null si no hay username
    }
    try {
        const response = await fetch(`/profile/${username}`); // Llama a la API de perfil
        if (!response.ok) {
            // Si la API devuelve error (ej. 404), lanzar un error
            const errorData = await response.json();
            throw new Error(errorData.error || `Error ${response.status} al cargar perfil`);
        }
        const profileData = await response.json(); // Obtiene { stats: {...}, achievements: {...} }
        if (profileData.stats) {
            updateProfileUI(profileData.stats); // Actualiza la UI del header
            return profileData.stats; // Devuelve los stats cargados
        } else {
            throw new Error("Datos de perfil incompletos recibidos del servidor.");
        }
    } catch (error) {
        console.error("Error al cargar/actualizar perfil:", error);
        // Muestra notificación de error
        showNotification(`Error al cargar perfil: ${error.message}`, notifContainer, "error");
        updateProfileUI(null); // Limpia la UI si hubo error
        return null; // Devuelve null indicando fallo
    }
}