import pytest
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User

@pytest.fixture
def cliente_test():
    app.config['TESTING'] = True
    # Usar DB en memoria para que esté limpia y tenga todas las columnas nuevas
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    # Clave secreta falsa necesaria para las sesiones (Login)
    app.config['SECRET_KEY'] = 'clave_secreta_para_tests_123'
    app.config['WTF_CSRF_ENABLED'] = False 
    
    # Crear contexto de aplicación
    with app.app_context():
        # Crear todas las tablas desde cero
        db.create_all()
        
        yield app.test_client()
        
        # Limpieza al terminar
        db.session.remove()
        db.drop_all()

def test_registro_usuario(cliente_test):
    payload = {
        "username": "TestUser",
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = cliente_test.post('/register', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
    
    # Verificar respuesta HTTP
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['user_data']['username'] == "TestUser"
    
    # Verificar que se guardó en la DB simulada
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        assert user is not None
        assert user.username == "TestUser"

def test_login_exitoso(cliente_test):
    # Registrar primero 
    cliente_test.post('/register', 
                      data=json.dumps({
                          "username": "LoginTester", 
                          "email": "login@test.com", 
                          "password": "123"
                      }),
                      content_type='application/json')
    
    # Intentar Login
    payload = {
        "email": "login@test.com",
        "password": "123"
    }
    response = cliente_test.post('/login', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['user_data']['username'] == "LoginTester"

def test_login_fallido(cliente_test):
    payload = {
        "email": "noexiste@test.com",
        "password": "123"
    }
    response = cliente_test.post('/login', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] is False

def test_ruta_protegida_sin_login(cliente_test):
    response = cliente_test.post('/api/set_avatar', 
                                 data=json.dumps({"avatar_emoji": "😎"}),
                                 content_type='application/json')
    
    assert response.status_code == 401

def test_obtener_perks(cliente_test):
    response = cliente_test.get('/api/get_all_perks')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert isinstance(data, dict)
    assert "recarga_constante" in data

def test_perfil_usuario(cliente_test):
    # Crear usuario
    cliente_test.post('/register', 
                      data=json.dumps({"username": "ProfileUser", "email": "p@p.com", "password": "123"}),
                      content_type='application/json')
    
    # Consultar perfil
    response = cliente_test.get('/profile/ProfileUser')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['stats']['username'] == "ProfileUser"