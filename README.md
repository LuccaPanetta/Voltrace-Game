# 🎲 VoltRace - Documentación Completa

![Versión de Python](https://img.shields.io/badge/python-3.10-blue.svg)
![Framework](https://img.shields.io/badge/Flask-2.x-black.svg)
![Real-time](https://img.shields.io/badge/Socket.IO-brightgreen.svg)
![Database](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)
![Deployment](https://img.shields.io/badge/Deploy-Render-lightgrey.svg)
![Container](https://img.shields.io/badge/Docker-ready-blue.svg)

### ¡Probá VoltRace ahora mismo!
### [https://voltrace-game.onrender.com/](https://voltrace-game.onrender.com/)

**VoltRace** es una implementación web moderna del clásico juego de mesa, diseñada para múltiples jugadores en tiempo real. Cuenta con un sistema completo de usuarios (con reseteo de contraseña por email), persistencia en base de datos PostgreSQL, logros, perks (mejoras), un sistema de progresión de "Maestría de Kit" con Títulos y Animaciones cosméticas, funciones sociales y un servidor de producción listo para *deploy* con Docker.

## 📋 Índice
1.  [Descripción General](#-descripción-general)
2.  [Características Principales](#-características-principales)
3.  [Sistemas Implementados](#️-sistemas-implementados-clases-principales)
4.  [Tecnologías Utilizadas](#-tecnologías-utilizadas)

---

## 📖 Descripción General

### 🎮 Características del Juego
-   **2-4 jugadores** por partida.
-   **Tablero de 75 casillas** con casillas especiales y paquetes de energía.
-   **Sistema de 5 Kits Únicos**: Los jugadores eligen un Kit (Táctico, Ingeniero, etc.) que define sus 4 habilidades únicas para la partida.
-   **Sistema de Energía** (puntos de vida) y **Puntos de Mejora (PM)** para perks.
-   **Sistema de Cazarrecompensas (Bounty)**: A partir de la ronda 10, el jugador en 1er lugar es marcado y otorga una recompensa de PM y Energía al primer jugador que le inflija daño.
-   **Chat en tiempo real** (en sala y en partida).
-   **Sistema de Perks** (mejoras pasivas aleatorias compradas durante la partida).
-   **Sistema de Logros** con recompensas de XP.
-   **Ranking global**.
-   **Funciones sociales** (amigos, chat privado, presencia, invitaciones).

---
## ⭐ Características Principales

### 🔐 **Sistema de Usuarios (Flask-Login + SQLAlchemy)**
-   **Registro** con email/username/password (validado y hasheado).
-   **Login** persistente basado en sesiones seguras.
-   **Recuperación de Contraseña**: Flujo completo de "Olvidé mi contraseña" con envío de token único por email (vía SendGrid).
-   **Persistencia** en base de datos **PostgreSQL** (gestionada en Neon).
-   **Perfil de usuario** con nivel, XP, estadísticas, avatar y kit preferido.

### 🛡️ **Sistema de Arsenal (Maestría de Kit)**
-   **Progresión Asincrónica**: Ganar partidas otorga "XP de Maestría" para el kit específico que se utilizó (si el jugador es Nivel 5+).
-   **Desbloqueo de Títulos**: Alcanzar el Nivel 5 de Maestría con un kit desbloquea un Título cosmético (ej. "Título: 'Táctico'").
-   **Sistema de Títulos Equipables**: Los jugadores pueden equipar los títulos que han ganado, mostrándolos junto a su nombre en el lobby.
-   **Animaciones Cosméticas**: Alcanzar el Nivel 10 de Maestría desbloquea una animación de habilidad única para ese kit (ej. "Sabotaje Sónico").

### 🤝 **Sistema Social Completo (Socket.IO + API REST)**
-   **Lista de Amigos**: Agregar, aceptar/rechazar solicitudes, eliminar amigos.
-   **Chat Privado**: Conversaciones 1-a-1 en tiempo real con historial persistente en la DB (modelo `PrivateMessage`).
-   **Presencia en Tiempo Real**: Indicadores de estado (Online, Offline, En Lobby, En Partida) actualizados vía *heartbeat* de Socket.IO.
-   **Invitaciones a Sala**: Invitar amigos online (que estén en el lobby) a unirse a tu sala actual.

### 🏆 **Sistema de Logros (Base de Datos)**
-   **Amplia variedad de logros** (>40) cubriendo gameplay, social, persistencia, etc.
-   **Desbloqueo automático** basado en eventos (`check_achievement`) y persistido en la tabla `UserAchievement`.
-   **Recompensas de XP** por cada logro.
-   **Modal de Logros** con visualización de progreso y fecha de desbloqueo, con caché en el cliente.

### 🎬 **Sistema de Animaciones (CSS + JS)**
-   **Movimiento de fichas** visualizado en el tablero (CSS Transitions).
-   **Efectos visuales** para habilidades, energía, trampas, colisiones.
-   **Celebración de victoria** (confetti).
-   **Animaciones Cosméticas Únicas** (Nv. 10 de Maestría) que reemplazan los efectos genéricos.
-   **Opción para activar/desactivar** animaciones (persiste en `localStorage`).

---

## 🛠️ Sistemas Implementados (Clases Principales)

### 1. **Flask App (`app.py`)**
-   **Rutas HTTP**: `/login`, `/register`, `/logout`, `/forgot-password`, `/reset-password`, `/profile`, `/leaderboard`, API social.
-   **Handlers SocketIO**: `connect`, `authenticate`, `crear_sala`, `unirse_sala`, `lanzar_dado`, `usar_habilidad`, `comprar_perk`, `enviar_mensaje`, `private_message`, `invite_to_room`, `solicitar_revancha`, `arsenal:cargar_maestria`, `arsenal:equip_title`, etc.
-   **Clase `SalaJuego`**: Gestión de estado de salas individuales (jugadores, instancia de juego).
-   **Gestión de Hilos**: Usa `threading` para tareas de base de datos asincrónicas (guardar stats, XP de maestría) para no bloquear el chat ni el juego.

### 2. **JuegoOcaWeb (`juego_web.py`)**
-   **`__init__`**: Inicializa tablero, jugadores, y asigna habilidades basadas en el `kit_id` seleccionado.
-   **Flujo de Turno**: `paso_1_lanzar_y_mover` y `paso_2_procesar_casilla_y_avanzar`.
-   **`_avanzar_turno`**: Contiene la lógica para asignar la Cazarrecompensas (Bounty) al líder de la partida.
-   **`_procesar_recompensa_caza`**: Función *helper* para otorgar la recompensa y marcarla como reclamada.
-   **`_hab_*`**: Métodos para cada habilidad (ej. `_hab_sabotaje`, `_hab_bomba_energetica`).
-   **`comprar_pack_perk` / `activar_perk_seleccionado`**: Maneja la compra y activación de perks.

### 3. **Models (`models.py`)**
-   Define las clases (`User`, `PrivateMessage`, `Achievement`, `UserAchievement`) que mapean a la base de datos **PostgreSQL**.
-   **`UserKitMaestria`**: Nuevo modelo para rastrear el `xp` y `cosmetic_unlocked` para cada kit de cada usuario.
-   Incluye métodos helper en `User` para manejar reseteo de tokens y relaciones sociales.

### 4. Lógica de Cliente (JavaScript Modular)
El frontend utiliza **módulos de JavaScript (ES6+)** para organizar la lógica, importados en `main.js`.

-   **Módulos Principales**: `main.js`, `auth.js`, `socketHandlers.js`, `gameUI.js`, `lobby.js`, `social.js`, `achievements.js`, `perks.js`, `arsenal.js`, `animations.js`, `utils.js`.
-   **Listeners SocketIO (`socketHandlers.js`)**: Define cómo reacciona el cliente a eventos del servidor (`juego_iniciado`, `paso_1_resultado_movimiento`, `arsenal:maestria_data`, etc.).
-   **`checkAndPlayCosmetic`**: Función clave que revisa el `state.cosmeticsUnlocked` y decide si reproducir una animación normal o la de Maestría Nv. 10.

---

## 💻 Tecnologías Utilizadas

### **Backend**
-   **Python 3.10**
-   **Flask** - Microframework web y API REST.
-   **Flask-SocketIO** / **Eventlet** - Comunicación WebSockets en tiempo real y concurrencia.
-   **Gunicorn** - Servidor WSGI para producción.
-   **Flask-SQLAlchemy** - ORM para interacción con la base de datos.
-   **PostgreSQL** (gestionado en **Neon**) - Base de datos de producción.
-   **psycopg2-binary** - Adaptador de Python para PostgreSQL.
-   **Flask-Login** - Gestión de sesiones de usuario.
-   **Flask-Mail** / **SendGrid** - Para envío de emails de reseteo de contraseña.

### **Frontend**
-   **HTML5**
-   **CSS3** (Layouts con Grid + Flexbox, Custom Properties, Keyframe Animations).
-   **JavaScript (ES6+ Módulos)** - Lógica del cliente, Socket.IO client, Async/await (fetch), Manipulación del DOM, Delegación de Eventos.

### **DevOps & Despliegue**
-   **Docker** / **docker-compose.yml** - Containerización para un entorno de producción consistente.
-   **Render** - Plataforma de hosting (PaaS) para el servicio web y la base de datos.
-   **UptimeRobot** - Monitoreo de *uptime*.
-   **Neon** - Base de datos PostgreSQL *serverless* en la nube.

## ⚖️ Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.