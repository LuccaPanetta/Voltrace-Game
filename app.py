import eventlet
eventlet.monkey_patch()
# ===================================================================
# APLICACIÓN PRINCIPAL DEL SERVIDOR - VOLTRACE (app.py)
# ===================================================================
#
# Este archivo es el punto de entrada principal del servidor Flask.
# Maneja:
# - Configuración de Flask, SocketIO, SQLAlchemy y Flask-Login.
# - Definición de todas las rutas HTTP (API) para autenticación,
#   perfiles, rankings, amigos, etc.
# - Definición de todos los handlers de Socket.IO para la
#   comunicación en tiempo real (salas, juego, chat, perks).
# - Gestión del estado global del servidor (salas_activas,
#   sessions_activas, revanchas_pendientes).
# - Lógica de inicio de juego, revancha y limpieza de salas.
#
# Módulos que utiliza:
# - juego_web.py: Para la lógica de la partida.
# - models.py: Para la base de datos (User, Achievement, etc.).
# - achievements.py: Para el sistema de logros.
# - social.py: Para el sistema de amigos y chat.
#
# ===================================================================

# ===================================================================
# --- 1. IMPORTACIONES Y CONFIGURACIÓN INICIAL ---
# ===================================================================

from flask import Flask, render_template, request, jsonify, session, flash, url_for, redirect, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_mail import Mail, Message
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail, TrackingSettings, ClickTracking
import json
import uuid                    # Para generar IDs únicos de salas
from datetime import datetime  # Para timestamps
from threading import Timer
import threading              # Para tareas en background
import time                   # Para delays y timers
import traceback
import os
import math                   

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Importaciones de nuestros módulos locales
from juego_web import JuegoOcaWeb        # Lógica del juego
from achievements import AchievementSystem  # Sistema de logros
from social import SocialSystem          # Sistema social
from models import User, db              # Modelos de base de datos
from habilidades import crear_habilidades
from perks import PERKS_CONFIG

# --- Configuración de Flask ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# --- Configuración de Flask-Mail ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'voltrace.bot@gmail.com')

mail = Mail(app)

def send_reset_email(user):
    try:
        token = user.get_reset_token()
        # Generamos la URL que irá en el email
        reset_url = url_for('reset_token', token=token, _external=True)
        
        # 1. Obtenemos la API Key y el email remitente de las variables de entorno
        sendgrid_api_key = os.environ.get('MAIL_PASSWORD') 
        from_email = os.environ.get('MAIL_DEFAULT_SENDER', 'voltrace.bot@gmail.com')
        
        if not sendgrid_api_key:
            print("!!! ERROR FATAL: SENDGRID_API_KEY (MAIL_PASSWORD) no está configurada.")
            return False

        # 2. Creamos el contenido del email 
        content = f'''Para restablecer tu contraseña, visitá el siguiente enlace:
{reset_url}

Si no solicitaste este cambio, simplemente ignorá este email.
'''

        # 3. Creamos el objeto Mail de SendGrid 
        message = SendGridMail(
            from_email=from_email,
            to_emails=user.email,
            subject='VoltRace - Restablecimiento de Contraseña',
            plain_text_content=content) 
        tracking_settings = TrackingSettings(
            click_tracking=ClickTracking(enable=False, enable_text=False)
        )
        message.tracking_settings = tracking_settings

        print(f"--- DEBUG: Intentando enviar email a {user.email} (vía SendGrid API)...")

        # 4. Inicializamos el cliente y enviamos el email por la API WEB
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)

        # 5. Verificamos la respuesta de SendGrid 
        if response.status_code >= 200 and response.status_code < 300:
            print(f"--- DEBUG: Email enviado exitosamente (Status: {response.status_code}) ---")
            return True
        else:
            # Si SendGrid da un error, lo veremos en los logs de Render
            print("!!! ERROR FATAL AL ENVIAR EMAIL (Respuesta de SendGrid) !!!")
            print(f"Status Code: {response.status_code}")
            print(f"Body: {response.body}")
            return False
        
    except Exception as e:
        print("!!! ERROR FATAL AL ENVIAR EMAIL (Excepción de Python) !!!")
        print(f"Error: {e}")
        traceback.print_exc() # Imprime el traceback completo
        return False
    
# --- Configuración de la Base de Datos (SQLAlchemy) ---
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Si estamos en producción
    print("INFO: Usando base de datos de producción (PostgreSQL).")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # Verifica la conexión antes de usarla
        'pool_recycle': 280,    # Recicla la conexión cada 280s 
        'pool_timeout': 20,     # Tiempo de espera para obtener una conexión
    }
else:
    print("ADVERTENCIA: DATABASE_URL no encontrada. Usando 'voltrace.db' (SQLite) local.")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'voltrace.db')
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app) # Conectar DB a la App

# --- Configuración de Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # Le dice a flask_login cómo encontrar un usuario por su ID
    return User.query.get(int(user_id))

XP_BASE_PARA_NIVEL = 500 # XP necesaria para Nivel 2

def calculate_level_from_xp(xp):
    if xp < XP_BASE_PARA_NIVEL:
        return 1
    level = int(xp // XP_BASE_PARA_NIVEL) + 1
    return level

def update_xp_and_level(user, xp_to_add):
    if not user or xp_to_add == 0:
        return False

    try:
        # Asegurarse que los valores no sean None
        current_level = user.level or 1
        user.xp = (user.xp or 0) + xp_to_add
        
        new_level = calculate_level_from_xp(user.xp)
        
        level_up = False
        if new_level > current_level:
            user.level = new_level
            level_up = True
        
        db.session.commit()
        return level_up
    except Exception as e:
        db.session.rollback()
        print(f"!!! ERROR al actualizar XP/Nivel para {user.username}: {e}")
        return False

def _procesar_creacion_sala_db_async(app, sid, username):
    with app.app_context():
        try:
            print(f"--- THREAD: Procesando XP/Logros de creación de sala para: {username}")
            user = User.query.filter_by(username=username).first()
            if user:
                user.rooms_created = getattr(user, 'rooms_created', 0) + 1 
                level_up = update_xp_and_level(user, 5) # 5 XP por crear sala
                if level_up:
                    socketio.emit('level_up', {'new_level': user.level, 'xp': user.xp}, to=sid)
                
                # Verificar logros
                unlocked_list = achievement_system.check_achievement(username, 'room_created')
                if unlocked_list:
                    socketio.emit('achievements_unlocked', {
                        'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_list]
                    }, to=sid)
            print(f"--- THREAD: Fin de procesamiento de creación de sala para: {username}")
        except Exception as e:
            print(f"!!! ERROR FATAL en _procesar_creacion_sala_db_async: {e}")
            traceback.print_exc()

def _procesar_habilidad_db_async(app, sid, username, event_data=None):
    with app.app_context():
        try:
            if event_data is None:
                event_data = {} # Asegurar que sea un dict
                
            print(f"--- THREAD: Procesando XP/Logros de habilidad para: {username}. Event data: {event_data}")
            user_db = User.query.filter_by(username=username).first()
            if user_db:
                # Actualizar XP y Nivel
                user_db.abilities_used = getattr(user_db, 'abilities_used', 0) + 1
                level_up = update_xp_and_level(user_db, 10) # 10 XP por usar habilidad
                if level_up:
                    socketio.emit('level_up', {'new_level': user_db.level, 'xp': user_db.xp}, to=sid)
            
            # Pasar el event_data completo a check_achievement
            unlocked_list = achievement_system.check_achievement(username, 'ability_used', event_data)

            if unlocked_list:
                socketio.emit('achievements_unlocked', {
                    'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_list]
                }, to=sid)
            
            print(f"--- THREAD: Fin de procesamiento para: {username}")
        except Exception as e:
            print(f"!!! ERROR FATAL en _procesar_habilidad_db_async: {e}")
            traceback.print_exc()

# --- Configurar SocketIO ---
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Inicialización de Sistemas ---
achievement_system = AchievementSystem()
social_system = SocialSystem()

# --- Creación de Tablas de DB (si no existen) ---
with app.app_context():
    db.create_all()
    print("Base de datos inicializada y tablas creadas (si no existían).")
    try:
        from models import Achievement # Importar el modelo
        
        # Obtener todos los IDs de logros que YA están en la DB
        existing_ids = {ach.internal_id for ach in Achievement.query.all()}
        
        # Iterar sobre la configuración en achievements.py
        new_achievements_added = 0
        for internal_id, config in achievement_system.achievements_config.items():
            if internal_id not in existing_ids:
                # Si el logro falta en la DB, crearlo
                new_ach = Achievement(
                    internal_id=internal_id,
                    name=config.get('name', 'Logro Sin Nombre'),
                    description=config.get('description', ''),
                    icon=config.get('icon', '⭐'),
                    xp_reward=config.get('xp_reward', 0)
                )
                db.session.add(new_ach)
                new_achievements_added += 1
                print(f"Sincronizando DB: Añadiendo logro '{internal_id}'...")
        
        # Guardar los cambios
        if new_achievements_added > 0:
            db.session.commit()
            print(f"¡Sincronización de Logros completa! Se añadieron {new_achievements_added} nuevos logros a la DB.")
        else:
            print("Sincronización de Logros: La DB ya está actualizada.")
            
    except Exception as e:
        db.session.rollback()
        print(f"!!! ERROR al sincronizar la tabla de Logros: {e}")
        traceback.print_exc()

# --- Variables Globales del Servidor ---
salas_activas = {}              # Diccionario para guardar las salas activas
revanchas_pendientes = {}       # Para manejar la lógica de revancha
sessions_activas = {}           # Mapeo de SID de SocketIO a username

# --- Constantes para Revancha ---
TIEMPO_MAXIMO_REVANCHA = 45 
MIN_JUGADORES_REVANCHA = 2

# --- Definición de la Clase SalaJuego ---
class SalaJuego:
    def __init__(self, id_sala):
        self.id_sala = id_sala
        # Diccionario de jugadores conectados: {'sid': {'nombre': str, 'sid': str, 'conectado': bool}}
        self.jugadores = {}
        self.espectadores = {} # (No usado actualmente, pero puede ser útil)
        self.juego = None # Instancia de JuegoOcaWeb
        self.estado = 'esperando' # 'esperando' -> 'jugando' -> 'terminado'
        self.creado_en = datetime.now()
        self.turno_actual = 0 # (No usado directamente aquí, se maneja en JuegoOcaWeb)
        self.log_eventos = [] # Log para la sala de espera
        self.turn_timer = None

    def agregar_jugador(self, sid, nombre):
        if len(self.jugadores) < 4 and sid not in self.jugadores:
            self.jugadores[sid] = {
                'nombre': nombre,
                'sid': sid,
                'conectado': True # Marcar como conectado al unirse
            }
            self.log_eventos.append(f"{nombre} se unió al juego")
            return True
        return False

    def remover_jugador(self, sid):
        if sid in self.jugadores:
            nombre = self.jugadores[sid]['nombre']
            del self.jugadores[sid]
            self.log_eventos.append(f"{nombre} salió del juego")
            return True
        return False

    def puede_iniciar(self):
        # Necesita al menos 2 jugadores y estar en estado 'esperando'
        return len(self.jugadores) >= 2 and self.estado == 'esperando'

    def iniciar_juego(self):
        if self.puede_iniciar():
            nombres_jugadores = [datos['nombre'] for datos in self.jugadores.values()]
            self.juego = JuegoOcaWeb(nombres_jugadores) # Crear instancia del juego
            self.estado = 'jugando'
            self.log_eventos.append("¡El juego ha comenzado!")
            return True
        return False

    # ===================================================================
    # --- 2. RUTAS HTTP (Flask @app.route) ---
    # ===================================================================

@app.route('/')
def index():
    # Ruta principal que sirve el archivo HTML del juego
    user_data = None
    
    if current_user.is_authenticated:
        try:
            user = current_user 
            user_data = {
                'username': user.username,
                'level': user.level,
                'xp': user.xp
            }
            
            session['user_id'] = user.id
            session['username'] = user.username
            session['level'] = user.level
            session['xp'] = user.xp

            _procesar_login_diario(user)

        except Exception as e:
            print(f"Error al cargar current_user autenticado: {e}")
            user_data = None
            session.clear() 

    # Convertir user_data a JSON para inyectar en el template
    user_data_json = json.dumps(user_data) 
    
    return render_template(
        'index.html', 
        game_name="VoltRace",
        user_data_json=user_data_json
    )

# --- Rutas de Autenticación ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not email or not username or not password:
        return jsonify({"success": False, "message": "Faltan campos."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "El email ya está en uso."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "El nombre de usuario ya está en uso."}), 400

    new_user = User(email=email, username=username)
    new_user.set_password(password) 

    try:
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user, remember=True)
        
        # Guardar todo en la sesión
        session['username'] = new_user.username
        session['level'] = new_user.level
        session['xp'] = new_user.xp
        
        # Devolver el perfil completo para saltar fetchAndUpdateUserProfile
        user_data = {
            'username': new_user.username,
            'level': new_user.level,
            'xp': new_user.xp
        }
        return jsonify({"success": True, "user_data": user_data})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en registro: {e}")
        return jsonify({"success": False, "message": "Error en el servidor al crear usuario."}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and request.method == 'GET':
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.get_json(silent=True)
        
        if data:
            email = data.get('email', '').strip()
            password = data.get('password', '')
            user = User.query.filter_by(email=email).first() 

            if not user or not user.check_password(password):
                return jsonify({"success": False, "message": "Email o contraseña incorrectos."}), 401
            
            login_user(user, remember=True)
            
            # Guardar todo en la sesión
            session['username'] = user.username
            session['level'] = user.level
            session['xp'] = user.xp
            
            # Comprobar si es un nuevo día de login 
            _procesar_login_diario(user)
            
            # Devolver el perfil completo
            user_data = {
                'username': user.username,
                'level': user.level,
                'xp': user.xp
            }
            return jsonify({"success": True, "user_data": user_data})

        else:
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user, remember=True)
                session['username'] = user.username
                session['level'] = user.level
                session['xp'] = user.xp
                
                _procesar_login_diario(user)
                
                flash('¡Inicio de sesión exitoso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Inicio de sesión fallido. Verificá tu email y contraseña.', 'danger')
                return render_template('index.html') 

    return render_template('index.html', user_data_json=json.dumps(None))

