import pytest
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, socketio, db, User


@pytest.fixture
def socket_clients():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SECRET_KEY"] = "test_secret"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        u1 = User(username="Player1", email="p1@test.com")
        u1.set_password("123")
        u2 = User(username="Player2", email="p2@test.com")
        u2.set_password("123")
        db.session.add_all([u1, u2])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def get_event_arg(received, event_name):
    for event in received:
        if event["name"] == event_name:
            return event["args"][0]
    return None


def test_creacion_y_union_sala(socket_clients):
    # --- CLIENTE 1 (HOST) ---
    client1 = socketio.test_client(socket_clients)
    client1.emit("authenticate", {"username": "Player1"})

    # Player1 crea sala
    client1.emit("crear_sala", {"kit_id": "tactico"})

    # Buscar respuesta
    received = client1.get_received()
    data_sala = get_event_arg(received, "sala_creada")

    assert data_sala is not None, "No se recibió evento 'sala_creada'"
    id_sala = data_sala["id_sala"]

    # --- CLIENTE 2 (INVITADO) ---
    client2 = socketio.test_client(socket_clients)
    client2.emit("authenticate", {"username": "Player2"})

    # Player2 se une
    client2.emit("unirse_sala", {"id_sala": id_sala})

    # Verificar respuesta para Client2
    received_2 = client2.get_received()
    data_unido = get_event_arg(received_2, "unido_exitoso")
    assert data_unido is not None
    assert data_unido["id_sala"] == id_sala

    client1.disconnect()
    client2.disconnect()


def test_validacion_turno_socket(socket_clients):
    client1 = socketio.test_client(socket_clients)
    client1.emit("authenticate", {"username": "Player1"})
    client1.emit("crear_sala", {})

    # Obtener ID sala de forma segura
    received = client1.get_received()
    data_sala = get_event_arg(received, "sala_creada")
    assert data_sala is not None
    id_sala = data_sala["id_sala"]

    client2 = socketio.test_client(socket_clients)
    client2.emit("authenticate", {"username": "Player2"})
    client2.emit("unirse_sala", {"id_sala": id_sala})

    # Iniciar juego
    client1.emit("iniciar_juego", {"id_sala": id_sala})

    # Limpiar colas
    client1.get_received()
    client2.get_received()

    # Intentar jugar fuera de turno (Player2)
    client2.emit("lanzar_dado", {"id_sala": id_sala})

    # Verificar error
    received_2 = client2.get_received()
    error_data = get_event_arg(received_2, "error")

    assert error_data is not None
    assert "No es tu turno" in error_data["mensaje"]


def test_chat_sala(socket_clients):
    c1 = socketio.test_client(socket_clients)
    c1.emit("authenticate", {"username": "Player1"})
    c1.emit("crear_sala", {})

    received = c1.get_received()
    id_sala = get_event_arg(received, "sala_creada")["id_sala"]

    c2 = socketio.test_client(socket_clients)
    c2.emit("authenticate", {"username": "Player2"})
    c2.emit("unirse_sala", {"id_sala": id_sala})

    # Limpiar
    c1.get_received()
    c2.get_received()

    # Enviar mensaje
    msg = "Test Socket Chat"
    c1.emit("enviar_mensaje", {"id_sala": id_sala, "mensaje": msg})

    # Verificar recepción en C2
    resp_c2 = c2.get_received()
    chat_data = get_event_arg(resp_c2, "nuevo_mensaje")

    assert chat_data is not None
    assert chat_data["mensaje"] == msg
    assert chat_data["jugador"] == "Player1"
