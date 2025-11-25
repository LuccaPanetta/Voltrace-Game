import pytest
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, social_system

@pytest.fixture
def social_env():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'social_secret'
    
    with app.app_context():
        db.create_all()
        # Crear 2 usuarios
        u1 = User(username="Juan", email="a@test.com"); u1.set_password("123")
        u2 = User(username="Bob", email="b@test.com"); u2.set_password("123")
        db.session.add_all([u1, u2])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

def test_solicitud_amistad_flujo_completo(social_env):
    with social_env.app_context():
        # Juan envía solicitud a Bob
        res_send = social_system.send_friend_request("Juan", "Bob")
        assert res_send['success'] is True
        
        # Verificar estado intermedio (Pendiente)
        bob = User.query.filter_by(username="Bob").first()
        alice = User.query.filter_by(username="Juan").first()
        
        assert alice.has_sent_request_to(bob) is True
        assert bob.has_received_request_from(alice) is True
        assert alice.is_friend(bob) is False
        
        # Bob acepta la solicitud
        res_accept = social_system.accept_friend_request("Bob", "Juan")
        assert res_accept['success'] is True
        
        # Verificar Amistad
        # Recargamos objetos para asegurar estado fresco
        db.session.expire_all()
        bob = User.query.filter_by(username="Bob").first()
        alice = User.query.filter_by(username="Juan").first()
        
        assert alice.is_friend(bob) is True
        assert bob.is_friend(alice) is True
        
        # Verificar que ya no hay solicitudes pendientes
        assert alice.has_sent_request_to(bob) is False
        assert bob.has_received_request_from(alice) is False

def test_solicitud_rechazada(social_env):
    with social_env.app_context():
        social_system.send_friend_request("Juan", "Bob")
        
        res_reject = social_system.reject_friend_request("Bob", "Juan")
        assert res_reject['success'] is True 
        
        alice = User.query.filter_by(username="Juan").first()
        bob = User.query.filter_by(username="Bob").first()
        
        assert alice.is_friend(bob) is False
        assert bob.has_received_request_from(alice) is False