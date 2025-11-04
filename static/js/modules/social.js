/* ===================================================================
   MÓDULO SOCIAL (social.js)
   Maneja la UI y lógica del modal social (amigos, solicitudes, búsqueda),
   chat privado e invitaciones.
   =================================================================== */

import { escapeHTML, playSound, showNotification } from './utils.js';

// Referencias DOM
let modalSocialElement, btnCerrarSocial, btnSocialGlobal, btnSocialWaiting;
let socialTabFriends, socialTabRequests, socialTabSearch;
let socialContentFriends, socialContentRequests, socialContentSearch;
let socialFriendsListDisplay, socialRequestsListDisplay, socialSearchResultsDisplay;
let socialSearchInput, socialSearchButton;
let modalPrivateChatElement, btnCerrarPrivateChat, chatWithUsernameDisplay;
let privateChatMessagesDisplay, privateChatInput, privateChatSendBtn;

// Referencias a estado/funciones externas
let _socket = null;
let _state = null; 

// --- Caché Social ---
const socialCache = {
    friends: [],
    pending_received: [],
    pending_sent: [],
    isLoaded: false, 
    isLoading: false,
};


/**
 * Inicializa el módulo social.
 * @param {object} socketRef - Instancia de Socket.IO.
 * @param {object} stateRef - Referencia al estado global.
 */
export function initSocial(socketRef, stateRef) {
    _socket = socketRef;
    _state = stateRef; 

    // Cachear elementos DOM
    modalSocialElement = document.getElementById("modal-social");
    btnCerrarSocial = document.getElementById("btn-cerrar-social");
    btnSocialGlobal = document.getElementById("btn-social"); 
    btnSocialWaiting = document.getElementById("btn-social-waiting"); 
    socialTabFriends = document.getElementById("social-tab-friends");
    socialTabRequests = document.getElementById("social-tab-requests");
    socialTabSearch = document.getElementById("social-tab-search");
    socialContentFriends = document.getElementById("social-content-friends");
    socialContentRequests = document.getElementById("social-content-requests");
    socialContentSearch = document.getElementById("social-content-search");
    socialFriendsListDisplay = document.getElementById("social-friends-list");
    socialRequestsListDisplay = document.getElementById("social-requests-list");
    socialSearchInput = document.getElementById("social-search-input");
    socialSearchButton = document.getElementById("social-search-button");
    socialSearchResultsDisplay = document.getElementById("social-search-results");
    modalPrivateChatElement = document.getElementById("modal-private-chat");
    btnCerrarPrivateChat = document.getElementById("btn-cerrar-private-chat");
    chatWithUsernameDisplay = document.getElementById("chat-with-username");
    privateChatMessagesDisplay = document.getElementById("private-chat-messages");
    privateChatInput = document.getElementById("private-chat-input");
    privateChatSendBtn = document.getElementById("private-chat-send");

    // Asignar listeners
    btnSocialGlobal?.addEventListener("click", openSocialModal);
    btnSocialWaiting?.addEventListener("click", openSocialModal);
    btnCerrarSocial?.addEventListener("click", closeSocialModal);
    modalSocialElement?.addEventListener('click', (e) => { if (e.target === modalSocialElement) closeSocialModal(); }); 

    socialTabFriends?.addEventListener("click", () => switchSocialTab("friends"));
    socialTabRequests?.addEventListener("click", () => switchSocialTab("requests"));
    socialTabSearch?.addEventListener("click", () => switchSocialTab("search"));

    socialSearchButton?.addEventListener("click", handleSearchUsers);
    socialSearchInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleSearchUsers(); });

    // Delegación de eventos
    socialFriendsListDisplay?.addEventListener("click", handleSocialListClick);
    socialRequestsListDisplay?.addEventListener("click", handleSocialListClick);
    socialSearchResultsDisplay?.addEventListener("click", handleSocialListClick);

    // Chat Privado
    btnCerrarPrivateChat?.addEventListener("click", closePrivateChat);
    privateChatSendBtn?.addEventListener("click", handleSendPrivateMessage);
    privateChatInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleSendPrivateMessage(); });

    // Listeners para invalidar el caché
    _socket?.on("friend_status_update", (data) => invalidateSocialCache());
    _socket?.on("new_friend_request", (data) => invalidateSocialCache());
}

