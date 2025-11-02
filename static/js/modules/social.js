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

/**
 * Inicializa el módulo social.
 * @param {object} socketRef - Instancia de Socket.IO.
 * @param {object} currentUserRef - Referencia al usuario actual.
 * @param {object} idSalaRef - Referencia al ID de la sala actual.
 */
export function initSocial(socketRef, stateRef) {
    _socket = socketRef;
    _state = stateRef; // Guardamos la referencia a 'state'

    // Cachear elementos DOM del Modal Social
    modalSocialElement = document.getElementById("modal-social");
    btnCerrarSocial = document.getElementById("btn-cerrar-social");
    btnSocialGlobal = document.getElementById("btn-social"); // Botón en el header
    btnSocialWaiting = document.getElementById("btn-social-waiting"); // Botón en espera
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

    // Cachear elementos DOM del Chat Privado
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
    modalSocialElement?.addEventListener('click', (e) => { if (e.target === modalSocialElement) closeSocialModal(); }); // Clic fuera

    socialTabFriends?.addEventListener("click", () => loadSocialTab("friends"));
    socialTabRequests?.addEventListener("click", () => loadSocialTab("requests"));
    socialTabSearch?.addEventListener("click", () => loadSocialTab("search"));

    socialSearchButton?.addEventListener("click", handleSearchUsers);
    socialSearchInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleSearchUsers(); });

    // Delegación de eventos para las listas
    socialFriendsListDisplay?.addEventListener("click", handleSocialListClick);
    socialRequestsListDisplay?.addEventListener("click", handleSocialListClick);
    socialSearchResultsDisplay?.addEventListener("click", handleSocialListClick);

    // Chat Privado
    btnCerrarPrivateChat?.addEventListener("click", closePrivateChat);
    privateChatSendBtn?.addEventListener("click", handleSendPrivateMessage);
    privateChatInput?.addEventListener("keypress", (e) => { if (e.key === 'Enter') handleSendPrivateMessage(); });
}

// --- Lógica del Modal Social ---

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
    loadSocialTab("friends", _state.currentUser.username);
}
function closeSocialModal() {
    playSound('OpenCloseModal', 0.2);
    if (modalSocialElement) modalSocialElement.style.display = 'none';
}

