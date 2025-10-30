# 🎲 VoltRace - DOCUMENTACIÓN COMPLETA

## 📋 Índice
1.  [Descripción General](#-descripción-general)
2.  [Arquitectura del Sistema](#️-arquitectura-del-sistema)
3.  [Estructura de Archivos](#-estructura-de-archivos)
4.  [Características Principales](#-características-principales)
5.  [Sistemas Implementados](#️-sistemas-implementados)
6.  [Tecnologías Utilizadas](#-tecnologías-utilizadas)
7.  [Instalación y Configuración](#-instalación-y-configuración)
8.  [Guía de Código](#-guía-de-código)
9.  [Características Técnicas](#️-características-técnicas)

---

## 📖 Descripción General

**VoltRace** is a modern web implementation of the classic board game, designed for multiple players in real-time. It features a complete user system, database persistence, achievements, perks, social features, animations, and modern gaming elements.

### 🎮 Game Features
-   **2-4 players** per match
-   **75-square board** with special tiles and energy packs
-   **Unique abilities** per player (assigned randomly from pools)
-   **Energy system** (health points) and **Command Points (PM)** for perks
-   **Player collisions** with energy loss/stealing
-   **Real-time chat** (in-lobby and in-game)
-   **Perk system** (passive upgrades)
-   **Achievement system** with XP rewards
-   **Leveling system** (1-100)
-   **Global ranking**
-   **Social features** (friends, private chat, presence, invites)

---
## ⭐ Características Principales

### 🔐 **Sistema de Usuarios (Flask-Login + SQLAlchemy)**
-   **Registro** con email/username/password (validado).
-   **Login** persistente basado en sesiones seguras.
-   **Hashing seguro** de contraseñas (via Werkzeug).
-   **Persistencia** en base de datos SQLite (`User` model).
-   **Perfil de usuario** con nivel, XP, y estadísticas de juego.

### ✨ **Sistema de Perks (Mejoras Pasivas)**
-   Compra de **Packs de Perks** (Básico, Intermedio, Avanzado) usando Puntos de Mando (PM).
-   **Oferta aleatoria** de perks al comprar un pack.
-   **Activación de perks** que modifican habilidades o mecánicas del juego (ej. `Aislamiento`, `Enfriamiento Rápido`, `Último Aliento`).
-   Perks organizados por **tiers** y con **requisitos de habilidad**.
-   Persistencia de perks activos en `JugadorWeb`.

### 🤝 **Sistema Social Completo**
-   **Lista de Amigos**: Agregar, aceptar/rechazar solicitudes, eliminar amigos.
-   **Búsqueda de Usuarios**: Encontrar otros jugadores para agregar.
-   **Chat Privado**: Conversaciones 1-a-1 en tiempo real con historial persistente (DB).
-   **Presencia**: Indicadores de estado (Online, Offline, En Lobby, En Partida).
-   **Invitaciones a Sala**: Invitar amigos online a unirse a tu sala actual.

### 🏆 **Sistema de Logros (Base de Datos)**
-   **Amplia variedad de logros** (>40) cubriendo gameplay, social, persistencia, etc.
-   **Desbloqueo automático** basado en eventos del juego (`check_achievement`).
-   **Recompensas de XP** por cada logro.
-   **Persistencia** en base de datos (`Achievement`, `UserAchievement` models).
-   **Modal de Logros** con visualización de progreso y fecha de desbloqueo.

### 📈 **Sistema de Niveles y XP**
-   **Niveles 1-100** con fórmula de XP progresiva.
-   **Ganancia de XP** por acciones: jugar partida, ganar, usar habilidad, enviar mensaje, desbloquear logro.
-   **Visualización** del nivel y XP en el perfil.

### 🥇 **Ranking Global (Top 50)**
-   **Clasificación** basada en **Nivel** y luego **XP**.
-   **Visualización** en el Lobby (Top 5) y en una pestaña dedicada (Top 50).
-   **Estadísticas mostradas**: Nivel, XP, Partidas Jugadas, Victorias, Win Rate %.

### 🎬 **Sistema de Animaciones (CSS + JS)**
-   **Movimiento de fichas** visualizado en el tablero (CSS Transitions).
-   **Efectos visuales** para habilidades, energía, trampas, colisiones (usando clases de `animations.css`).
-   **Celebración de victoria** (confetti).
-   **Notificaciones animadas** para logros y eventos.
-   **Transiciones suaves** entre pantallas.
-   **Opción para activar/desactivar** animaciones (persiste en `localStorage`).

---

## 🛠️ Sistemas Implementados (Clases Principales)

### 1. **Flask App (`app.py`)**
-   **Rutas HTTP**: `/login`, `/register`, `/profile`, `/leaderboard`, API social.
-   **Handlers SocketIO**: `connect`, `authenticate`, `crear_sala`, `unirse_sala`, `lanzar_dado`, `usar_habilidad`, `comprar_perk`, `seleccionar_perk`, `enviar_mensaje`, `private_message`, `invite_to_room`, `solicitar_revancha`, etc.
-   **Clase `SalaJuego`**: Gestión de estado de salas individuales (jugadores, instancia de juego).
-   **Gestión de Sesiones**: Asociación de `request.sid` (SocketIO) con `username` (Flask-Login).

### 2. **JuegoOcaWeb (`juego_web.py`)**
-   **`__init__`**: Inicializa tablero, jugadores, habilidades, perks.
-   **`ejecutar_turno_dado`**: Lógica central del turno (dado, movimiento, efectos).
-   **`_procesar_efectos_posicion`**: Activa casillas especiales, packs, colisiones.
-   **`usar_habilidad_jugador`**: Valida y despacha a la lógica específica de la habilidad (`_hab_*`).
-   **`comprar_pack_perk` / `activar_perk_seleccionado`**: Maneja la compra y activación de perks.
-   **`determinar_ganador` / `_calcular_puntaje_final_avanzado`**: Lógica de fin de juego y puntuación.

### 3. **SocialSystem (`social.py`)**
-   **`send_friend_request`, `accept_friend_request`, etc.**: Gestión de amistades (interactúa con `User` model).
-   **`send_private_message`, `get_conversation`**: Chat privado (interactúa con `PrivateMessage` model).
-   **`update_user_presence`, `_get_user_status`**: Manejo de estado online/offline/in_game.
-   **`send_room_invitation`**: Lógica de invitaciones a sala.

### 4. **AchievementSystem (`achievements.py`)**
-   **`achievements_config`**: Definición estática de todos los logros.
-   **`check_achievement`**: Punto de entrada para verificar si un evento desbloquea logros.
-   **`_check_*_achievements`**: Funciones helper para evaluar condiciones específicas.
-   **`get_user_achievement_progress`**: Calcula y formatea el estado de todos los logros para un usuario (interactúa con `UserAchievement` model).

### 5. **Models (`models.py`)**
-   Define las clases (`User`, `PrivateMessage`, `Achievement`, `UserAchievement`) que mapean a tablas de la base de datos SQLite.
-   Incluye métodos helper en `User` para manejar relaciones sociales (`add_friend`, `send_friend_request`, etc.).

### 6. **Cliente JavaScript (`script.js`)**
-   **Inicialización**: Conexión SocketIO, caché de elementos DOM.
-   **Listeners SocketIO**: Define cómo reacciona el cliente a eventos del servidor (`juego_iniciado`, `turno_ejecutado`, `nuevo_mensaje`, etc.).
-   **Funciones de Renderizado**: `renderTablero`, `renderJugadoresEstado`, `renderEventos`, etc.
-   **Manejo de UI**: Funciones `show`, `setLoading`, `showNotification`, modales, etc.
-   **Lógica de Interacción**: Handlers para clics en botones (lanzar dado, usar habilidad, comprar perk, chat, social).

### 7. **AnimationSystem (`animations.js`)**
-   **Clase `AnimationSystem`**: Provee métodos para activar efectos visuales (ej. `shakeBoard`, `celebrateVictory`).
-   **Integración con CSS**: Aplica/remueve clases definidas en `animations.css`.

---

## 💻 Tecnologías Utilizadas

### **Backend**
-   **Python 3.8+**
-   **Flask** - Microframework web y API REST.
-   **Flask-SocketIO** - Comunicación WebSockets en tiempo real.
-   **Flask-SQLAlchemy** - ORM para interacción con la base de datos.
-   **SQLAlchemy** - Toolkit SQL y ORM subyacente.
-   **Flask-Login** - Gestión de sesiones de usuario y autenticación.
-   **Werkzeug** - Utilidades WSGI (incluye hashing de contraseñas).
-   **SQLite** - Motor de base de datos (archivo `voltrace.db`).
-   **uuid**, **datetime**, **threading**.

### **Frontend**
-   **HTML5** - Estructura semántica.
-   **CSS3** - Estilos modernos y animaciones.
    -   Arquitectura Modular (múltiples archivos CSS).
    -   Custom Properties (variables CSS).
    -   Grid + Flexbox layouts.
    -   Responsive Design (mobile-first, `clamp()`, media queries).
    -   Keyframe Animations.
-   **JavaScript (ES6+)** - Lógica del cliente.
    -   Socket.IO Client.
    -   Async/await para llamadas API (fetch).
    -   Manipulación del DOM.
    -   Manejo de eventos (delegación).

### **Comunicación**
-   **Socket.IO** (sobre WebSockets) - Para eventos de juego en tiempo real, chat, presencia.
-   **HTTP/HTTPS** - Para API REST (login, register, profile, leaderboard).

---

## 🚀 Instalación y Configuración

### **Prerrequisitos**
-   Python 3.8 o superior instalado.
-   `pip` (gestor de paquetes de Python).
-   Un navegador web moderno.

### **Instalación**
```bash
# 1. Clona o descarga el repositorio del proyecto
# git clone <url-del-repositorio>
# cd VoltRace

# 2. (Opcional pero recomendado) Crea y activa un entorno virtual
# python -m venv venv
# source venv/bin/activate  # En Linux/macOS
# .\venv\Scripts\activate   # En Windows

# 3. Instala las dependencias de Python
pip install -r requirements.txt

# 4. Ejecuta el servidor Flask
#    La base de datos (voltrace.db) se creará automáticamente la primera vez.
python app.py

# 5. Abre tu navegador web y ve a:
#    [http://127.0.0.1:5000](http://127.0.0.1:5000)  