// --- Lógica del Modal Social ---

/**
 * Abre el modal. Si el caché no está cargado, muestra 'Cargando...'.
 * La carga real ahora se hace en 'loadSocialData'.
 */
function openSocialModal() {
    playSound('OpenCloseModal', 0.3);
    if (!modalSocialElement) return;
    if (!_state || !_state.currentUser || !_state.currentUser.username) {
        const notifContainer = document.getElementById('notificaciones');
        showNotification("Debes iniciar sesión para usar las funciones sociales.", notifContainer, "warning");
        return;
    }
    modalSocialElement.style.display = "flex";
    btnSocialGlobal?.classList.remove("has-notification");
    btnSocialWaiting?.classList.remove("has-notification");
    
    if (socialCache.isLoaded) {
        renderFriendsList(socialCache.friends);
        renderRequestsList(socialCache.pending_received);
    } else {
        // Si el caché aún no está listo (porque la precarga está en curso),
        // muestra 'Cargando...'.
        if (socialFriendsListDisplay) socialFriendsListDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">Cargando...</p>';
        if (socialRequestsListDisplay) socialRequestsListDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">Cargando...</p>';
    }
    switchSocialTab("friends"); // Siempre abre en la pestaña de amigos
}

function closeSocialModal() {
    playSound('OpenCloseModal', 0.2);
    if (modalSocialElement) modalSocialElement.style.display = 'none';
}

/**
 * Invalida (borra) el caché social.
 * Se llama desde socketHandlers cuando hay una actualización.
 */
export function invalidateSocialCache() {
    console.log("Invalidando caché social...");
    socialCache.isLoaded = false;
    socialCache.data = null;
    
    // Si el modal está abierto, recargarlo
    if (modalSocialElement?.style.display === "flex") {
        console.log("Modal social abierto, forzando recarga de datos...");
        loadSocialData(); 
    }
}

/**
 * Función para cargar todos los datos sociales.
 * Esta función es llamada por 'main.js' durante la precarga.
 */
