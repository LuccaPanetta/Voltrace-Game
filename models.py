# ===================================================================
# MODELOS DE BASE DE DATOS - VOLTRACE (models.py)
# ===================================================================
#
# Este archivo define el esquema de la base de datos (DB Schema)
# utilizando Flask-SQLAlchemy.
#
# Modelos definidos:
# - User: Almacena la información de la cuenta, perfil, nivel, XP,
#   y define las relaciones de amistad y logros.
# - PrivateMessage: Almacena un mensaje privado entre dos usuarios.
# - Achievement: Define la configuración de un logro (nombre, icono, etc.).
# - UserAchievement: Tabla de asociación que vincula un User con un
#   Achievement desbloqueado (relación N-a-N).
# - Tablas de asociación: 'friendship' y 'friend_request' para
#   el sistema social.
#
# ===================================================================

from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Modelo de tabla de asociación para Amigos (relación muchos-a-muchos)
friendship = db.Table('friendship',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Modelo de tabla de asociación para Solicitudes de Amistad
friend_request = db.Table('friend_request',
    db.Column('sender_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('receiver_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Modelo de tabla de asociación para Logros de Usuario
class UserAchievement(db.Model):
    __tablename__ = 'user_achievement'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), primary_key=True)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones (opcional, pero útil)
    user = db.relationship('User', back_populates='unlocked_achievements_assoc')
    achievement = db.relationship('Achievement', back_populates='user_associations')

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256)) # Aumentado a 256
    
    # Estadísticas del jugador
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    game_messages_sent = db.Column(db.Integer, default=0) 
    private_messages_sent = db.Column(db.Integer, default=0) 
    games_won = db.Column(db.Integer, default=0)
    abilities_used = db.Column(db.Integer, default=0)
    rooms_created = db.Column(db.Integer, default=0)
    
    # --- Sistema Social (Amigos) ---
    
    # Amigos (Muchos-a-Muchos)
    friends = db.relationship('User',
        secondary=friendship,
        primaryjoin=(friendship.c.user_id == id),
        secondaryjoin=(friendship.c.friend_id == id),
        backref=db.backref('friend_of', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # Solicitudes Enviadas (Muchos-a-Muchos)
    sent_requests = db.relationship('User',
        secondary=friend_request,
        primaryjoin=(friend_request.c.sender_id == id),
        secondaryjoin=(friend_request.c.receiver_id == id),
        backref=db.backref('received_requests', lazy='dynamic'),
        lazy='dynamic'
    )

    # --- Sistema Social (Chat Privado) ---
    messages_sent = db.relationship('PrivateMessage',
                                    foreign_keys='PrivateMessage.sender_id',
                                    backref='sender', lazy='dynamic')
    messages_received = db.relationship('PrivateMessage',
                                        foreign_keys='PrivateMessage.recipient_id',
                                        backref='recipient', lazy='dynamic')

    # --- Sistema de Logros ---
    unlocked_achievements_assoc = db.relationship('UserAchievement', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_friend(self, user):
        if not self.is_friend(user):
            self.friends.append(user)
            user.friends.append(self)
            return True
        return False

    def remove_friend(self, user):
        if self.is_friend(user):
            self.friends.remove(user)
            user.friends.remove(self)
            return True
        return False

    def is_friend(self, user):
        return self.friends.filter(friendship.c.friend_id == user.id).count() > 0

    def send_friend_request(self, user):
        if not self.has_sent_request_to(user) and not user.has_sent_request_to(self) and not self.is_friend(user) and self != user:
            self.sent_requests.append(user)
            return True
        return False

    def has_sent_request_to(self, user):
        return self.sent_requests.filter(friend_request.c.receiver_id == user.id).count() > 0

    def has_received_request_from(self, user):
        return self.received_requests.filter(friend_request.c.sender_id == user.id).count() > 0

    def accept_friend_request(self, user):
        if self.has_received_request_from(user):
            self.received_requests.remove(user) # Eliminar de "Recibidas" del receptor
            
            if user.has_sent_request_to(self):
                user.sent_requests.remove(self) # Eliminar de "Enviadas" del emisor

            self.add_friend(user) # Añadir la amistad
            return True
        return False

    def reject_friend_request(self, user):
        # 'self' es el receptor, 'user' es el remitente
        request_found = False
        if self.has_received_request_from(user):
            self.received_requests.remove(user)
            request_found = True
        
        if user.has_sent_request_to(self):
            user.sent_requests.remove(self)
            request_found = True
            
        return request_found

    def get_unlocked_achievements(self):
        return [ua.achievement for ua in self.unlocked_achievements_assoc]

    def get_reset_token(self, expires_sec=1800):
        # Usamos la nueva clase
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
            user_id = data['user_id']
        except Exception:
            # Token inválido, expirado o con salt incorrecto
            return None
        # Devuelve el usuario si el ID es válido
        return User.query.get(user_id)

class PrivateMessage(db.Model):
    __tablename__ = 'private_message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False, nullable=False)

class Achievement(db.Model):
    __tablename__ = 'achievement'
    id = db.Column(db.Integer, primary_key=True)
    # Identificador único en código (ej: 'FIRST_WIN')
    internal_id = db.Column(db.String(100), unique=True, nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250))
    icon = db.Column(db.String(20), default="🏆")
    xp_reward = db.Column(db.Integer, default=0)
    
    user_associations = db.relationship('UserAchievement', back_populates='achievement')