async function loadSocialTab(tabName) {
    if (!_state.currentUser || !_state.currentUser.username) return;
    if (!socialTabFriends || !socialContentFriends) return; // Verificar elementos
    playSound('ClickMouse', 0.3);

    // Reset tabs y content
    [socialTabFriends, socialTabRequests, socialTabSearch].forEach(btn => btn?.classList.remove("active"));
    [socialContentFriends, socialContentRequests, socialContentSearch].forEach(content => content?.classList.remove("active"));

    const loadingHTML = '<p style="text-align: center; color: var(--muted);">Cargando...</p>';
    let targetListElement, endpoint = null, renderFunction, activeTabButton, activeContent;

    if (tabName === "friends") {
        targetListElement = socialFriendsListDisplay;
        endpoint = `/social/amigos/${_state.currentUser.username}`;
        renderFunction = (data) => renderFriendsList(data.friends);
        activeTabButton = socialTabFriends;
        activeContent = socialContentFriends;
    } else if (tabName === "requests") {
        targetListElement = socialRequestsListDisplay;
        endpoint = `/social/amigos/${_state.currentUser.username}`;
        renderFunction = (data) => renderRequestsList(data.pending_received);
        activeTabButton = socialTabRequests;
        activeContent = socialContentRequests;
    } else if (tabName === "search") {
        targetListElement = socialSearchResultsDisplay;
        activeTabButton = socialTabSearch;
        activeContent = socialContentSearch;
        if(socialSearchInput) socialSearchInput.value = "";
        targetListElement.innerHTML = '<p style="text-align: center; color: var(--muted);">Ingresa un nombre para buscar.</p>';
        activeTabButton?.classList.add("active");
        activeContent?.classList.add("active");
        return; // No fetch inicial para búsqueda
    } else {
        return; // Tab desconocida
    }

    if (!targetListElement || !activeTabButton || !activeContent) return; // Salir si falta algún elemento

    targetListElement.innerHTML = loadingHTML;
    activeTabButton.classList.add("active");
    activeContent.classList.add("active");

    // Fetch para friends o requests
    if (endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error(`Network response error ${response.status}`);
            const data = await response.json();
            if (data.error) throw new Error(data.error); // Manejar error devuelto por la API
            renderFunction(data);
        } catch (error) {
            console.error(`Error al cargar ${tabName}:`, error);
            targetListElement.innerHTML = `<p style="text-align: center; color: var(--danger);">Error al cargar: ${error.message}</p>`;
        }
    }
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

        // El ID de la sala actual está en la variable global _idSala (referencia)
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
        switch (user.relation) {
            case "friend": relationHTML = '<span style="color: var(--success); font-size: 0.9em;">Amigo</span>'; break;
            case "pending_sent": relationHTML = '<span style="color: var(--warning); font-size: 0.9em;">Pendiente</span>'; break;
            case "pending_received": relationHTML = '<button class="btn-success btn-accept-request">Aceptar</button>'; break;
            default: relationHTML = '<button class="btn-primary btn-add-friend">Agregar</button>';
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
            const listItem = buttonElement.closest(".social-list-item");
            const actionsDiv = listItem?.querySelector(".social-actions");
            if (actionsDiv) {
                actionsDiv.innerHTML = '<span style="color: var(--warning); font-size: 0.9em;">Pendiente</span>';
            }
        } else {
            // Si falló, restaura el botón (esto estaba bien)
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
          actionsDiv.textContent = "..."; // Feedback visual
      }
    const notifContainer = document.getElementById('notificaciones');

    try {
        const response = await fetch(`/social/solicitud/accept/${_state.currentUser.username}/${senderUsername}`, { method: "POST" });
        const result = await response.json();
        showNotification(result.message, notifContainer, result.success ? "success" : "error");
        if (result.success) {
            listItem?.remove();
            // Recargar amigos si estamos en esa pestaña
            if (socialTabFriends?.classList.contains("active")) {
                loadSocialTab("friends");
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
        actionsDiv.textContent = "..."; // Feedback visual
    }
    const notifContainer = document.getElementById('notificaciones');

    try {
        const response = await fetch(`/social/solicitud/reject/${_state.currentUser.username}/${senderUsername}`, { method: "POST" });
        const result = await response.json();
        showNotification(result.message, notifContainer, result.success ? "success" : "error");
        if (result.success) {
            listItem?.remove();
        } else {
            // Restaurar botones si falla
            const actionsDiv = listItem?.querySelector(".social-actions");
            if (actionsDiv) {
                actionsDiv.innerHTML = `<button class="btn-success btn-accept-request">Aceptar</button> <button class="btn-danger btn-reject-request">Rechazar</button>`;
            }
        }
    } catch (error) {
        showNotification("Error de red al rechazar solicitud.", notifContainer, "error");
        // Restaurar botones si falla
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
    buttonElement.textContent = "..."; // Feedback visual de envío

    _socket.emit("invite_to_room", {
        recipient: targetUsername,
        room_id: _state.idSala.value,
    });
    // El servidor responderá con 'invite_sent_confirm'
}

// --- Chat Privado ---

let privateChatTarget = null; // Mantiene el usuario con el que se está chateando

async function openPrivateChat(targetUsername) {
    if (!_state.currentUser || !_state.currentUser.username || !modalPrivateChatElement || !chatWithUsernameDisplay || !privateChatMessagesDisplay) return;
    playSound('OpenCloseModal', 0.3);

    privateChatTarget = targetUsername;
    chatWithUsernameDisplay.textContent = escapeHTML(targetUsername);
    privateChatMessagesDisplay.innerHTML = '<p style="text-align: center; color: var(--muted);">Cargando historial...</p>';
    modalPrivateChatElement.style.display = "flex";
    if (modalSocialElement) modalSocialElement.style.display = "none"; // Ocultar modal social

    try {
        const response = await fetch(`/social/messages/${_state.currentUser.username}/${targetUsername}`);
        if (!response.ok) throw new Error("Error al cargar mensajes");
        const messages = await response.json();
        privateChatMessagesDisplay.innerHTML = "";
        messages.forEach(appendPrivateMessage);
    } catch (error) {
        console.error("Error al cargar chat:", error);
        privateChatMessagesDisplay.innerHTML = '<p style="text-align: center; color: var(--danger);">Error al cargar historial.</p>';
    }
}

function closePrivateChat() {
    playSound('OpenCloseModal', 0.2);
    if (modalPrivateChatElement) modalPrivateChatElement.style.display = "none";
    privateChatTarget = null; // Limpiar objetivo al cerrar
    // No reabrir el modal social automáticamente, el usuario puede querer volver al juego/lobby
}

/** Añade un mensaje a la ventana de chat privado. */
export function appendPrivateMessage(msgData) {
    if (!privateChatMessagesDisplay || !_state.currentUser) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = "private-message";
    const timestamp = new Date(msgData.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Determinar si el mensaje es enviado o recibido
    const isSent = msgData.sender === _state.currentUser.username;
    msgDiv.classList.add(isSent ? "sent" : "received");

    msgDiv.innerHTML = `<div>${escapeHTML(msgData.message)}</div><small>${timestamp}</small>`;
    privateChatMessagesDisplay.appendChild(msgDiv);
    privateChatMessagesDisplay.scrollTop = privateChatMessagesDisplay.scrollHeight; // Auto-scroll
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
    // El servidor confirmará con 'message_sent_confirm'
}

/** Manejador centralizado para clics en listas sociales. */
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