export async function loadSocialData() {
    // Evitar recargas si ya está cargando o si ya está cargado
    if (socialCache.isLoading || socialCache.isLoaded) return;
    if (!_state.currentUser || !_state.currentUser.username) return;

    console.log("Iniciando precarga de datos sociales...");
    socialCache.isLoading = true;

    const endpoint = `/social/amigos/${_state.currentUser.username}`;
    try {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error(`Error de red ${response.status}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);

        // Guardar datos en el caché
        socialCache.friends = data.friends || [];
        socialCache.pending_received = data.pending_received || [];
        socialCache.pending_sent = data.pending_sent || [];
        socialCache.isLoaded = true;
        console.log("Caché social cargado exitosamente.");

        // Si el modal está abierto, renderizar los datos que acabamos de cargar
        if (modalSocialElement?.style.display === "flex") {
            renderFriendsList(socialCache.friends);
            renderRequestsList(socialCache.pending_received);
        }

    } catch (error) {
        console.error(`Error al cargar datos sociales:`, error);
        // Si falla, permitir un reintento la próxima vez que se abra el modal
        socialCache.isLoaded = false; 
        if (modalSocialElement?.style.display === "flex") {
            const errorHTML = `<p style="text-align: center; color: var(--danger);">Error al cargar: ${error.message}</p>`;
            if (socialFriendsListDisplay) socialFriendsListDisplay.innerHTML = errorHTML;
            if (socialRequestsListDisplay) socialRequestsListDisplay.innerHTML = errorHTML;
        }
    } finally {
        socialCache.isLoading = false;
    }
}

/**
 * Cambia la pestaña visible. Ahora solo renderiza desde el caché (es instantáneo).
 */
function switchSocialTab(tabName) {
    if (!socialTabFriends || !socialContentFriends) return;
    playSound('ClickMouse', 0.3);

    [socialTabFriends, socialTabRequests, socialTabSearch].forEach(btn => btn?.classList.remove("active"));
    [socialContentFriends, socialContentRequests, socialContentSearch].forEach(content => content?.classList.remove("active"));

    let activeTabButton, activeContent;

    if (tabName === "friends") {
        activeTabButton = socialTabFriends;
        activeContent = socialContentFriends;
        if(socialCache.isLoaded) renderFriendsList(socialCache.friends); // Renderizar desde caché
    } else if (tabName === "requests") {
        activeTabButton = socialTabRequests;
        activeContent = socialContentRequests;
        if(socialCache.isLoaded) renderRequestsList(socialCache.pending_received); // Renderizar desde caché
    } else if (tabName === "search") {
        activeTabButton = socialTabSearch;
        activeContent = socialContentSearch;
        if(socialSearchInput) socialSearchInput.value = "";
        if (socialSearchResultsDisplay) socialSearchResultsDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">Ingresa un nombre para buscar.</p>';
    } else {
        return;
    }

    if (!activeTabButton || !activeContent) return; 

    activeTabButton.classList.add("active");
    activeContent.classList.add("active");
}

// --- Renderizado UI Social ---

function renderFriendsList(friends) {
    if (!socialFriendsListDisplay) return;
    if (!friends || friends.length === 0) {
        socialFriendsListDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">No tienes amigos aún. ¡Busca y agrega!</p>';
        return;
    }
    socialFriendsListDisplay.innerHTML = "";
    friends.forEach(friend => {
        const item = document.createElement("div");
        item.className = "social-list-item";
        item.dataset.username = friend.username;
        let statusClass = "offline", statusText = "Offline";
        const friendStatus = friend.status || "offline";
        if (friendStatus.startsWith("in_game")) { statusClass = "in_game"; statusText = "En Partida"; }
        else if (friendStatus === "online" || friendStatus.startsWith("in_lobby")) { statusClass = "online"; statusText = "Online"; }
        const canInvite = statusClass === "online" && _state.idSala.value;
        item.innerHTML = `
          <div class="social-user-info">
            <div class="social-status ${statusClass}" title="${statusText}"></div>
            <span>${escapeHTML(friend.username)} (Nvl ${friend.level || 1})</span>
          </div>
          <div class="social-actions">
            <button class="btn-primary btn-chat-friend" title="Chatear">💬</button>
            <button class="btn-success btn-invite-friend" title="Invitar a sala actual" ${!canInvite ? 'disabled' : ''}>🎮</button>
            <button class="btn-danger btn-remove-friend" title="Eliminar amigo">🗑️</button>
          </div>
        `;
        socialFriendsListDisplay.appendChild(item);
    });
}

function renderRequestsList(requests) {
    if (!socialRequestsListDisplay) return;
    if (!requests || requests.length === 0) {
        socialRequestsListDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">No tienes solicitudes pendientes.</p>';
        return;
    }
    socialRequestsListDisplay.innerHTML = "";
    requests.forEach(username => {
        const item = document.createElement("div");
        item.className = "social-list-item";
        item.dataset.username = username;
        item.innerHTML = `
          <div class="social-user-info">
            <span>${escapeHTML(username)} quiere ser tu amigo.</span>
          </div>
          <div class="social-actions">
            <button class="btn-success btn-accept-request">Aceptar</button>
            <button class="btn-danger btn-reject-request">Rechazar</button>
          </div>
        `;
        socialRequestsListDisplay.appendChild(item);
    });
}

function renderSearchResults(users) {
    if (!socialSearchResultsDisplay) return;
    if (!users || users.length === 0) {
        socialSearchResultsDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">No se encontraron usuarios.</p>';
        return;
    }
    socialSearchResultsDisplay.innerHTML = "";
    users.forEach(user => {
        const item = document.createElement("div");
        item.className = "social-list-item";
        item.dataset.username = user.username;
        let relationHTML = "";
        if (socialCache.friends.find(f => f.username === user.username)) {
            relationHTML = '<span style="color: var(--success); font-size: 0.9em;">Amigo</span>';
        } else if (socialCache.pending_sent.includes(user.username)) {
            relationHTML = '<span style="color: var(--warning); font-size: 0.9em;">Pendiente</span>';
        } else if (socialCache.pending_received.includes(user.username)) {
            relationHTML = '<button class="btn-success btn-accept-request">Aceptar</button>';
        } else {
            relationHTML = '<button class="btn-primary btn-add-friend">Agregar</button>';
        }
        item.innerHTML = `
          <div class="social-user-info">
            <span>${escapeHTML(user.username)} (Nvl ${user.level || 1})</span>
          </div>
          <div class="social-actions" style="min-width: 80px; text-align: right;">${relationHTML}</div>
        `;
        socialSearchResultsDisplay.appendChild(item);
    });
}

// --- Acciones Sociales (API y Eventos) ---
async function handleSearchUsers() {
    playSound('ClickMouse', 0.3);
    if (!_state.currentUser || !_state.currentUser.username || !socialSearchInput || !socialSearchButton || !socialSearchResultsDisplay) return;
    const query = socialSearchInput.value.trim();
    const notifContainer = document.getElementById('notificaciones');
    if (query.length < 2) {
        return showNotification("La búsqueda debe tener al menos 2 caracteres.", notifContainer, "warning");
    }
    socialSearchResultsDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">Buscando...</p>';
    socialSearchButton.textContent = "...";
    socialSearchButton.disabled = true;
    try {
        const response = await fetch(`/social/search/${query}/${_state.currentUser.username}`);
        if (!response.ok) throw new Error("Error en la búsqueda");
        const data = await response.json();
        renderSearchResults(data); 
    } catch (error) {
        console.error("Error al buscar usuarios:", error);
        socialSearchResultsDisplay.innerHTML = '<p style="text-align: center; color: var(--danger);">Error al buscar.</p>';
    } finally {
        socialSearchButton.textContent = "Buscar";
        socialSearchButton.disabled = false;
    }
}

async function sendFriendRequest(targetUsername, buttonElement) {
    if (!_state.currentUser || !_state.currentUser.username || !buttonElement) return;
    const originalText = buttonElement.textContent;
    buttonElement.textContent = "...";
    buttonElement.disabled = true;
    const notifContainer = document.getElementById('notificaciones');
    try {
        const response = await fetch(`/social/solicitud/send/${_state.currentUser.username}/${targetUsername}`, { method: "POST" });
        const result = await response.json();
        showNotification(result.message, notifContainer, result.success ? "success" : "error");
        if (result.success) {
            socialCache.pending_sent.push(targetUsername); 
            const listItem = buttonElement.closest(".social-list-item");
            const actionsDiv = listItem?.querySelector(".social-actions");
            if (actionsDiv) {
                actionsDiv.innerHTML = '<span style="color: var(--warning); font-size: 0.9em;">Pendiente</span>';
            }
        } else {
            buttonElement.textContent = originalText;
            buttonElement.disabled = false;
        }
    } catch (error) {
        showNotification("Error de red al enviar solicitud.", notifContainer, "error");
        buttonElement.textContent = originalText;
        buttonElement.disabled = false;
    }
}

async function acceptFriendRequest(senderUsername, buttonElement) {
    if (!_state.currentUser || !_state.currentUser.username || !buttonElement) return;
    const listItem = buttonElement.closest(".social-list-item");
    const actionsDiv = listItem?.querySelector(".social-actions");
      if (actionsDiv) {
          actionsDiv.textContent = "..."; 
      }
    const notifContainer = document.getElementById('notificaciones');
    try {
        const response = await fetch(`/social/solicitud/accept/${_state.currentUser.username}/${senderUsername}`, { method: "POST" });
        const result = await response.json();
        showNotification(result.message, notifContainer, result.success ? "success" : "error");
        if (result.success) {
            socialCache.isLoaded = false;
            listItem?.remove(); 
            if (socialTabFriends?.classList.contains("active")) {
                loadSocialData(); // Forzar recarga
            }
        } else {
            const actionsDiv = listItem?.querySelector(".social-actions");
            if (actionsDiv) {
                actionsDiv.innerHTML = `<button class="btn-success btn-accept-request">Aceptar</button> <button class="btn-danger btn-reject-request">Rechazar</button>`;
            }
        }
    } catch (error) {
        showNotification("Error de red al aceptar solicitud.", notifContainer, "error");
        const actionsDiv = listItem?.querySelector(".social-actions");
        if (actionsDiv) {
            actionsDiv.innerHTML = `<button class="btn-success btn-accept-request">Aceptar</button> <button class="btn-danger btn-reject-request">Rechazar</button>`;
        }
    }
}

async function rejectFriendRequest(senderUsername, buttonElement) {
    if (!_state.currentUser || !_state.currentUser.username || !buttonElement) return;
    const listItem = buttonElement.closest(".social-list-item");
    const actionsDiv = listItem?.querySelector(".social-actions");
    if (actionsDiv) {
        actionsDiv.textContent = "..."; 
    }
    const notifContainer = document.getElementById('notificaciones');
    try {
        const response = await fetch(`/social/solicitud/reject/${_state.currentUser.username}/${senderUsername}`, { method: "POST" });
        const result = await response.json();
        showNotification(result.message, notifContainer, result.success ? "success" : "error");
        if (result.success) {
            socialCache.pending_received = socialCache.pending_received.filter(u => u !== senderUsername);
            listItem?.remove();
        } else {
            const actionsDiv = listItem?.querySelector(".social-actions");
            if (actionsDiv) {
                actionsDiv.innerHTML = `<button class="btn-success btn-accept-request">Aceptar</button> <button class="btn-danger btn-reject-request">Rechazar</button>`;
            }
        }
    } catch (error) {
        showNotification("Error de red al rechazar solicitud.", notifContainer, "error");
        const actionsDiv = listItem?.querySelector(".social-actions");
        if (actionsDiv) {
            actionsDiv.innerHTML = `<button class="btn-success btn-accept-request">Aceptar</button> <button class="btn-danger btn-reject-request">Rechazar</button>`;
        }
    }
}

async function removeFriend(friendUsername, buttonElement) {
    if (!_state.currentUser || !_state.currentUser.username || !buttonElement) return;
    if (!confirm(`¿Seguro que quieres eliminar a ${friendUsername}?`)) return;
    const listItem = buttonElement.closest(".social-list-item");
    buttonElement.textContent = "...";
    buttonElement.disabled = true;
    const notifContainer = document.getElementById('notificaciones');
    try {
        const response = await fetch(`/social/amigos/remove/${_state.currentUser.username}/${friendUsername}`, { method: "POST" });
        const result = await response.json();
        showNotification(result.message, notifContainer, result.success ? "success" : "error");
        if (result.success) {
            socialCache.friends = socialCache.friends.filter(f => f.username !== friendUsername);
            listItem?.remove();
        } else {
            buttonElement.textContent = "🗑️";
            buttonElement.disabled = false;
        }
    } catch (error) {
        showNotification("Error de red al eliminar amigo.", notifContainer, "error");
        buttonElement.textContent = "🗑️";
        buttonElement.disabled = false;
    }
}

function handleInviteToRoom(targetUsername, buttonElement) {
    const notifContainer = document.getElementById('notificaciones');
    if (!_state.idSala.value) {
        return showNotification("Debes estar en una sala para invitar.", notifContainer, "warning");
    }
    if (!_state.currentUser || !_state.currentUser.username || !buttonElement) return;
    buttonElement.disabled = true;
    buttonElement.textContent = "..."; 
    _socket.emit("invite_to_room", {
        recipient: targetUsername,
        room_id: _state.idSala.value,
    });
}

// --- Chat Privado ---
let privateChatTarget = null; 
async function openPrivateChat(targetUsername) {
    if (!_state.currentUser || !_state.currentUser.username || !modalPrivateChatElement || !chatWithUsernameDisplay || !privateChatMessagesDisplay) return;
    playSound('OpenCloseModal', 0.3);
    privateChatTarget = targetUsername;
    chatWithUsernameDisplay.textContent = escapeHTML(targetUsername);
    privateChatMessagesDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">Cargando historial...</p>';
    modalPrivateChatElement.style.display = "flex";
    if (modalSocialElement) modalSocialElement.style.display = "none"; 
    try {
        const response = await fetch(`/social/messages/${_state.currentUser.username}/${targetUsername}`);
        if (!response.ok) throw new Error("Error al cargar mensajes");
        const messages = await response.json();
        privateChatMessagesDisplay.innerHTML = "";
        messages.forEach(appendPrivateMessage);
        _socket.emit('mark_chat_as_read', { sender: targetUsername });
    } catch (error) {
        console.error("Error al cargar chat:", error);
        privateChatMessagesDisplay.innerHTML = '<p style="text-align: center; color: var(--danger);">Error al cargar historial.</p>';
    }
}
function closePrivateChat() {
    playSound('OpenCloseModal', 0.2);
    if (modalPrivateChatElement) modalPrivateChatElement.style.display = "none";
    privateChatTarget = null; 
}
export function appendPrivateMessage(msgData) {
    if (!privateChatMessagesDisplay || !_state.currentUser) return;
    const msgDiv = document.createElement("div");
    msgDiv.className = "private-message";
    const timestamp = new Date(msgData.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const isSent = msgData.sender === _state.currentUser.username;
    msgDiv.classList.add(isSent ? "sent" : "received");
    msgDiv.innerHTML = `<div>${escapeHTML(msgData.message)}</div><small>${timestamp}</small>`;
    privateChatMessagesDisplay.appendChild(msgDiv);
    privateChatMessagesDisplay.scrollTop = privateChatMessagesDisplay.scrollHeight; 
}
function handleSendPrivateMessage() {
    playSound('ClickMouse', 0.3);
    const message = privateChatInput?.value.trim();
    if (!message || !privateChatTarget || !_state.currentUser || !_state.currentUser.username || !privateChatSendBtn) return;
    privateChatSendBtn.disabled = true;
    privateChatSendBtn.textContent = "...";
    _socket.emit("private_message", {
        target: privateChatTarget,
        message: message,
    });
    if(privateChatInput) privateChatInput.value = "";
}

// --- Manejador de Clics Delegado ---
function handleSocialListClick(event) {
    const targetButton = event.target.closest("button");
    if (!targetButton) return;
    playSound('ClickMouse', 0.3);
    const listItem = targetButton.closest(".social-list-item");
    const username = listItem?.dataset.username;
    if (!username) return;
    if (targetButton.classList.contains("btn-chat-friend")) {
        openPrivateChat(username);
    } else if (targetButton.classList.contains("btn-invite-friend")) {
        handleInviteToRoom(username, targetButton);
    } else if (targetButton.classList.contains("btn-remove-friend")) {
        removeFriend(username, targetButton);
    } else if (targetButton.classList.contains("btn-accept-request")) {
        acceptFriendRequest(username, targetButton);
    } else if (targetButton.classList.contains("btn-reject-request")) {
        rejectFriendRequest(username, targetButton);
    } else if (targetButton.classList.contains("btn-add-friend")) {
        sendFriendRequest(username, targetButton);
    }
}

/** Marca el botón social si hay notificaciones pendientes. */
export function updateSocialNotificationIndicator(hasNotification) {
     btnSocialGlobal?.classList.toggle("has-notification", hasNotification);
     btnSocialWaiting?.classList.toggle("has-notification", hasNotification);
}