@app.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            if send_reset_email(user):
                flash('Se ha enviado un email con instrucciones para restablecer tu contraseña.', 'info')
            else:
                flash('Error al enviar el email. Por favor, intentá de nuevo más tarde.', 'danger')
            # Si el usuario existe, SIEMPRE redirigir a /login
            return redirect(url_for('login')) 
        else:
            # Si el usuario NO existe, flashear el error y redirigir DE VUELTA a la misma página
            print(f"--- DEBUG: Intento de reseteo para email NO ENCONTRADO: {email} ---")
            flash('No existe una cuenta asociada a ese email.', 'warning')
            return redirect(url_for('forgot_password')) 

    # Esto ahora solo se ejecuta en el GET 
    return render_template('forgot_password.html')


@app.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user = User.verify_reset_token(token)
    if user is None:
        flash('El token es inválido o ha expirado.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('reset_password.html', token=token)

        user.set_password(password) # Usamos tu método existente
        db.session.commit()
        flash('Tu contraseña ha sido actualizada. Ya podés iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token) 

@app.route('/logout', methods=['POST'])
@login_required # Requiere que el usuario esté logueado
def logout():
    session.clear()
    logout_user() # Cierra la sesión
    return jsonify({'success': True, 'message': 'Sesión cerrada'})

# --- Rutas de Perfil, Ranking y Logros ---
@app.route('/profile/<username>')
def profile(username):
    # Buscar el usuario en la base de datos
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    # Crear el diccionario de estadísticas del usuario
    user_stats = {
        'username': user.username,
        'email': user.email, # Considera si realmente quieres exponer el email
        'level': user.level,
        'xp': user.xp,
        'games_played': user.games_played,
        'games_won': user.games_won
        # Añade más campos si los tienes en el modelo User
    }

    try:
        # Obtener el progreso de logros del usuario
        achievement_progress = achievement_system.get_user_achievement_progress(username)
    except Exception as e:
        print(f"ERROR al calcular progreso de logros para {username}: {e}")
        achievement_progress = {'error': 'No se pudo calcular el progreso de logros'}

    return jsonify({
        'stats': user_stats,
        'achievements': achievement_progress if achievement_progress else {}
    })

@app.route('/leaderboard')
def leaderboard():
    try:
        # Obtener los top 50 jugadores ordenados por nivel y luego XP
        top_jugadores = User.query.order_by(User.level.desc(), User.xp.desc()).limit(50).all()

        # Formatear los datos para el cliente
        ranking_data = [
            {
                "username": j.username,
                "level": j.level,
                "xp": j.xp,
                "games_played": j.games_played,
                "games_won": j.games_won,
            } for j in top_jugadores
        ]
        print(f"DEBUG /leaderboard: {ranking_data}") # Útil para depurar
        return jsonify(ranking_data)
    except Exception as e:
        print(f"Error al obtener leaderboard: {e}")
        return jsonify([]) # Devolver lista vacía en caso de error

@app.route('/achievements')
def all_achievements():
    # Devuelve la configuración de todos los logros (nombre, descripción, icono, etc.)
    achievements = achievement_system.get_all_achievements()
    return jsonify(achievements)

# --- Rutas del Sistema Social ---
@app.route('/social/search/<query>/<current_user>')
def search_users(query, current_user):
    # Busca usuarios por nombre para agregar como amigos
    results = social_system.search_users(query, current_user)
    return jsonify(results)

@app.route('/social/amigos/<username>')
def get_friends(username):
    # Obtiene la lista de amigos, solicitudes pendientes (recibidas/enviadas) y estado online
    data = social_system.get_friends_list(username)
    return jsonify(data)

@app.route('/social/solicitud/send/<sender_username>/<target_username>', methods=['POST'])
def send_friend_request(sender_username, target_username):
    print(f"\n--- RUTA: send_friend_request --- De: {sender_username}, Para: {target_username}")
    result = social_system.send_friend_request(sender_username, target_username)
    print(f"Resultado de social_system.send_friend_request: {result}")

    # Notificar al objetivo si está conectado (vía SocketIO)
    if result['success']:
        print(f"Buscando SID para notificar a: {target_username}")
        presence_info = social_system.presence_data.get(target_username, {})
        print(f"Datos de presencia encontrados para {target_username}: {presence_info}")
        target_sid = presence_info.get('extra_data', {}).get('sid')
        print(f"SID encontrado: {target_sid}")

        if target_sid:
            try:
                print(f"Intentando emitir 'new_friend_request' a SID: {target_sid}")
                socketio.emit('new_friend_request', {'from_user': sender_username}, room=target_sid)
                print("--- Emisión completada ---")
            except Exception as e:
                print(f"!!! ERROR al emitir notificación: {e}")
        else:
            print(f"--- ADVERTENCIA: No se encontró SID activo para {target_username}. No se envió notificación en tiempo real. ---")

    return jsonify(result)

@app.route('/social/solicitud/accept/<username>/<friend_username>', methods=['POST'])
def accept_friend_request(username, friend_username):
    result = social_system.accept_friend_request(username, friend_username)

    if result['success']:
        # Notificar al sistema de logros para AMBOS usuarios
        unlocked_user = achievement_system.check_achievement(username, 'friend_added')
        if unlocked_user:
            user_sid = social_system.presence_data.get(username, {}).get('extra_data', {}).get('sid')
            if user_sid:
                socketio.emit('achievements_unlocked', {
                    'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_user]
                }, to=user_sid)

        unlocked_friend = achievement_system.check_achievement(friend_username, 'friend_added')
        sid_sender = social_system.presence_data.get(friend_username, {}).get('extra_data', {}).get('sid')
        if unlocked_friend and sid_sender:
                socketio.emit('achievements_unlocked', {
                    'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_friend]
                }, to=sid_sender)

        # Notificar al emisor (friend_username) de que su solicitud fue aceptada (vía SocketIO)
        if sid_sender:
            socketio.emit('friend_status_update', {'friend': username, 'status': 'friend', 'type': 'accepted'}, room=sid_sender)

    return jsonify(result)

@app.route('/social/solicitud/reject/<username>/<friend_username>', methods=['POST'])
def reject_friend_request(username, friend_username):
    result = social_system.reject_friend_request(username, friend_username)
    return jsonify(result)

@app.route('/social/amigos/remove/<username>/<friend_to_remove>', methods=['POST'])
def remove_friend(username, friend_to_remove):
    result = social_system.remove_friend(username, friend_to_remove)
    # Podrías notificar al amigo eliminado si está online
    return jsonify(result)

# --- Rutas de Mensajería y Chat Privado ---
@app.route('/social/messages/<user1>/<user2>')
def get_conversation(user1, user2):
    # Obtiene el historial de mensajes entre dos usuarios
    messages = social_system.get_conversation(user1, user2)
    # Marca los mensajes como leídos (asume que user1 es quien está viendo)
    social_system.mark_messages_as_read(user1, user2)
    return jsonify(messages)

@app.route('/social/conversations/recent/<username>')
def get_recent_conversations(username):
    # Obtiene una lista de las conversaciones recientes del usuario
    conversations = social_system.get_recent_conversations(username)
    return jsonify(conversations)

# --- Rutas de Invitaciones a Salas (Sistema Social) ---
@app.route('/social/invitations/get/<username>')
def get_pending_invitations_route(username):
    # Obtiene las invitaciones a sala pendientes para un usuario
    invitations = social_system.get_pending_invitations(username)
    return jsonify(invitations)

@app.route('/social/invitations/respond/<username>/<invitation_id>/<response>', methods=['POST'])
def respond_to_invitation_route(username, invitation_id, response):
    # Permite al usuario aceptar ('accept') o rechazar ('reject') una invitación
    result = social_system.respond_to_invitation(username, invitation_id, response)
    # Aquí podrías notificar al remitente de la invitación sobre la respuesta
    return jsonify(result)

@app.route('/api/get_all_abilities')
def get_all_abilities():
    try:
        # crear_habilidades() devuelve un dict de listas de objetos Habilidad
        habilidades_dict = crear_habilidades()
        habilidades_json_ready = {}
        
        # Convertir los objetos Habilidad en diccionarios para que JSON pueda leerlos
        for categoria, lista_habilidades in habilidades_dict.items():
            habilidades_json_ready[categoria] = []
            for hab in lista_habilidades:
                habilidades_json_ready[categoria].append({
                    "nombre": hab.nombre,
                    "tipo": hab.tipo,
                    "descripcion": hab.descripcion,
                    "simbolo": hab.simbolo,
                    "cooldown_base": hab.cooldown_base
                })
        return jsonify(habilidades_json_ready)
    except Exception as e:
        print(f"!!! ERROR en /api/get_all_abilities: {e}")
        return jsonify({"error": "No se pudieron cargar las habilidades"}), 500

@app.route('/api/get_all_perks')
def get_all_perks():
    try:
        # PERKS_CONFIG ya está en un formato de diccionario listo para JSON
        return jsonify(PERKS_CONFIG)
    except Exception as e:
        print(f"!!! ERROR en /api/get_all_perks: {e}")
        return jsonify({"error": "No se pudieron cargar los perks"}), 500
    
# ===================================================================
# --- 3. HANDLERS DE SOCKET.IO (Conexión y Lobby) ---
# ===================================================================

@socketio.on('connect')
def on_connect():
    # Se ejecuta cuando un cliente establece una conexión WebSocket
    print(f"Cliente conectado: {request.sid}")
    emit('conectado', {'mensaje': 'Conexión exitosa'}) # Enviar confirmación al cliente

@socketio.on('authenticate')
def authenticate(data):
    # Asocia un username (obtenido tras login HTTP) al SID de SocketIO
    username = data.get('username')
    if username:
        sessions_activas[request.sid] = {'username': username}
        emit('authenticated', {'username': username}) # Confirmar autenticación al cliente
        # Actualizar presencia en el sistema social a 'online'
        social_system.update_user_presence(username, 'online', {'sid': request.sid})
        print(f"--- SOCKET AUTHENTICATED --- User: {username}, SID: {request.sid}")

        try:
            friends_list = social_system.get_friends_list_server(username)
            for friend_username in friends_list:
                friend_sid = social_system.presence_data.get(friend_username, {}).get('extra_data', {}).get('sid')
                if friend_sid:
                    socketio.emit('friend_status_update', {
                        'username': username, # Quién cambió
                        'status': 'online'      # Cuál es su nuevo estado
                    }, room=friend_sid)
        except Exception as e:
            print(f"!!! ERROR al notificar conexión a amigos: {e}")

@socketio.on('disconnect')
def on_disconnect():
    # Se ejecuta cuando un cliente se desconecta
    print(f"Cliente desconectado: {request.sid}")

    # Obtener username y limpiar de sesiones activas
    sesion_info = sessions_activas.pop(request.sid, {})
    username_desconectado = sesion_info.get('username')

    if not username_desconectado:
        print("Desconexión de un SID no autenticado.")
        return

    # Actualizar presencia social a 'offline'
    social_system.update_user_presence(username_desconectado, 'offline')
    
    try:
        friends_list = social_system.get_friends_list_server(username_desconectado)
        for friend_username in friends_list:
            friend_sid = social_system.presence_data.get(friend_username, {}).get('extra_data', {}).get('sid')
            if friend_sid:
                socketio.emit('friend_status_update', {
                    'username': username_desconectado, # Quién cambió
                    'status': 'offline'               # Cuál es su nuevo estado
                }, room=friend_sid)
    except Exception as e:
        print(f"!!! ERROR al notificar desconexión a amigos: {e}")

    # Buscar en qué sala estaba el jugador
    id_sala_afectada = None
    sala_afectada = None
    for id_sala, sala in salas_activas.items():
        if request.sid in sala.jugadores:
            id_sala_afectada = id_sala
            sala_afectada = sala
            break

    # Si estaba en una sala, finalizar la desconexión inmediatamente
    if sala_afectada:
        print(f"--- DESCONEXIÓN INMEDIATA --- Jugador: {username_desconectado} en Sala: {id_sala_afectada}.")
        _finalizar_desconexion(request.sid, id_sala_afectada, username_desconectado)
    else:
        print(f"Jugador {username_desconectado} desconectado (no estaba en una sala).")

@socketio.on('crear_sala')
def crear_sala(data):
    # Maneja la creación de una nueva sala de juego
    if request.sid not in sessions_activas:
        emit('error', {'mensaje': 'Debes iniciar sesión para crear una sala.'})
        return

    username = sessions_activas[request.sid]['username']
    id_sala = str(uuid.uuid4())[:8] # Generar ID corto único
    print(f"--- SALA CREADA --- ID: {id_sala} por: {username}")
    salas_activas[id_sala] = SalaJuego(id_sala) # Crear instancia de la sala

    join_room(id_sala) # Unir al creador a la room de SocketIO

    if salas_activas[id_sala].agregar_jugador(request.sid, username):
        
        # Enviar respuesta al cliente INMEDIATAMENTE
        emit('sala_creada', {
            'id_sala': id_sala,
            'mensaje': f'Sala {id_sala} creada exitosamente'
        })

        # Iniciar hilo para el trabajo de DB 
        threading.Thread(
            target=_procesar_creacion_sala_db_async,
            args=(
                current_app._get_current_object(),
                request.sid,
                username
            )
        ).start()
        # Actualizar presencia a 'in_lobby'
        social_system.update_user_presence(username, 'in_lobby', {'room_id': id_sala, 'sid': request.sid})
    
    else:
        emit('error', {'mensaje': 'Error al agregar jugador a la sala recién creada.'})
        if id_sala in salas_activas: del salas_activas[id_sala] # Limpiar si falló

@socketio.on('unirse_sala')
def unirse_sala(data):
    # Maneja cuando un jugador intenta unirse a una sala existente
    id_sala_original = data['id_sala']
    id_sala = id_sala_original.lower() # Normalizar a minúsculas

    if request.sid not in sessions_activas:
        emit('error', {'mensaje': 'Debes iniciar sesión para unirte a una sala.'})
        return

    username = sessions_activas[request.sid]['username']

    if id_sala not in salas_activas:
        emit('error', {'mensaje': f'La sala "{id_sala_original}" no existe.'})
        return

    sala = salas_activas[id_sala]

    # Validar estado de la sala y si ya está llena
    if sala.estado != 'esperando':
        emit('error', {'mensaje': 'No puedes unirte, la partida ya comenzó.'})
        return
    if len(sala.jugadores) >= 4:
        emit('error', {'mensaje': 'La sala está llena (máximo 4 jugadores).'})
        return

    # Verificar si el usuario ya está en la sala (quizás con otro SID, improbable pero posible)
    for sid_jugador, datos_jugador in sala.jugadores.items():
        if datos_jugador['nombre'] == username:
            print(f"DEBUG: {username} intentó unirse a la sala {id_sala} pero ya estaba dentro.")
            # Podrías simplemente reenviar el estado actual o un mensaje de éxito
            emit('unido_exitoso', {'id_sala': id_sala, 'mensaje': 'Ya estabas en esta sala.'})
            return

    # Intentar agregar al jugador
    if sala.agregar_jugador(request.sid, username):
        join_room(id_sala) # Unir a la room de SocketIO

        # Actualizar presencia a 'in_lobby'
        social_system.update_user_presence(username, 'in_lobby', {'room_id': id_sala, 'sid': request.sid})

        # Enviar confirmación al jugador que se unió
        emit('unido_exitoso', {
            'id_sala': id_sala,
            'mensaje': f'Te uniste a la sala {id_sala}'
        })

        # Notificar a TODOS en la sala (incluido el nuevo) sobre el estado actualizado
        socketio.emit('jugador_unido', {
            'jugador_nombre': username, # Quién se unió
            'jugadores': len(sala.jugadores),
            'lista_jugadores': [datos['nombre'] for datos in sala.jugadores.values()],
            'puede_iniciar': sala.puede_iniciar(),
            'log_eventos': sala.log_eventos[-10:] # Últimos eventos
        }, room=id_sala)
    else:
        # Esto podría pasar si justo en ese momento alguien más llenó la sala
        emit('error', {'mensaje': 'Error al unirse a la sala (posiblemente llena).'})

@socketio.on('salir_sala')
def salir_sala(data):
    # Maneja cuando un jugador decide salir de la sala de espera
    id_sala = data.get('id_sala')
    sid = request.sid

    if id_sala in salas_activas and sid in salas_activas[id_sala].jugadores:
        sala = salas_activas[id_sala]
        nombre_jugador = sala.jugadores[sid]['nombre']

        # Remover al jugador de la estructura de la sala
        sala.remover_jugador(sid)
        leave_room(id_sala) # Sacar el socket de la room de SocketIO

        # Notificar al resto de la sala que alguien salió
        socketio.emit('jugador_desconectado', {
            'jugador_nombre': nombre_jugador,
            'jugadores': len(sala.jugadores),
            'lista_jugadores': [datos['nombre'] for datos in sala.jugadores.values()],
            'puede_iniciar': sala.puede_iniciar(),
            'mensaje_desconexion': f"🔌 {nombre_jugador} salió de la sala." # Mensaje específico para 'jugador_desconectado'
        }, room=id_sala) # Enviar solo a los que quedan

        # Actualizar presencia del jugador que salió a 'online'
        if sid in sessions_activas:
            username = sessions_activas[sid]['username']
            social_system.update_user_presence(username, 'online', {'sid': sid})

        # Confirmar al jugador que salió
        emit('sala_abandonada', {'success': True, 'message': 'Has salido de la sala.'})
        print(f"Jugador {nombre_jugador} (Socket: {sid}) salió voluntariamente de la sala {id_sala}")

        # Si la sala queda vacía después de que alguien sale, eliminarla
        if len(sala.jugadores) == 0:
                print(f"Sala {id_sala} vacía tras salida voluntaria. Eliminando...")
                if id_sala in salas_activas:
                    del salas_activas[id_sala]
    else:
        # Si la sala no existe o el jugador no estaba, igual confirmar para desbloquear UI
        emit('sala_abandonada', {'success': False, 'message': 'No estabas en esa sala o ya no existe.'})

@socketio.on('obtener_estado_sala')
def obtener_estado_sala(data):
    # Permite a un cliente pedir el estado actual de una sala 
    id_sala_data = data.get('id_sala')
    if isinstance(id_sala_data, dict) and 'value' in id_sala_data:
        id_sala = id_sala_data['value']
    else:
        id_sala = id_sala_data 

    print(f"\n--- RECIBIDO EVENTO: lanzar_dado --- Sala: {id_sala}, SID: {request.sid}")

    if id_sala in salas_activas:
        sala = salas_activas[id_sala]
        emit('estado_sala', {
            'jugadores': len(sala.jugadores),
            'lista_jugadores': [datos['nombre'] for datos in sala.jugadores.values()],
            'estado': sala.estado,
            'puede_iniciar': sala.puede_iniciar(),
            'log_eventos': sala.log_eventos[-10:] # Enviar últimos logs
        })
    else:
        # Si la sala no existe (quizás se eliminó), informar al cliente
        emit('sala_abandonada', {'success': False, 'message': 'La sala a la que intentas acceder ya no existe.'})
        # O podrías usar emit('error', ...)

# ===================================================================
# --- 4. HANDLERS DE SOCKET.IO (Juego Activo) ---
# ===================================================================

@socketio.on('iniciar_juego')
def iniciar_juego_manual(data):
    # Handler para el botón "Iniciar Juego" en la sala de espera
    id_sala = data['id_sala']
    print(f"\n--- RECIBIDO EVENTO: iniciar_juego (manual) --- Sala: {id_sala}, SID: {request.sid}")
    # Verificar si el que lo pide es el creador o si tiene permisos (podrías añadir lógica de permisos)
    if id_sala in salas_activas:
        print(f"Llamando a iniciar_juego_sala para {id_sala}...")
        # Llama a la función interna que realmente inicia el juego
        iniciar_juego_sala(id_sala)
    else:
        print(f"ERROR: Sala {id_sala} no encontrada al intentar iniciar juego.")
        emit('error', {'mensaje': 'La sala ya no existe.'})

@socketio.on('lanzar_dado')
def lanzar_dado(data):
    # Maneja la acción de lanzar el dado
    try:
        id_sala = data['id_sala']
        print(f"\n--- PASO 1: RECIBIDO 'lanzar_dado' --- Sala: {id_sala}, SID: {request.sid}")
        
        # Si el jugador actúa, cancelar el timer de inactividad
        _cancelar_temporizador_turno(id_sala)
        
        if id_sala not in salas_activas:
            emit('error', {'mensaje': 'Sala no encontrada'})
            return

        sala = salas_activas[id_sala]
        if sala.estado != 'jugando' or not sala.juego:
            emit('error', {'mensaje': 'El juego no está activo'})
            return

        jugador_actual_obj = sala.juego.obtener_jugador_actual()
        nombre_jugador_actual = jugador_actual_obj.get_nombre() if jugador_actual_obj else None
        nombre_jugador_emitente = sala.jugadores.get(request.sid, {}).get('nombre', 'DESCONOCIDO')

        if nombre_jugador_actual != nombre_jugador_emitente:
            print("--- ACCIÓN RECHAZADA: No es su turno (lanzar dado) ---")
            emit('error', {'mensaje': 'No es tu turno'})
            return

        # Ejecutar el movimiento
        resultado = sala.juego.paso_1_lanzar_y_mover(nombre_jugador_emitente)

        try:
            seises_consecutivos = resultado.get('consecutive_sixes', 0)
            if seises_consecutivos >= 3:
                print(f"--- LOGRO DETECTADO: 'lucky_seven' para {nombre_jugador_emitente} ---")
                unlocked_list = achievement_system.check_achievement(
                    nombre_jugador_emitente,
                    'dice_rolled',
                    {'consecutive_sixes': seises_consecutivos}
                )
                if unlocked_list:
                    socketio.emit('achievements_unlocked', {
                        'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_list]
                    }, to=request.sid) # Notificar solo al jugador
        except Exception as e:
            print(f"!!! ERROR al procesar logro 'lucky_seven': {e}")
            traceback.print_exc()

        if resultado.get('pausado'):
            print(f"--- TURNO PAUSADO --- Sala: {id_sala}. Enviando estado completo.")
            colores_map = getattr(sala, 'colores_map', {})
            socketio.emit('paso_2_resultado_casilla', { 
                'estado_juego': {
                    'jugadores': sala.juego.obtener_estado_jugadores(),
                    'tablero': sala.juego.obtener_estado_tablero(),
                    'turno_actual': sala.juego.obtener_turno_actual(),
                    'ronda': sala.juego.ronda,
                    'estado': sala.estado,
                    'colores_jugadores': colores_map,
                    'evento_global_activo': sala.juego.evento_global_activo
                },
                'eventos': resultado.get('eventos', [])
            }, room=id_sala)
            
            nuevo_jugador_turno = sala.juego.obtener_turno_actual()
            if nuevo_jugador_turno:
                _iniciar_temporizador_turno(id_sala, nuevo_jugador_turno)
            return

        # Emitir el resultado del movimiento 
        socketio.emit('paso_1_resultado_movimiento', {
            'jugador': nombre_jugador_emitente,
            'resultado': resultado,
            'habilidad_usada': None # Flag para el dado fantasma
        }, room=id_sala)

    except Exception as e:
        print(f"!!! ERROR GRAVE en 'lanzar_dado' (PASO 1): {e}")
        traceback.print_exc()
        emit('error', {'mensaje': f'Error fatal del servidor (Paso 1): {e}'})

@socketio.on('paso_2_terminar_movimiento')
def terminar_movimiento(data):
    # Maneja la señal del cliente de que la animación de movimiento terminó 
    try:
        id_sala = data['id_sala']
        print(f"\n--- PASO 2: RECIBIDO 'terminar_movimiento' --- Sala: {id_sala}, SID: {request.sid}")
        if id_sala not in salas_activas:
            emit('error', {'mensaje': 'Sala no encontrada (Paso 2)'})
            return
            
        sala = salas_activas[id_sala]
        if sala.estado != 'jugando' or not sala.juego:
            emit('error', {'mensaje': 'El juego no está activo (Paso 2)'})
            return

        nombre_jugador_que_termino = data.get('jugador_que_termino')
        jugador_actual_obj = sala.juego.obtener_jugador_actual()
        nombre_jugador_a_procesar = None
        if jugador_actual_obj:
            nombre_jugador_a_procesar = jugador_actual_obj.get_nombre()
        elif nombre_jugador_que_termino:
            nombre_jugador_a_procesar = nombre_jugador_que_termino
        
        if not nombre_jugador_a_procesar:
            print("--- ERROR PASO 2: No se pudo determinar el jugador (ni por servidor ni por cliente).")
            emit('error', {'mensaje': 'Error interno: Jugador no encontrado (Paso 2)'})
            return
            
        print(f"Procesando casilla para: {nombre_jugador_a_procesar}")
        
        # Esta función ahora solo avanza el turno si fue un dado
        resultado = sala.juego.paso_2_procesar_casilla_y_avanzar(nombre_jugador_a_procesar)
        
        try:
            eventos_del_paso_2 = resultado.get('eventos', [])
            eventos_procesados_logros = set() # Para no duplicar (ej. 'inmortal')

            for evento_str in eventos_del_paso_2:
                if not isinstance(evento_str, str):
                    continue

                nombre_salvado = None
                evento_logro = None

                # Comprobar 'Inmortal'
                if 'inmortal' not in eventos_procesados_logros and evento_str.startswith("❤️‍🩹 ¡Último Aliento salvó a"):
                    partes = evento_str.split(' ')
                    if len(partes) >= 6:
                        nombre_salvado = partes[5]
                        evento_logro = 'inmortal'
                        eventos_procesados_logros.add('inmortal') # Marcar como procesado

                # Comprobar 'Muralla Humana'
                # El evento es "  Nombre: 🛡️ protegido"
                elif 'muralla_humana' not in eventos_procesados_logros and evento_str.strip().endswith(": 🛡️ protegido"):
                    partes = evento_str.strip().split(':')
                    if len(partes) >= 2:
                        nombre_salvado = partes[0].strip() # Obtener el nombre
                        evento_logro = 'muralla_humana'
                        eventos_procesados_logros.add('muralla_humana') # Marcar
                
                # Si encontramos un evento de logro, procesarlo
                if nombre_salvado and evento_logro:
                    print(f"--- LOGRO DETECTADO: '{evento_logro}' para {nombre_salvado} ---")
                    
                    unlocked_list = achievement_system.check_achievement(
                        nombre_salvado, 
                        'game_event', 
                        {'event_name': evento_logro}
                    )
                    
                    if unlocked_list:
                        sid_salvado = None
                        for sid, data_jugador in sala.jugadores.items():
                            if data_jugador['nombre'] == nombre_salvado:
                                sid_salvado = sid
                                break
                        
                        if sid_salvado:
                            socketio.emit('achievements_unlocked', {
                                'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_list]
                            }, to=sid_salvado)
                    # No hacemos 'break' por si un evento activa ambos (improbable, pero seguro)

        except Exception as e:
            print(f"!!! ERROR al procesar logros de 'paso_2_terminar_movimiento': {e}")
            traceback.print_exc()
        
        if sala.juego.ha_terminado():
            print(f"--- JUEGO TERMINADO (PASO 2) --- Sala: {id_sala}")
            _cancelar_temporizador_turno(id_sala)
            sala.estado = 'terminado'

            # Obtener las estadísticas finales (esto es rápido, solo calcula)
            ganador_obj = sala.juego.determinar_ganador()
            ganador_nombre = ganador_obj.get_nombre() if ganador_obj else None
            stats_finales_dict = sala.juego.obtener_estadisticas_finales()

            # Emitir el modal de fin de juego INMEDIATAMENTE
            print("--- Emitiendo 'juego_terminado' al cliente AHORA.")
            socketio.emit('juego_terminado', {
                'ganador': stats_finales_dict.get('ganador'),
                'estadisticas_finales': stats_finales_dict.get('lista_final')
            }, room=id_sala)
            
            # Preparar los datos para el hilo (copiar datos)
            jugadores_items_copia = list(sala.jugadores.items())
            ronda_copia = sala.juego.ronda
            player_count_copia = len(sala.jugadores)
            juego_obj_copia = sala.juego # El objeto juego ya no se modificará

            # Iniciar el hilo para procesar DB (lento) en segundo plano
            print("--- Iniciando hilo para procesar estadísticas de DB en segundo plano...")
            stats_thread = threading.Thread(
                target=_procesar_estadisticas_fin_juego_async,
                args=(
                    current_app._get_current_object(), 
                    jugadores_items_copia,
                    ganador_nombre,
                    ronda_copia,
                    player_count_copia,
                    juego_obj_copia
                )
            )
            stats_thread.start()
            
            # Salir inmediatamente
            return

        # Si el juego NO ha terminado, enviar la actualización normal
        colores_map = getattr(sala, 'colores_map', {})
        socketio.emit('paso_2_resultado_casilla', {
            'estado_juego': {
                'jugadores': sala.juego.obtener_estado_jugadores(),
                'tablero': sala.juego.obtener_estado_tablero(),
                'turno_actual': sala.juego.obtener_turno_actual(),
                'ronda': sala.juego.ronda,
                'estado': sala.estado,
                'colores_jugadores': colores_map,
                'evento_global_activo': sala.juego.evento_global_activo
            },
            'eventos': resultado.get('eventos', [])
        }, room=id_sala)
        nuevo_jugador_turno = sala.juego.obtener_turno_actual()
        if nuevo_jugador_turno:
            _iniciar_temporizador_turno(id_sala, nuevo_jugador_turno)
    except Exception as e:
        print(f"!!! ERROR GRAVE en 'terminar_movimiento' (PASO 2): {e}")
        traceback.print_exc()
        emit('error', {'mensaje': f'Error fatal del servidor (Paso 2): {e}'})

@socketio.on('usar_habilidad')
def usar_habilidad(data):
    # Maneja la acción de usar una habilidad
    id_sala_data = data.get('id_sala')
    if isinstance(id_sala_data, dict) and 'value' in id_sala_data:
        id_sala = id_sala_data['value']
    else:
        id_sala = id_sala_data
    indice_habilidad = data['indice_habilidad']
    objetivo = data.get('objetivo')
    sid = request.sid # Guardamos el SID
    print(f"\n--- RECIBIDO EVENTO: usar_habilidad --- Sala: {id_sala}, SID: {sid}, Habilidad idx: {indice_habilidad}")
    _cancelar_temporizador_turno(id_sala)

    if id_sala not in salas_activas:
        emit('error', {'mensaje': 'Sala no encontrada'})
        return

    sala = salas_activas[id_sala]
    if not sala.juego or sala.estado != 'jugando':
        emit('error', {'mensaje': 'El juego no está activo.'})
        return

    # Verificar que es el turno del jugador
    nombre_jugador_emitente = sessions_activas.get(sid, {}).get('username') # Usar sessions_activas es más fiable
    jugador_actual_obj = sala.juego.obtener_jugador_actual()
    nombre_jugador_actual = jugador_actual_obj.get_nombre() if jugador_actual_obj else None
    print(f"Verificando turno (habilidad): Esperado='{nombre_jugador_actual}', Emitente='{nombre_jugador_emitente}'")

    if nombre_jugador_actual != nombre_jugador_emitente:
        print(f"--- ACCIÓN RECHAZADA: No es su turno (usar habilidad) ---")
        emit('error', {'mensaje': 'No es tu turno para usar habilidad.'})
        return

    # Ejecutar la lógica de la habilidad en JuegoOcaWeb
    print("--- TURNO VÁLIDO: Llamando a sala.juego.usar_habilidad_jugador ---")
    try:
        # 1. EJECUTAR LÓGICA DEL JUEGO (Esto es rápido)
        resultado = sala.juego.usar_habilidad_jugador(nombre_jugador_emitente, indice_habilidad, objetivo)
        
        # Revisar los eventos devueltos por la habilidad, INCLUSO SI FALLÓ
        try:
            eventos_de_habilidad = resultado.get('eventos', [])
            for evento_str in eventos_de_habilidad:
                if isinstance(evento_str, str) and evento_str.strip().endswith("protegido por Invisibilidad."):
                    partes = evento_str.strip().split(' ')
                    if len(partes) >= 2:
                        # Extraer el nombre del jugador (el primero)
                        nombre_protegido = partes[1] 
                        print(f"--- LOGRO DETECTADO: 'fantasma' para {nombre_protegido} ---")
                        
                        unlocked_list = achievement_system.check_achievement(
                            nombre_protegido, 
                            'game_event', 
                            {'event_name': 'fantasma'}
                        )
                        
                        if unlocked_list:
                            sid_protegido = None
                            for s, data_jugador in sala.jugadores.items():
                                if data_jugador['nombre'] == nombre_protegido:
                                    sid_protegido = s
                                    break
                            
                            if sid_protegido:
                                socketio.emit('achievements_unlocked', {
                                    'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_list]
                                }, to=sid_protegido)
                        break # Encontramos el evento
        except Exception as e:
            print(f"!!! ERROR al procesar logros de 'usar_habilidad': {e}")
            traceback.print_exc()

        if resultado['exito']:
            
            # 2. VERIFICAR SI ES HABILIDAD DE MOVIMIENTO O NO
            es_habilidad_movimiento = (resultado.get('es_movimiento') or 
                                       resultado.get('es_movimiento_doble') or 
                                       resultado.get('es_movimiento_otro') or 
                                       resultado.get('es_movimiento_multiple'))

            # --- CASO A: HABILIDAD DE MOVIMIENTO (Cohete, Caos, etc.) ---
            if es_habilidad_movimiento:
                
                # CASO 1: Movimiento Simple (Cohete, Rebote)
                if resultado.get('es_movimiento'):
                    print("--- Habilidad de Movimiento (Paso 1) detectada. Emitiendo 'paso_1_resultado_movimiento'.")
                    socketio.emit('paso_1_resultado_movimiento', {
                        'jugador': nombre_jugador_emitente,
                        'resultado': { **resultado['resultado_movimiento'], 'eventos': resultado.get('eventos', []) },
                        'habilidad_usada': resultado.get('habilidad')
                    }, room=id_sala)
                
                # CASO 2: Movimiento Doble (Intercambio Forzado)
                elif resultado.get('es_movimiento_doble'):
                    print("--- Habilidad de Movimiento Doble (Paso 1) detectada. Emitiendo 'paso_1' para ambos.")
                    socketio.emit('paso_1_resultado_movimiento', {
                        'jugador': nombre_jugador_emitente,
                        'resultado': { **resultado['resultado_movimiento_jugador'], 'eventos': resultado.get('eventos', []) },
                        'habilidad_usada': resultado.get('habilidad')
                    }, room=id_sala)
                    mov_obj = resultado['resultado_movimiento_objetivo']
                    socketio.emit('paso_1_resultado_movimiento', {
                        'jugador': mov_obj['jugador'],
                        'resultado': { **mov_obj, 'eventos': [] },
                        'habilidad_usada': None
                    }, room=id_sala)

                # CASO 3: Movimiento de Otro (Retroceso)
                elif resultado.get('es_movimiento_otro'):
                    print("--- Habilidad de Movimiento de Otro (Paso 1) detectada. Emitiendo 'paso_1'.")
                    mov_obj = resultado['resultado_movimiento']
                    socketio.emit('paso_1_resultado_movimiento', {
                        'jugador': mov_obj['jugador_movido'],
                        'resultado': { **mov_obj, 'eventos': resultado.get('eventos', []) },
                        'habilidad_usada': resultado.get('habilidad')
                    }, room=id_sala)

                # CASO 4: Movimiento Múltiple (Caos)
                elif resultado.get('es_movimiento_multiple'):
                    print("--- Habilidad de Movimiento Múltiple (Paso 1) detectada. Emitiendo 'paso_1' para todos.")
                    eventos_principales = resultado.get('eventos', [])
                    for i, mov in enumerate(resultado.get('movimientos', [])):
                        eventos_a_enviar = eventos_principales if i == 0 else []
                        socketio.emit('paso_1_resultado_movimiento', {
                            'jugador': mov['jugador'],
                            'resultado': { **mov, 'eventos': eventos_a_enviar },
                            'habilidad_usada': resultado.get('habilidad')
                        }, room=id_sala)

            # --- CASO B: HABILIDAD DE NO-MOVIMIENTO (Escudo, Bomba, etc.) ---
            else:
                print("--- Habilidad estándar (No-Mov) detectada. Procesando DB en hilo.")
                
                # 3. INICIAR HILO PARA DB (Pasando el 'resultado' como event_data)
                if sid in sessions_activas:
                    threading.Thread(
                        target=_procesar_habilidad_db_async,
                        args=(
                            current_app._get_current_object(),
                            sid,
                            nombre_jugador_emitente,
                            resultado # Pasamos el diccionario de resultado completo
                        )
                    ).start()
                
                # 4. ENVIAR RESPUESTA DEL JUEGO INMEDIATAMENTE 
                colores_map = getattr(sala, 'colores_map', {})
                celda_actualizada = resultado.get('celda_actualizada')

                if celda_actualizada:
                    # CASO B1: Habilidad que SÍ cambia el tablero 
                    print("--- (Habilidad No-Mov) Celda actualizada detectada. Enviando FULL state.")
                    estado_juego_full = {
                        'jugadores': sala.juego.obtener_estado_jugadores(),
                        'tablero': sala.juego.obtener_estado_tablero(), 
                        'turno_actual': sala.juego.obtener_turno_actual(), 
                        'ronda': sala.juego.ronda,
                        'estado': sala.estado,
                        'colores_jugadores': colores_map,
                        'evento_global_activo': sala.juego.evento_global_activo
                    }
                    socketio.emit('habilidad_usada_full', { 
                        'jugador': nombre_jugador_emitente, 
                        'habilidad': resultado['habilidad'], 
                        'resultado': resultado, 
                        'estado_juego': estado_juego_full 
                    }, room=id_sala)
                
                else:
                    # CASO B2: Habilidad que NO cambia el tablero (Escudo, Curar, Bomba, etc.)
                    print("--- (Habilidad No-Mov) Sin cambio de celda. Enviando PARTIAL state.")
                    estado_juego_parcial = {
                        'jugadores': sala.juego.obtener_estado_jugadores(),
                        'turno_actual': sala.juego.obtener_turno_actual(), 
                        'ronda': sala.juego.ronda,
                        'estado': sala.estado,
                        'colores_jugadores': colores_map,
                        'evento_global_activo': sala.juego.evento_global_activo
                    }
                    
                    if resultado.get('habilidad', {}).get('nombre') == 'Invisibilidad':
                        emit('habilidad_usada_privada', { 'jugador': nombre_jugador_emitente, 'habilidad': resultado['habilidad'], 'resultado': resultado, 'estado_juego_parcial': estado_juego_parcial }, to=sid)
                        socketio.emit('habilidad_usada_parcial', { 'jugador': nombre_jugador_emitente, 'habilidad': {'nombre': 'Habilidad usada', 'tipo': 'defensiva', 'simbolo': '❔'}, 'resultado': {'exito': True, 'eventos': [f"{nombre_jugador_emitente} usó una habilidad."]}, 'estado_juego_parcial': estado_juego_parcial }, room=id_sala, include_self=False)
                    else:
                        socketio.emit('habilidad_usada_parcial', { 
                            'jugador': nombre_jugador_emitente, 
                            'habilidad': resultado['habilidad'], 
                            'resultado': resultado, 
                            'estado_juego_parcial': estado_juego_parcial 
                        }, room=id_sala)

        else:
            # Si la habilidad falló, enviar solo el mensaje de error al emisor
            emit('error', {'mensaje': resultado['mensaje']})
    
    except Exception as e:
            print(f"!!! ERROR GRAVE en 'usar_habilidad': {e}")
            traceback.print_exc()
            emit('error', {'mensaje': f'Error fatal del servidor al usar habilidad: {e}'})

@socketio.on('comprar_perk')
def comprar_perk(data):
    # Maneja la solicitud de comprar un pack de perks
    id_sala_data = data.get('id_sala')
    if isinstance(id_sala_data, dict) and 'value' in id_sala_data:
        id_sala = id_sala_data['value']
    else:
        id_sala = id_sala_data
    tipo_pack = data.get('tipo_pack')
    sid = request.sid
    print(f"\n--- RECIBIDO EVENTO: comprar_perk --- SID: {sid}, Sala: {id_sala}, Pack: {tipo_pack}")

    if not id_sala or not tipo_pack:
        emit('error', {'mensaje': 'Datos incompletos para comprar perk.'})
        return

    if id_sala in salas_activas and sid in salas_activas[id_sala].jugadores:
        sala = salas_activas[id_sala]
        nombre_jugador = sala.jugadores[sid]['nombre']
        print(f"Jugador: {nombre_jugador}")

        # Verificar si es el turno del jugador y el juego está activo
        turno_actual_juego = sala.juego.obtener_turno_actual() if sala.juego else None
        es_turno_valido = (sala.juego and sala.estado == 'jugando' and turno_actual_juego == nombre_jugador)
        print(f"Verificando turno (comprar perk): Turno actual='{turno_actual_juego}', Jugador='{nombre_jugador}', Es válido? {es_turno_valido}")

        if es_turno_valido:
            print("Turno válido. Llamando a sala.juego.comprar_pack_perk...")
            try:
                # Llamar a la función en JuegoOcaWeb para obtener la oferta
                resultado_oferta = sala.juego.comprar_pack_perk(nombre_jugador, tipo_pack)
                print(f"Resultado de comprar_pack_perk: {resultado_oferta}")

                # Emitir la oferta (o el error) SOLO al jugador que compró
                print(f"Intentando emitir 'oferta_perk' a SID: {sid}...")
                emit('oferta_perk', resultado_oferta)
                print("--- Emisión de 'oferta_perk' completada ---")

            except Exception as e:
                print(f"!!! ERROR dentro de comprar_pack_perk o al emitir: {e}")
                traceback.print_exc()
                emit('error', {'mensaje': f'Error interno al procesar compra: {e}'})
        else:
            print("--- COMPRAR PERK ERROR: No es el turno del jugador o juego no activo ---")
            emit('error', {'mensaje': 'No es tu turno o el juego no está activo para comprar perks.'})
    else:
        print(f"--- COMPRAR PERK ERROR: Sala {id_sala} no encontrada o SID {sid} no está en la sala ---")
        emit('error', {'mensaje': 'Sala no encontrada o no estás en ella.'})

@socketio.on('seleccionar_perk')
def seleccionar_perk(data):
    id_sala_data = data.get('id_sala')
    if isinstance(id_sala_data, dict) and 'value' in id_sala_data:
        id_sala = id_sala_data['value']
    else:
        id_sala = id_sala_data # Debería ser un string

    perk_id = data.get('perk_id')
    coste_pack = data.get('coste') # Coste del pack original para verificación/devolución
    sid = request.sid
    print(f"\n--- RECIBIDO EVENTO: seleccionar_perk --- SID: {sid}, Sala: {id_sala}, Perk ID: {perk_id}")

    if not id_sala or not perk_id or coste_pack is None:
        emit('error', {'mensaje': 'Datos incompletos para seleccionar perk.'})
        return

    if id_sala in salas_activas and sid in salas_activas[id_sala].jugadores:
        sala = salas_activas[id_sala]
        nombre_jugador = sala.jugadores[sid]['nombre']

        # Verificar turno de nuevo
        if sala.juego and sala.estado == 'jugando' and sala.juego.obtener_turno_actual() == nombre_jugador:
            print("Turno válido. Llamando a sala.juego.activar_perk_seleccionado...")
            try:
                # Llamar a la función en JuegoOcaWeb para activar el perk seleccionado
                resultado_activacion = sala.juego.activar_perk_seleccionado(nombre_jugador, perk_id, coste_pack)
                print(f"Resultado de activar_perk_seleccionado: {resultado_activacion}")

                # Enviar confirmación (éxito o fallo) SOLO al jugador que seleccionó
                print(f"Intentando emitir 'perk_activado' a SID: {sid}...")
                emit('perk_activado', resultado_activacion)
                print("--- Emisión de 'perk_activado' completada ---")

                # Si la activación fue exitosa, enviar estado actualizado a TODOS en la sala
                if resultado_activacion.get('exito'):
                    colores_map = getattr(sala, 'colores_map', {})
                    estado_juego = {
                        'jugadores': sala.juego.obtener_estado_jugadores(), # Incluirá PM actualizados y perks activos
                        'tablero': sala.juego.obtener_estado_tablero(),
                        'turno_actual': sala.juego.obtener_turno_actual(), # Sigue siendo el mismo turno
                        'ronda': sala.juego.ronda,
                        'estado': sala.estado,
                        'colores_jugadores': colores_map,
                        'evento_global_activo': sala.juego.evento_global_activo
                    }
                    print(f"Activación exitosa. Emitiendo 'estado_juego_actualizado' a sala {id_sala}")
                    socketio.emit('estado_juego_actualizado', {
                            'estado_juego': estado_juego,
                            'eventos_recientes': sala.juego.eventos_turno[-5:] 
                        }, room=id_sala)

            except Exception as e:
                print(f"!!! ERROR dentro de activar_perk_seleccionado o al emitir: {e}")
                traceback.print_exc()
                emit('error', {'mensaje': f'Error interno al activar perk: {e}'})
        else:
            print("--- SELECCIONAR PERK ERROR: No es el turno del jugador o juego no activo ---")
            emit('error', {'mensaje': 'No es tu turno para seleccionar perks.'})
    else:
        print(f"--- SELECCIONAR PERK ERROR: Sala {id_sala} no encontrada o SID {sid} no está en la sala ---")
        emit('error', {'mensaje': 'Sala no encontrada o no estás en ella.'})

@socketio.on('cancelar_oferta_perk')
def cancelar_oferta_perk(data):
    id_sala = data.get('id_sala')
    sid = request.sid
    print(f"\n--- RECIBIDO EVENTO: cancelar_oferta_perk --- SID: {sid}, Sala: {id_sala}")
    
    if not id_sala or id_sala not in salas_activas or sid not in salas_activas[id_sala].jugadores:
        return # Fallo silencioso, no es crítico

    sala = salas_activas[id_sala]
    nombre_jugador = sala.jugadores[sid].get('nombre')

    if sala.juego and nombre_jugador:
        try:
            resultado = sala.juego._cancelar_oferta_perk(nombre_jugador)
            
            if resultado.get('exito'):
                print(f"--- Oferta de Perk cancelada para {nombre_jugador} ---")
                # Notificar al jugador de sus PM actualizados
                emit('perk_activado', { 
                    "exito": True, 
                    "mensaje": "Oferta de perk cancelada. PM devueltos.",
                    "pm_restantes": resultado.get('pm_restantes')
                }, to=sid)

                # Notificar a todos del estado actualizado (por los PM)
                colores_map = getattr(sala, 'colores_map', {})
                estado_juego_parcial = {
                    'jugadores': sala.juego.obtener_estado_jugadores(),
                    'turno_actual': sala.juego.obtener_turno_actual(), 
                    'ronda': sala.juego.ronda,
                    'estado': sala.estado,
                    'colores_jugadores': colores_map,
                    'evento_global_activo': sala.juego.evento_global_activo
                }
                socketio.emit('habilidad_usada_parcial', { 
                    'jugador': nombre_jugador, 
                    'habilidad': {'nombre': 'Canceló Perk', 'tipo': 'control', 'simbolo': '↩️'}, 
                    'resultado': {'eventos': [resultado.get('mensaje')]}, 
                    'estado_juego_parcial': estado_juego_parcial 
                }, room=id_sala)

        except Exception as e:
            print(f"!!! ERROR en 'cancelar_oferta_perk': {e}")
            traceback.print_exc()

@socketio.on('solicitar_precios_perks')
def solicitar_precios_perks(data):
    id_sala = data.get('id_sala')
    sid = request.sid
    print(f"\n--- RECIBIDO EVENTO: solicitar_precios_perks --- SID: {sid}, Sala: {id_sala}")

    if not id_sala or id_sala not in salas_activas:
        emit('error', {'mensaje': 'Sala no encontrada al pedir precios.'})
        return

    sala = salas_activas[id_sala]
    costes = {"basico": 4, "intermedio": 8, "avanzado": 12} # Precios base

    try:
        # Comprobar si el evento global está activo
        if sala.juego and sala.juego.evento_global_activo == "Mercado Negro":
            print(f"--- Evento 'Mercado Negro' ACTIVO. Enviando precios con descuento. ---")
            costes = {
                "basico": max(1, costes["basico"] // 2),
                "intermedio": max(1, costes["intermedio"] // 2),
                "avanzado": max(1, costes["avanzado"] // 2)
            }
        else:
             print(f"--- Evento 'Mercado Negro' INACTIVO. Enviando precios normales. ---")

        # Enviar los precios actualizados SOLO al jugador que preguntó
        emit('precios_perks_actualizados', costes, to=sid)

    except Exception as e:
        print(f"!!! ERROR al solicitar precios de perks: {e}")
        emit('error', {'mensaje': 'Error al obtener precios de perks.'})

# ===================================================================
# --- 5. HANDLERS DE SOCKET.IO (Chat y Social) ---
# ===================================================================

@socketio.on('enviar_mensaje')
def manejar_mensaje(data):
    # Maneja mensajes enviados al chat de la sala (lobby o juego)
    id_sala_data = data.get('id_sala')
    if isinstance(id_sala_data, dict) and 'value' in id_sala_data:
        id_sala = id_sala_data['value']
    else:
        id_sala = id_sala_data
    mensaje = data['mensaje']

    # Verificar que la sala exista y el jugador pertenezca a ella
    if id_sala in salas_activas and request.sid in salas_activas[id_sala].jugadores:
        sala = salas_activas[id_sala]
        nombre = sala.jugadores[request.sid]['nombre']

        # Actualizar estadísticas y verificar logros
        if request.sid in sessions_activas:
            username = sessions_activas[request.sid]['username']
            user_db = User.query.filter_by(username=username).first()
            if user_db:
                user_db.game_messages_sent = getattr(user_db, 'game_messages_sent', 0) + 1
                # No notificar level up por chat, pero sí calcularlo
                update_xp_and_level(user_db, 1) # Añade 1 XP
            
            # Incrementar el contador de la partida actual en JuegoOcaWeb
            if sala.juego:
                jugador_juego = sala.juego._encontrar_jugador(nombre)
                if jugador_juego:
                    jugador_juego.game_messages_sent_this_match = getattr(jugador_juego, 'game_messages_sent_this_match', 0) + 1

            unlocked_achievements = achievement_system.check_achievement(username, 'message_sent', {})
            if unlocked_achievements:
                socketio.emit('achievements_unlocked', {
                    'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_achievements]
                }, to=request.sid)

        # Emitir el mensaje a todos en la sala
        socketio.emit('nuevo_mensaje', {
            'jugador': nombre,
            'mensaje': mensaje,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }, room=id_sala)
    else:
        emit('error', {'mensaje': 'No se pudo enviar el mensaje (sala no encontrada o no perteneces).'})

@socketio.on('mark_chat_as_read')
def mark_chat_as_read(data):
    # Handler para cuando el cliente recibe un mensaje en una ventana ya abierta
    username = sessions_activas.get(request.sid, {}).get('username')
    sender_username = data.get('sender')
    
    if not username or not sender_username:
        return # No se puede procesar

    # Llama a la función existente en social_system
    print(f"--- CHAT: Marcando mensajes de {sender_username} para {username} como leídos... ---")
    social_system.mark_messages_as_read(username, sender_username)

@socketio.on('private_message')
def handle_private_message(data):
    # Maneja el envío de mensajes privados entre usuarios
    sender = sessions_activas.get(request.sid, {}).get('username')
    target = data.get('target')
    message = data.get('message')
    print(f"\n--- RECIBIDO EVENTO: private_message --- De: {sender}, Para: {target}")

    if not sender or not target or not message:
        print("--- PM ERROR: Faltan datos ---")
        emit('error', {'mensaje': 'Faltan datos para enviar mensaje privado.'})
        return

    # Llama al sistema social para guardar el mensaje y obtener datos
    result = social_system.send_private_message(sender, target, message)
    print(f"Resultado de social_system.send_private_message: {result}")

    if result['success']:
        # Actualizar stats y logros del remitente
        user_db = User.query.filter_by(username=sender).first()
        if user_db:
            user_db.private_messages_sent = getattr(user_db, 'private_messages_sent', 0) + 1 
            db.session.commit()
        unlocked = achievement_system.check_achievement(sender, 'private_message_sent')
        if unlocked:
            socketio.emit('achievements_unlocked', {
                'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked]
            }, to=request.sid)

        # Intentar notificar al destinatario si está conectado
        presence_info = social_system.presence_data.get(target, {})
        target_sid = presence_info.get('extra_data', {}).get('sid')
        print(f"Intentando notificar a {target} (SID: {target_sid})")
        if target_sid:
            try:
                socketio.emit('new_private_message', result['message_data'], room=target_sid)
                print("--- Emisión a destinatario de PM completada ---")
            except Exception as e:
                print(f"!!! ERROR al emitir PM a destinatario: {e}")
        else:
            print(f"--- ADVERTENCIA PM: Destinatario {target} no conectado. ---")

        # Enviar confirmación al remitente
        print(f"Enviando confirmación 'message_sent_confirm' a {sender} (SID: {request.sid})")
        emit('message_sent_confirm', result['message_data'])
    else:
        print(f"--- PM ERROR (social_system): {result['message']} ---")
        emit('error', {'mensaje': result['message']})

@socketio.on('invite_to_room')
def handle_invite_to_room(data):
    # Maneja el envío de invitaciones a sala a otros usuarios
    sender = sessions_activas.get(request.sid, {}).get('username')
    recipient = data.get('recipient')
    room_id = data.get('room_id')
    print(f"\n--- RECIBIDO EVENTO: invite_to_room --- De: {sender}, Para: {recipient}, Sala: {room_id}")

    if not sender or not recipient or not room_id:
        emit('error', {'mensaje': 'Datos de invitación incompletos.'})
        return

    # Llama al sistema social para validar y crear la invitación
    result = social_system.send_room_invitation(sender, recipient, room_id)
    print(f"Resultado de social_system.send_room_invitation: {result}")

    if result['success']:
        # Intentar notificar al destinatario si está conectado
        recipient_sid = social_system.presence_data.get(recipient, {}).get('extra_data', {}).get('sid')
        print(f"Intentando notificar invitación a {recipient} (SID: {recipient_sid})")
        if recipient_sid:
            try:
                socketio.emit('room_invite', result['invitation_data'], room=recipient_sid)
                print("--- Emisión de 'room_invite' completada ---")
            except Exception as e:
                print(f"!!! ERROR al emitir 'room_invite': {e}")
        else:
            print(f"--- INVITE WARNING: Destinatario {recipient} no conectado. ---")

        # Confirmar al remitente que la invitación fue enviada
        emit('invite_sent_confirm', {'to': recipient, 'room_id': room_id})
    else:
        print(f"--- INVITE FALLIDO (social_system): {result['message']} ---")
        emit('error', {'mensaje': result['message']})

@socketio.on('presence_heartbeat')
def handle_presence_heartbeat():
    # Recibe pings periódicos del cliente para mantener actualizado el 'last_seen'
    sid = request.sid
    if sid in sessions_activas:
        username = sessions_activas[sid]['username']
        current_status = social_system._get_user_status(username) # Obtener estado actual

        if current_status != 'offline':
            # Refrescar 'last_seen' llamando a update_user_presence
            presence_data = social_system.presence_data.get(username, {})
            extra_data = presence_data.get('extra_data', {'sid': sid})
            if extra_data.get('sid') != sid: extra_data['sid'] = sid # Corregir SID si es viejo
            social_system.update_user_presence(username, current_status, extra_data)
            # print(f"Heartbeat recibido de {username}, 'last_seen' actualizado.") # Descomentar para debug detallado

# ===================================================================
# --- 6. HANDLERS DE SOCKET.IO (Fin de Juego y Varios) ---
# ===================================================================

@socketio.on('solicitar_revancha')
def solicitar_revancha(data):
    # Maneja la solicitud de un jugador para jugar una revancha
    id_sala_original = data.get('value') if isinstance(data, dict) else data
    sid = request.sid

    if not id_sala_original or sid not in sessions_activas:
        emit('error', {'mensaje': 'Datos inválidos para solicitar revancha.'})
        return

    username = sessions_activas[sid]['username']
    print(f"--- SOLICITUD REVANCHA --- Usuario: {username}, Sala Original (procesada): {id_sala_original}")

    # Si es la primera solicitud para esta sala, inicializar la estructura
    if id_sala_original not in revanchas_pendientes:
        sala_original_obj = salas_activas.get(id_sala_original) # Obtener la sala original (puede ya no existir si tardaron mucho)
        if not sala_original_obj or not sala_original_obj.jugadores:
                emit('error', {'mensaje': 'Revancha expirada: La sala original ya no existe o está vacía.'})
                return

        # Guardar quiénes eran los participantes originales
        participantes_originales = list(sala_original_obj.jugadores.values())
        revanchas_pendientes[id_sala_original] = {
            'solicitudes': set(),
            'participantes': participantes_originales, # Lista de dicts {'nombre': ..., 'sid': ...}
            'timestamp': datetime.now(),
            'timer': None # El timer se iniciará después
        }

    # Añadir la solicitud del jugador actual
    info_revancha = revanchas_pendientes[id_sala_original]
    info_revancha['solicitudes'].add(username)
    print(f"Revancha Sala {id_sala_original}: {len(info_revancha['solicitudes'])} solicitudes de {len(info_revancha['participantes'])} participantes.")

    # Notificar a TODOS en la sala sobre el estado actualizado de la revancha
    try:
        lista_solicitudes = list(info_revancha['solicitudes'])
        # (Nombres de los participantes originales)
        lista_participantes = [p['nombre'] for p in info_revancha['participantes']] 
        
        socketio.emit('revancha_actualizada', {
            'lista_solicitudes': lista_solicitudes,
            'lista_participantes': lista_participantes
        }, room=id_sala_original) # Emitir a la sala de juego original
        print(f"Emitiendo 'revancha_actualizada' a sala {id_sala_original}")
    except Exception as e:
        print(f"!!! ERROR al emitir 'revancha_actualizada': {e}")

    # Iniciar timer si se alcanza el mínimo y aún no ha empezado
    if len(info_revancha['solicitudes']) >= MIN_JUGADORES_REVANCHA and info_revancha['timer'] is None:
        iniciar_timer_revancha(id_sala_original)

    # Si TODOS los participantes originales solicitan, iniciar revancha inmediatamente
    if len(info_revancha['solicitudes']) == len(info_revancha['participantes']):
            if info_revancha['timer']:
                info_revancha['timer'].cancel() # Cancelar timer si estaba corriendo
                print(f"Timer de revancha para sala {id_sala_original} cancelado (todos respondieron).")
            _crear_nueva_sala_revancha(id_sala_original) # Crear la nueva sala ahora

@socketio.on('cancelar_revancha')
def cancelar_revancha(data):
    # Permite a un jugador retirar su solicitud de revancha
    id_sala_original = data.get('id_sala')
    username = sessions_activas.get(request.sid, {}).get('username')

    if id_sala_original in revanchas_pendientes and username:
        if username in revanchas_pendientes[id_sala_original]['solicitudes']:
            revanchas_pendientes[id_sala_original]['solicitudes'].remove(username)
            print(f"Revancha Sala {id_sala_original}: Solicitud de {username} cancelada.")
            # Aquí podrías notificar a otros si lo deseas, pero usualmente no es necesario

@socketio.on('abandonar_revancha')
def abandonar_revancha(data):
    id_sala_original = data.get('id_sala_original')
    username = sessions_activas.get(request.sid, {}).get('username')

    if not id_sala_original or not username or id_sala_original not in revanchas_pendientes:
        return # No hay nada que hacer

    info_revancha = revanchas_pendientes[id_sala_original]
    
    # Removerlo de la lista de participantes
    participante_encontrado = None
    for p in info_revancha['participantes']:
        if p['nombre'] == username:
            participante_encontrado = p
            break
    
    if participante_encontrado:
        info_revancha['participantes'].remove(participante_encontrado)
        print(f"--- REVANCHA ABANDONADA ---: {username} salió de la cola de revancha de {id_sala_original}.")

        # Si él estaba en la lista de solicitudes, removerlo también
        if username in info_revancha['solicitudes']:
            info_revancha['solicitudes'].remove(username)
        
        # Si todos los que *quedan* han aceptado
        if len(info_revancha['solicitudes']) == len(info_revancha['participantes']) and len(info_revancha['solicitudes']) >= MIN_JUGADORES_REVANCHA:
            print(f"--- Revancha (por abandono) ---: Todos los restantes ({len(info_revancha['solicitudes'])}) aceptaron. Iniciando.")
            _crear_nueva_sala_revancha(id_sala_original)

        # Si ahora es imposible alcanzar el mínimo
        elif len(info_revancha['participantes']) < MIN_JUGADORES_REVANCHA:
            print(f"--- Revancha (por abandono) ---: Imposible alcanzar el mínimo. Cancelando.")
            # Notificar a los que SÍ se quedaron esperando
            for p_data in info_revancha['participantes']:
                p_sid_original = p_data.get('sid') # El SID original de la sala anterior
                if p_sid_original:
                     # Usamos el SID original porque el jugador está en el modal de fin de juego
                     socketio.emit('revancha_cancelada', {'mensaje': f'{username} abandonó. Revancha cancelada.'}, room=p_sid_original)
            
            # Limpiar
            if info_revancha.get('timer'): info_revancha['timer'].cancel()
            revanchas_pendientes.pop(id_sala_original, None)

        # Si todavía es posible pero no todos han aceptado 
        else:
            # Emitir la actualización para que el que se quedó vea que el otro se fue
            try:
                lista_solicitudes = list(info_revancha['solicitudes'])
                lista_participantes = [p['nombre'] for p in info_revancha['participantes']]
                
                # Emitir a la sala original (que es donde están los modales)
                socketio.emit('revancha_actualizada', {
                    'lista_solicitudes': lista_solicitudes,
                    'lista_participantes': lista_participantes
                }, room=id_sala_original)
            except Exception as e:
                print(f"!!! ERROR al emitir 'revancha_actualizada' (por abandono): {e}")
    
@socketio.on('pedir_top_5')
def manejar_pedir_top_5():
    # Handler para obtener el top 5 (parece específico para alguna UI, mantener por si acaso)
    try:
        top_jugadores = User.query.order_by(User.level.desc(), User.xp.desc()).limit(5).all()
        ranking_data = [
            {
                "username": j.username,
                "level": j.level,
                "xp": j.xp
                # No incluir stats de juego aquí si solo es para un display rápido
            } for j in top_jugadores
        ]
        emit('actualizar_top_5', ranking_data) # Enviar solo al que pidió
    except Exception as e:
        print(f"Error al obtener top 5: {e}")
        emit('actualizar_top_5', []) # Enviar lista vacía en caso de error

# ===================================================================
# --- 7. LÓGICA INTERNA DEL SERVIDOR (Funciones Helper) y EJECUCIÓN ---
# ===================================================================

def _finalizar_desconexion(sid_original, id_sala, username_desconectado):
    print(f"--- Finalizando desconexión de {username_desconectado} (SID: {sid_original}) de sala {id_sala}")

    # Si un jugador se desconecta, hay que sacarlo de la cola de revancha
    if id_sala in revanchas_pendientes:
        info_revancha = revanchas_pendientes[id_sala]
        
        participante_encontrado = None
        for p in info_revancha['participantes']:
            if p['nombre'] == username_desconectado:
                participante_encontrado = p
                break
        
        if participante_encontrado:
            info_revancha['participantes'].remove(participante_encontrado)
            print(f"--- REVANCHA (Desconexión) ---: {username_desconectado} salió de la cola de revancha de {id_sala}.")

            if username_desconectado in info_revancha['solicitudes']:
                info_revancha['solicitudes'].remove(username_desconectado)
            
            # Recalcular (misma lógica que 'abandonar_revancha')
            if len(info_revancha['solicitudes']) == len(info_revancha['participantes']) and len(info_revancha['solicitudes']) >= MIN_JUGADORES_REVANCHA:
                print(f"--- Revancha (por desconexión) ---: Todos los restantes ({len(info_revancha['solicitudes'])}) aceptaron. Iniciando.")
                _crear_nueva_sala_revancha(id_sala)
            elif len(info_revancha['participantes']) < MIN_JUGADORES_REVANCHA:
                print(f"--- Revancha (por desconexión) ---: Imposible alcanzar el mínimo. Cancelando.")
                for p_data in info_revancha['participantes']:
                    p_sid_original = p_data.get('sid')
                    if p_sid_original:
                         socketio.emit('revancha_cancelada', {'mensaje': f'{username_desconectado} se desconectó. Revancha cancelada.'}, room=p_sid_original)
                if info_revancha.get('timer'): info_revancha['timer'].cancel()
                revanchas_pendientes.pop(id_sala, None)
            else:
                # Notificar a los que quedan
                try:
                    lista_solicitudes = list(info_revancha['solicitudes'])
                    lista_participantes = [p['nombre'] for p in info_revancha['participantes']]
                    socketio.emit('revancha_actualizada', {
                        'lista_solicitudes': lista_solicitudes,
                        'lista_participantes': lista_participantes
                    }, room=id_sala)
                except Exception as e:
                    print(f"!!! ERROR al emitir 'revancha_actualizada' (por desconexión): {e}")

    sala = salas_activas.get(id_sala)
    if not sala:
        print(f"Desconexión final: Sala {id_sala} ya no existe.")
        return

    jugador_data = sala.jugadores.get(sid_original)

    if jugador_data and jugador_data.get('nombre') == username_desconectado:
        print(f"Confirmado. Eliminando a {username_desconectado} de la sala {id_sala}.")

        # Remover jugador de la estructura de la sala
        sala.remover_jugador(sid_original)

        # Notificar a los demás
        socketio.emit('jugador_desconectado', {
                'jugador_nombre': username_desconectado,
                'jugadores': len(sala.jugadores),
                'lista_jugadores': [datos['nombre'] for datos in sala.jugadores.values()],
                'puede_iniciar': sala.puede_iniciar(),
                'mensaje_desconexion': f"🔌 {username_desconectado} se desconectó."
            }, room=id_sala)

        # Marcarlo como inactivo en la LÓGICA DEL JUEGO 
        if sala.estado == 'jugando' and sala.juego:
            print(f"Marcando a {username_desconectado} como inactivo en la lógica del juego...")

            # Debemos saber de quién era el turno ANTES de marcarlo inactivo
            turno_antes_de_desconexion = sala.juego.obtener_turno_actual()
            print(f"El turno ANTES de la desconexión era de: {turno_antes_de_desconexion}")
            
            sala.juego.marcar_jugador_inactivo(username_desconectado)

            try:
                print(f"Actualizando estadísticas de abandono para {username_desconectado}...")
                user_db = User.query.filter_by(username=username_desconectado).first()
                jugador_juego = sala.juego._encontrar_jugador(username_desconectado) # Obtener su estado en el juego

                if user_db and jugador_juego:
                    user_db.games_played += 1
                    # No sumar victoria 
                    update_xp_and_level(user_db, 25) # Dar una pequeña cantidad de XP por participar

                    # Verificar logros de "fin de partida" para el que abandonó
                    event_data = {
                        'won': False, # Abandono nunca es victoria
                        'final_energy': jugador_juego.get_puntaje(),
                        'reached_position': jugador_juego.get_posicion(),
                        'total_rounds': sala.juego.ronda,
                        'player_count': len(sala.jugadores) + 1, 
                        'colisiones': getattr(jugador_juego, 'colisiones_causadas', 0),
                        'special_tiles_activated': getattr(jugador_juego, 'tipos_casillas_visitadas', set()),
                        'abilities_used': getattr(jugador_juego, 'habilidades_usadas_en_partida', 0),
                        'treasures_this_game': getattr(jugador_juego, 'tesoros_recogidos', 0),
                        'completed_without_traps': getattr(jugador_juego, 'trampas_evitadas', True),
                        'precision_laser': getattr(jugador_juego, 'dado_perfecto_usado', 0),
                        'messages_this_game': getattr(jugador_juego, 'game_messages_sent_this_match', 0),
                        'only_active_player': False,
                        'never_eliminated': False, 
                        'energy_packs_collected': getattr(jugador_juego, 'energy_packs_collected', 0)
                    }
                    unlocked_achievements = achievement_system.check_achievement(username_desconectado, 'game_finished', event_data)
                    if unlocked_achievements:
                        # No podemos emitir al SID original
                        print(f"Logros de abandono guardados para {username_desconectado}.")
                else:
                    print(f"WARN: No se encontró el usuario {username_desconectado} en la DB o en el juego para actualizar stats de abandono.")
            except Exception as e:
                db.session.rollback()
                print(f"!!! ERROR al actualizar stats de abandono: {e}")
                traceback.print_exc()

            # Comprobar si el juego termina
            if sala.juego.ha_terminado():
                print(f"--- JUEGO TERMINADO POR DESCONEXIÓN --- Sala: {id_sala}")
                
                # Cancelar cualquier timer de turno al terminar el juego
                _cancelar_temporizador_turno(id_sala)
                
                sala.estado = 'terminado'
                
                ganador_obj = sala.juego.determinar_ganador()
                ganador_nombre = ganador_obj.get_nombre() if ganador_obj else None
                
                for sid, jugador_data_loop in list(sala.jugadores.items()):
                    if sid in sessions_activas: 
                        username = sessions_activas[sid]['username']
                        jugador_nombre_loop = jugador_data_loop['nombre']
                        jugador_juego = sala.juego._encontrar_jugador(jugador_nombre_loop)

                        if jugador_juego:
                            is_winner = (jugador_nombre_loop == ganador_nombre)

                            # Actualizar estadísticas en la DB
                            user_db = User.query.filter_by(username=username).first()
                            if user_db:
                                user_db.games_played += 1
                                if is_winner: user_db.games_won += 1
                                user_db.xp += 50 + (25 if is_winner else 0) # XP base + bonus
                                db.session.commit()

                                # Verificar logros
                                event_data = {
                                    'won': is_winner,
                                    'final_energy': jugador_juego.get_puntaje(),
                                    'reached_position': jugador_juego.get_posicion(),
                                    'total_rounds': sala.juego.ronda,
                                    'player_count': len(sala.jugadores) + 1,
                                    'colisiones': getattr(jugador_juego, 'colisiones_causadas', 0),
                                    'special_tiles_activated': getattr(jugador_juego, 'tipos_casillas_visitadas', set()),
                                    'abilities_used': getattr(jugador_juego, 'habilidades_usadas_en_partida', 0),
                                    'treasures_this_game': getattr(jugador_juego, 'tesoros_recogidos', 0),
                                    'completed_without_traps': getattr(jugador_juego, 'trampas_evitadas', True),
                                    'precision_laser': getattr(jugador_juego, 'dado_perfecto_usado', 0),
                                    'messages_this_game': getattr(jugador_juego, 'game_messages_sent_this_match', 0),
                                    'only_active_player': True, 
                                    'never_eliminated': jugador_juego.esta_activo(),
                                    'energy_packs_collected': getattr(jugador_juego, 'energy_packs_collected', 0)
                                }
                                unlocked_achievements = achievement_system.check_achievement(username, 'game_finished', event_data)
                                if unlocked_achievements:
                                    socketio.emit('achievements_unlocked', {
                                        'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_achievements]
                                    }, to=sid)
                            
                            # Actualizar presencia a 'online'
                            social_system.update_user_presence(username, 'online', {'sid': sid})

                stats_finales_dict = sala.juego.obtener_estadisticas_finales()
                
                socketio.emit('juego_terminado', {
                    'ganador': stats_finales_dict.get('ganador'),
                    'estadisticas_finales': stats_finales_dict.get('lista_final'),
                    'mensaje': f"🔌 {username_desconectado} se desconectó. ¡Juego terminado!"
                }, room=id_sala)
                
                return # Salir 

            # Si el juego continúa
            else:
                print(f"El juego continúa. Verificando si el turno debe avanzar...")

                if turno_antes_de_desconexion == username_desconectado:
                    print(f"¡Era el turno de {username_desconectado}! Forzando Paso 2 (efectos de casilla)...")
                    try:
                        sala.juego.paso_2_procesar_casilla_y_avanzar(username_desconectado)
                    except Exception as e:
                        print(f"!!! ERROR al forzar Paso 2 en desconexión: {e}")
                        traceback.print_exc()
                        if not sala.juego.ha_terminado():
                             sala.juego._avanzar_turno()
                
                # Ahora, el estado del juego (incluido el turno) está actualizado.
                colores_map = getattr(sala, 'colores_map', {})
                nuevo_turno_actual = sala.juego.obtener_turno_actual() # Obtener el nuevo turno
                
                estado_juego_actualizado = {
                    'jugadores': sala.juego.obtener_estado_jugadores(),
                    'tablero': sala.juego.obtener_estado_tablero(),
                    'turno_actual': nuevo_turno_actual, 
                    'ronda': sala.juego.ronda,
                    'estado': sala.estado,
                    'colores_jugadores': colores_map,
                    'evento_global_activo': sala.juego.evento_global_activo
                }
                
                eventos_recientes = [f"🔌 {username_desconectado} se desconectó."]
                if nuevo_turno_actual:
                     eventos_recientes.append(f"Es el turno de {nuevo_turno_actual}.")

                socketio.emit('estado_juego_actualizado', {
                    'estado_juego': estado_juego_actualizado,
                    'eventos_recientes': eventos_recientes
                }, room=id_sala)
                
                # Iniciar el timer para el *siguiente* jugador
                if nuevo_turno_actual:
                    _iniciar_temporizador_turno(id_sala, nuevo_turno_actual)

        # Si la sala queda vacía, eliminarla
        if len(sala.jugadores) == 0:
            print(f"Sala {id_sala} vacía tras desconexión. Eliminando...")
            if id_sala in salas_activas:
                del salas_activas[id_sala]
    else:
        print(f"Desconexión final: {username_desconectado} ya no estaba en la sala {id_sala}.")

def iniciar_juego_sala(id_sala):
    # Función interna para iniciar el juego en una sala específica
    if id_sala not in salas_activas:
        print(f"ERROR en iniciar_juego_sala: Sala {id_sala} no encontrada.")
        return

    sala = salas_activas[id_sala]
    print(f"--- INTENTANDO INICIAR JUEGO EN SALA {id_sala} --- Estado actual: {sala.estado}")

    if sala.estado != 'esperando':
        print(f"ADVERTENCIA: Intento de iniciar sala {id_sala} que ya está en estado '{sala.estado}'. Ignorando.")
        return

    # Asignar colores a los jugadores
    COLORES_JUGADORES = ['#ef4444', '#3b82f6', '#22c55e', '#f97316'] # Rojo, Azul, Verde, Naranja
    colores_map = {}
    i = 0
    for sid, data in sala.jugadores.items():
        nombre = data['nombre']
        if nombre not in colores_map:
            colores_map[nombre] = COLORES_JUGADORES[i % len(COLORES_JUGADORES)]
            i += 1
    print(f"MAPA DE COLORES CREADO PARA SALA {id_sala}: {colores_map}")
    sala.colores_map = colores_map # Guardar mapa en la sala

    # Llamar a sala.iniciar_juego() para crear la instancia de JuegoOcaWeb
    if sala.iniciar_juego(): # Cambia estado a 'jugando' y crea sala.juego
        print(f"sala.iniciar_juego() tuvo ÉXITO. Estado ahora: {sala.estado}")

        # Preparar el estado inicial del juego para enviar a los clientes
        estado_juego = {
            'estado': sala.estado,
            'jugadores': sala.juego.obtener_estado_jugadores(),
            'tablero': sala.juego.obtener_estado_tablero(),
            'turno_actual': sala.juego.obtener_turno_actual(),
            'ronda': sala.juego.ronda,
            'colores_jugadores': colores_map,
            'evento_global_activo': sala.juego.evento_global_activo 
        }
        print(f"--- ESTADO INICIAL A ENVIAR --- Turno: {estado_juego.get('turno_actual')}, Estado: {estado_juego.get('estado')}")

        # Actualizar presencia de todos los jugadores a "in_game"
        for sid, data in sala.jugadores.items():
            if sid in sessions_activas:
                username = sessions_activas[sid]['username']
                social_system.update_user_presence(username, 'in_game', {'room_id': id_sala, 'sid': sid})

        # Emitir el estado inicial a TODOS los jugadores en la sala
        print(f"EMITIENDO 'juego_iniciado' a sala {id_sala}")
        socketio.emit('juego_iniciado', estado_juego, room=id_sala)
        
        # Iniciar el timer para el *primer* jugador
        primer_jugador_turno = estado_juego.get('turno_actual')
        if primer_jugador_turno:
            _iniciar_temporizador_turno(id_sala, primer_jugador_turno)
    else:
        print(f"ERROR: sala.iniciar_juego() devolvió False. Jugadores: {len(sala.jugadores)}, Estado: {sala.estado}")

def _crear_nueva_sala_revancha(id_sala_original):
    # Intentar obtener Y eliminar la info de revancha atómicamente.
    info_revancha = revanchas_pendientes.pop(id_sala_original, None)
    
    if not info_revancha:
        print(f"INFO: La revancha para sala {id_sala_original} ya fue procesada o cancelada. Ignorando llamada duplicada.")
        return
    
    if info_revancha.get('timer'):
        info_revancha['timer'].cancel()

    nueva_id_sala = str(uuid.uuid4())[:8] # Nuevo ID para la sala de revancha
    print(f"--- CREANDO SALA DE REVANCHA --- Nueva ID: {nueva_id_sala}")
    salas_activas[nueva_id_sala] = SalaJuego(nueva_id_sala)
    nueva_sala = salas_activas[nueva_id_sala]

    jugadores_a_unir = []
    jugadores_rechazados = [] # Para notificar a los que están ocupados

    # Filtrar solo a los participantes originales que solicitaron revancha
    for p_data in info_revancha['participantes']:
        p_username = p_data['nombre']
        if p_username in info_revancha['solicitudes']:
            p_sid_actual = social_system.presence_data.get(p_username, {}).get('extra_data', {}).get('sid')
            
            # Verificar el estado actual del jugador ANTES de unirlo
            estado_actual = social_system._get_user_status(p_username)
            
            # Solo unir si tiene SID y está 'online' (no en otra sala o juego)
            if p_sid_actual and estado_actual == 'online':
                jugadores_a_unir.append({'sid': p_sid_actual, 'nombre': p_username})
            else:
                jugadores_rechazados.append({'sid': p_sid_actual, 'nombre': p_username})
                print(f"WARN (Revancha): Jugador {p_username} solicitó pero su estado es '{estado_actual}'. No será unido.")

    # Verificar mínimo de jugadores (ahora basado en los que SÍ pueden unirse)
    if len(jugadores_a_unir) < MIN_JUGADORES_REVANCHA:
            print(f"REVANCHA CANCELADA (Sala {id_sala_original}): Solo {len(jugadores_a_unir)} jugadores estaban disponibles.")
            # Notificar cancelación a los que sí solicitaron Y a los que estaban ocupados
            for j in (jugadores_a_unir + jugadores_rechazados):
                if j.get('sid'): # Asegurarse que el SID existe
                    socketio.emit('revancha_cancelada', {'mensaje': f'Revancha cancelada. Mínimo de {MIN_JUGADORES_REVANCHA} jugadores requerido.'}, room=j['sid'])
            if nueva_id_sala in salas_activas: del salas_activas[nueva_id_sala] # Eliminar sala nueva vacía
            return

    # Unir jugadores a la nueva sala y notificarles
    for jugador_info in jugadores_a_unir:
        sid_a_unir = jugador_info['sid']
        nombre_a_unir = jugador_info['nombre']
        if nueva_sala.agregar_jugador(sid_a_unir, nombre_a_unir):
            join_room(nueva_id_sala, sid=sid_a_unir) # Unir a la room de SocketIO
            socketio.emit('revancha_lista', {'nueva_id_sala': nueva_id_sala}, room=sid_a_unir) # Notificar al cliente
            social_system.update_user_presence(nombre_a_unir, 'in_lobby', {'room_id': nueva_id_sala, 'sid': sid_a_unir}) # Actualizar presencia

    # Notificar a los que fueron rechazados
    for jugador_info in jugadores_rechazados:
         if jugador_info.get('sid'):
            socketio.emit('revancha_cancelada', {'mensaje': 'Tu revancha se formó, pero ya estabas en otra sala.'}, room=jugador_info['sid'])

    if id_sala_original in salas_activas:
        del salas_activas[id_sala_original]
        
    print(f"Sala de revancha {nueva_id_sala} creada y {len(jugadores_a_unir)} jugadores unidos.")

def iniciar_timer_revancha(id_sala_original):
    # Inicia el temporizador para la revancha
    print(f"TIMER DE REVANCHA INICIADO para sala {id_sala_original}. Esperando {TIEMPO_MAXIMO_REVANCHA} segundos.")

    # Función que se ejecutará cuando el timer expire
    def timer_callback():
        with app.app_context(): # Necesario para operaciones de DB o SocketIO dentro del timer
            print(f"TIMER DE REVANCHA EXPIRADO para sala {id_sala_original}. Intentando crear sala...")
            _crear_nueva_sala_revancha(id_sala_original)

    # Crear y empezar el timer usando threading.Timer
    timer = Timer(TIEMPO_MAXIMO_REVANCHA, timer_callback)
    timer.start()

    # Guardar la referencia al timer por si necesitamos cancelarlo
    if id_sala_original in revanchas_pendientes:
            revanchas_pendientes[id_sala_original]['timer'] = timer

# --- Funciones de Timer ---
TURNO_TIMEOUT_SEGUNDOS = 90 # 90 segundos para que un jugador actúe

def _cancelar_temporizador_turno(id_sala):
    if id_sala in salas_activas:
        sala = salas_activas[id_sala]
        if sala.turn_timer:
            sala.turn_timer.cancel()
            sala.turn_timer = None
            print(f"--- TIMER CANCELADO --- Sala: {id_sala}")

def _expulsar_por_inactividad(id_sala, nombre_jugador_expulsado, turno_ronda_expulsion):
    with app.app_context(): # Necesario para usar socketio y db dentro del hilo del timer
        print(f"--- TIMER EXPIRADO --- Sala: {id_sala}, Jugador: {nombre_jugador_expulsado}")
        sala = salas_activas.get(id_sala)
        if not sala or not sala.juego or sala.estado != 'jugando':
            print(f"Timer expirado: Sala {id_sala} no encontrada o juego no activo. Ignorando.")
            return

        # Safety Check: Asegurarse que el turno no haya avanzado mientras el timer corría
        jugador_actual_juego = sala.juego.obtener_turno_actual()
        ronda_actual_juego = sala.juego.ronda
        if jugador_actual_juego != nombre_jugador_expulsado or ronda_actual_juego != turno_ronda_expulsion:
            print(f"Timer expirado: El turno ya avanzó. Esperado: {nombre_jugador_expulsado} (R{turno_ronda_expulsion}), Actual: {jugador_actual_juego} (R{ronda_actual_juego}). Ignorando.")
            return

        # Encontrar el SID del jugador a expulsar
        sid_a_expulsar = None
        for sid, data in sala.jugadores.items():
            if data['nombre'] == nombre_jugador_expulsado:
                sid_a_expulsar = sid
                break
        
        if not sid_a_expulsar:
            print(f"Timer expirado: No se encontró SID para {nombre_jugador_expulsado}.")
            return

        # Notificar a todos en la sala
        socketio.emit('error', {
            'mensaje': f"⏳ ¡{nombre_jugador_expulsado} ha sido expulsado por inactividad! Avanzando turno..."
        }, room=id_sala)
        
        # Usar la función de desconexión existente para manejar la expulsión
        _finalizar_desconexion(sid_a_expulsar, id_sala, nombre_jugador_expulsado)

def _iniciar_temporizador_turno(id_sala, nombre_jugador_turno):
    _cancelar_temporizador_turno(id_sala) # Cancelar cualquier timer anterior por si acaso
    
    sala = salas_activas.get(id_sala)
    if not sala or not sala.juego:
        return

    print(f"--- TIMER INICIADO --- Sala: {id_sala}, Jugador: {nombre_jugador_turno}, Duración: {TURNO_TIMEOUT_SEGUNDOS}s")
    
    # Guardamos la ronda actual para el safety check
    ronda_actual = sala.juego.ronda 
    
    timer = threading.Timer(
        TURNO_TIMEOUT_SEGUNDOS,
        _expulsar_por_inactividad,
        args=[id_sala, nombre_jugador_turno, ronda_actual]
    )
    sala.turn_timer = timer
    timer.start()

def limpiar_salas_inactivas():
    # Función periódica para limpiar salas vacías
    while True:
        time.sleep(30 * 60) # Ejecutar cada 30 minutos
        with app.app_context(): # Necesario para acceder a 'salas_activas' de forma segura
            ahora = datetime.now()
            salas_a_eliminar = []
            print(f"\n--- Ejecutando Limpieza de Salas Inactivas ({ahora.strftime('%H:%M')}) ---")
            for id_sala, sala in list(salas_activas.items()): # Usar list() para poder modificar el dict mientras se itera
                tiempo_desde_creacion = ahora - sala.creado_en
                # Criterios de eliminación: Vacía o muy antigua (ej. > 2 horas)
                if not sala.jugadores or tiempo_desde_creacion.total_seconds() > (2 * 60 * 60):
                    salas_a_eliminar.append(id_sala)

            if salas_a_eliminar:
                print(f"Eliminando {len(salas_a_eliminar)} salas inactivas: {salas_a_eliminar}")
                for id_sala in salas_a_eliminar:
                    if id_sala in salas_activas:
                        del salas_activas[id_sala]
                        # También limpiar revanchas pendientes asociadas si existen
                        if id_sala in revanchas_pendientes:
                            if revanchas_pendientes[id_sala].get('timer'):
                                revanchas_pendientes[id_sala]['timer'].cancel()
                            del revanchas_pendientes[id_sala]
            else:
                print("No se encontraron salas inactivas para eliminar.")

def _procesar_estadisticas_fin_juego_async(app, jugadores_items, ganador_nombre, ronda, player_count_db, juego_obj):
    with app.app_context():
        print(f"--- THREAD: Iniciando procesamiento de estadísticas para {len(jugadores_items)} jugadores...")
        try:
            for sid, jugador_data in jugadores_items:
                if sid in sessions_activas:
                    username = sessions_activas[sid]['username']
                    jugador_nombre_loop = jugador_data['nombre']
                    jugador_juego = juego_obj._encontrar_jugador(jugador_nombre_loop) # Usar método interno seguro

                    if jugador_juego:
                        is_winner = jugador_nombre_loop == ganador_nombre
                        user_db = User.query.filter_by(username=username).first()
                        if user_db:
                            user_db.games_played += 1
                            xp_ganada = 50 # XP base por jugar
                            
                            current_consecutive_wins = 0 # Valor por defecto
                            if is_winner: 
                                user_db.games_won += 1
                                xp_ganada += 25 # Bonus XP por ganar
                                # Incrementar racha de victorias
                                user_db.consecutive_wins = getattr(user_db, 'consecutive_wins', 0) + 1
                                current_consecutive_wins = user_db.consecutive_wins
                            else:
                                # Resetear racha de victorias
                                user_db.consecutive_wins = 0
                                current_consecutive_wins = 0

                            level_up = update_xp_and_level(user_db, xp_ganada) # Esto hace db.session.commit()
                            
                            if level_up:
                                socketio.emit('level_up', {'new_level': user_db.level, 'xp': user_db.xp}, to=sid)
                            
                            event_data = {
                                'won': is_winner,
                                'final_energy': jugador_juego.get_puntaje(),
                                'reached_position': jugador_juego.get_posicion(),
                                'total_rounds': ronda,
                                'player_count': player_count_db, 
                                'colisiones': getattr(jugador_juego, 'colisiones_causadas', 0),
                                'special_tiles_activated': getattr(jugador_juego, 'tipos_casillas_visitadas', set()),
                                'abilities_used': getattr(jugador_juego, 'habilidades_usadas_en_partida', 0),
                                'treasures_this_game': getattr(jugador_juego, 'tesoros_recogidos', 0),
                                'completed_without_traps': getattr(jugador_juego, 'trampas_evitadas', True),
                                'precision_laser': getattr(jugador_juego, 'dado_perfecto_usado', 0),
                                'messages_this_game': getattr(jugador_juego, 'game_messages_sent_this_match', 0),
                                'only_active_player': len([j for j in juego_obj.jugadores if j.esta_activo()]) == 1,
                                'never_eliminated': jugador_juego.esta_activo(),
                                'energy_packs_collected': getattr(jugador_juego, 'energy_packs_collected', 0),
                                'consecutive_wins': current_consecutive_wins,
                                'ultimo_en_mid_game': getattr(juego_obj, 'ultimo_en_mid_game', None)
                            }

                            # check_achievement también hace db.session.commit()
                            unlocked_achievements = achievement_system.check_achievement(username, 'game_finished', event_data) 
                            if unlocked_achievements:
                                socketio.emit('achievements_unlocked', {
                                    'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_achievements]
                                }, to=sid)
                        social_system.update_user_presence(username, 'online', {'sid': sid})
            print("--- THREAD: Procesamiento de estadísticas COMPLETO.")
        except Exception as e:
            print(f"!!! ERROR FATAL en hilo _procesar_estadisticas_fin_juego: {e}")
            traceback.print_exc()

def get_friends_list_server_safe(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return []
    # Obtener los nombres de usuario de los amigos
    friends = [friend.username for friend in user.friends]
    return friends

# Asignar la función a social_system para que el código anterior funcione
social_system.get_friends_list_server = get_friends_list_server_safe

def _procesar_login_diario(user_obj):
    if not user_obj:
        return

    try:
        today = datetime.utcnow().date()
        # Obtener el último login (puede ser None o un objeto date)
        last_login_day = getattr(user_obj, 'last_login_date', None)

        if last_login_day != today:
            print(f"--- LOGIN DIARIO DETECTADO --- Usuario: {user_obj.username}. Último login: {last_login_day}, Hoy: {today}")
            
            # Actualizar el contador y la fecha en la DB
            user_obj.last_login_date = today
            current_days_count = getattr(user_obj, 'unique_login_days_count', 0) + 1
            user_obj.unique_login_days_count = current_days_count
            
            db.session.commit() # Guardar los cambios en la DB

            # Ahora, comprobar el logro con el nuevo contador
            unlocked_list = achievement_system.check_achievement(
                user_obj.username, 
                'login', 
                {'login_days': current_days_count}
            )

            if unlocked_list:
                # Si se desbloqueó, notificar al usuario (si está conectado)
                sid = social_system.presence_data.get(user_obj.username, {}).get('extra_data', {}).get('sid')
                if sid:
                    socketio.emit('achievements_unlocked', {
                        'achievements': [achievement_system.get_achievement_info(ach_id) for ach_id in unlocked_list]
                    }, to=sid)
        else:
            # Si ya se logueó hoy, no hacer nada
            print(f"--- Login repetido hoy para {user_obj.username}. No se cuenta como nuevo día. ---")

    except Exception as e:
        db.session.rollback()
        print(f"!!! ERROR al procesar login diario para {user_obj.username}: {e}")
        traceback.print_exc()

# Iniciar el hilo de limpieza en segundo plano
hilo_limpieza = threading.Thread(target=limpiar_salas_inactivas, daemon=True)
hilo_limpieza.start()
print("Hilo de limpieza de salas iniciado.")

