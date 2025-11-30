# 🎲 VoltRace - Multiplayer Real-time Game

![Versión de Python](https://img.shields.io/badge/python-3.10-blue.svg)
![Framework](https://img.shields.io/badge/Flask-2.x-black.svg)
![Real-time](https://img.shields.io/badge/Socket.IO-brightgreen.svg)
![Coverage](https://img.shields.io/badge/Tests-Passing-success)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
![CI/CD](https://img.shields.io/badge/GitHub%20Actions-Active-blue)

### 🚀 ¡Juega ahora en Producción!
### [https://voltrace-game.onrender.com/](https://voltrace-game.onrender.com/)

**VoltRace** es una implementación web moderna de un juego de mesa competitivo en tiempo real. Más que un juego, es una demostración de **arquitectura de software robusta**, combinando WebSockets para la sincronización instantánea, persistencia de datos relacional y un pipeline de **DevOps** completo con Testing automatizado y CI/CD.

---

## 🏗️ Ingeniería y Arquitectura

Este proyecto ha sido refactorizado para cumplir con los más altos estándares de calidad de software:

### 1. 🧪 Estrategia de Testing (Suite de +30 Pruebas)
El proyecto cuenta con una cobertura de pruebas exhaustiva dividida en 4 capas críticas, ejecutadas automáticamente mediante **Pytest** y **Playwright**:

* **Unit Testing (Lógica de Juego):** Verificación matemática de mecánicas de daño, cooldowns, perks (ej: *Último Aliento*) y condiciones de victoria.
* **Edge Cases & Stress Testing:** Pruebas específicas para situaciones límite como desconexiones en turno activo, intentos de ingresar a salas llenas y conflictos de habilidades complejas.
* **Integration Testing (API REST):** Validación de endpoints, autenticación de usuarios, manejo de sesiones y respuestas JSON con base de datos en memoria (`sqlite:///:memory:`).
* **Socket Testing (Real-time):** Simulación de clientes `socket.io` conectados simultáneamente para validar la creación de salas, chat en vivo y sincronización de turnos.
* **E2E Testing (Frontend):** Pruebas de extremo a extremo con **Playwright** que navegan en la aplicación de producción, validando flujos críticos de UX (Registro, Login, Navegación) como un usuario real.

### 2. ⚡ Rendimiento y Base de Datos
* **Optimización N+1:** Implementación de `selectinload` y estrategias de carga eficiente en SQLAlchemy para reducir drásticamente las consultas a la base de datos en el módulo social.
* **Gestión de Concurrencia:** Uso de `db_lock` y contextos de aplicación seguros para manejar operaciones de base de datos dentro de hilos asíncronos de Socket.IO.

### 3. 🔍 Observabilidad y Logging
* **Structured Logging:** Migración total de `print statements` a un sistema de `logging` profesional con rotación de archivos y niveles de severidad (`INFO`, `WARNING`, `ERROR`), permitiendo un monitoreo efectivo en producción sin ruido en la consola.

### 4. ⚙️ DevOps & CI/CD
* **Docker Multi-stage Builds:** Imagen optimizada separando la fase de compilación (`builder`) de la ejecución (`runner`), reduciendo el tamaño de la imagen y eliminando dependencias innecesarias.
* **GitHub Actions:** Pipeline de Integración Continua que ejecuta:
    * **Linter:** Verificación de estilo con `Black` y `Flake8`.
    * **Tests:** Ejecución automática de la suite de pruebas en cada push.

---

## 💻 Stack Tecnológico

### Backend
-   **Python 3.10** & **Flask**: Núcleo de la aplicación.
-   **Flask-SocketIO (Eventlet)**: Comunicación bidireccional de baja latencia.
-   **SQLAlchemy**: ORM para manejo eficiente de datos.
-   **PostgreSQL**: Base de datos relacional en la nube (Neon Tech).

### Frontend
-   **JavaScript (ES6 Modules)**: Arquitectura modular para lógica de cliente.
-   **Socket.IO Client**: Sincronización de estado en tiempo real.

### QA & Herramientas
-   **Pytest**: Framework de testing principal.
-   **Playwright**: Automatización de navegadores.
-   **Docker**: Containerización.
-   **Black & Flake8**: Calidad de código.

---

## 🛠️ Ejecución de la Suite de Tests (Para Desarrolladores)

Si deseas verificar la integridad del código o contribuir, puedes ejecutar la suite de pruebas localmente:

1.  **Instalar dependencias de desarrollo:**
    ```bash
    pip install -r requirements.txt
    pip install pytest pytest-playwright
    playwright install
    ```

2.  **Correr pruebas de Lógica, API y Sockets:**
    ```bash
    pytest -v
    ```

3.  **Correr pruebas visuales (E2E):**
    ```bash
    # Ejecuta el navegador en modo visible para ver al bot interactuar
    pytest tests/test_frontend.py --headed --slowmo 1000
    ```

---

## ⚖️ Licencia
Este proyecto está bajo la Licencia [MIT](LICENSE.txt).