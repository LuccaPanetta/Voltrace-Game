import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego_web import JuegoOcaWeb
from app import app, socketio, db, User
from habilidades import Habilidad
from game_config import POSICION_META

@pytest.fixture
def socket_env_limit():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'secret_limit'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        users = [User(username=f"Jugador{i}", email=f"p{i}@test.com") for i in range(5)]
        for u in users: u.set_password("123")
        db.session.add_all(users)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def juego_interacciones():
    """Juego configurado para probar interacciones complejas."""
    config = [
        {'nombre': 'Trampero', 'kit_id': 'ingeniero'}, 
        {'nombre': 'Victima', 'kit_id': 'tactico'}
    ]
    juego = JuegoOcaWeb(config, achievement_system=None)
    return juego

def get_event_arg(received, event_name):
    for event in received:
        if event['name'] == event_name:
            return event['args'][0]
    return None

def test_limite_sala_llena(socket_env_limit):
    clients = []
    # Conectar 5 clientes
    for i in range(5):
        c = socketio.test_client(socket_env_limit)
        c.emit('authenticate', {'username': f"Jugador{i}"})
        clients.append(c)
    
    # Jugador 0 crea sala
    clients[0].emit('crear_sala', {'kit_id': 'tactico'})
    id_sala = get_event_arg(clients[0].get_received(), 'sala_creada')['id_sala']
    
    # Jugadores 1, 2, 3 se unen 
    for i in range(1, 4):
        clients[i].emit('unirse_sala', {'id_sala': id_sala})
        resp = get_event_arg(clients[i].get_received(), 'unido_exitoso')
        assert resp is not None, f"Jugador{i} debería haber entrado"
        
    # Jugador 4 intenta unirse
    clients[4].emit('unirse_sala', {'id_sala': id_sala})
    
    # Verificar rechazo
    resp_fail = clients[4].get_received()
    error_msg = get_event_arg(resp_fail, 'error')
    
    assert error_msg is not None
    # El mensaje debe indicar que está llena
    assert "llena" in error_msg['mensaje'].lower() or "máximo" in error_msg['mensaje'].lower()
    
    for c in clients: c.disconnect()

def test_desconexion_en_turno_avanza(juego_interacciones):
    juego = juego_interacciones
    p1 = juego.jugadores[0] # Trampero
    p2 = juego.jugadores[1] # Victima
    
    # Forzamos que sea turno de P1
    juego.turno_actual = 0
    assert p1.esta_activo() is True
    
    # Simulamos desconexión 
    juego.marcar_jugador_inactivo(p1.get_nombre())
    
    assert p1.esta_activo() is False
    
    # Ejecutamos la lógica de avanzar turno
    juego._avanzar_turno()
    
    # El turno debería ser ahora de P2
    assert juego.turno_actual == 1
    assert juego.obtener_turno_actual() == p2.get_nombre()

def test_victoria_por_intercambio(juego_interacciones):
    p1 = juego_interacciones.jugadores[0]
    p2 = juego_interacciones.jugadores[1]
    
    # Inyectamos la habilidad de Intercambio a P1
    intercambio = Habilidad("Intercambio Forzado", "movimiento", "desc", "🔄", 5, 0)
    p1.habilidades.append(intercambio)
    
    # Situación: P1 está lejos, P2 está YA en la meta 
    p1.teletransportar_a(5)
    p2.teletransportar_a(POSICION_META) 
    
    # P1 usa intercambio con P2
    res = juego_interacciones.usar_habilidad_jugador(p1.nombre, len(p1.habilidades), objetivo=p2.nombre)
    
    assert res['exito'] is True
    
    # P1 debería estar ahora en la meta
    assert p1.get_posicion() >= POSICION_META
    
    # El juego debería detectar que terminó
    assert juego_interacciones.ha_terminado() is True
    assert juego_interacciones.determinar_ganador().nombre == p1.nombre

def test_perk_recompensa_mina(juego_interacciones):
    trampero = juego_interacciones.jugadores[0]
    victima = juego_interacciones.jugadores[1]
    
    # Darle el Perk al Trampero
    trampero.perks_activos.append("recompensa_de_mina")
    energia_inicial_trampero = trampero.get_puntaje()
    
    # Colocar la mina manualmente en el tablero 
    pos_mina = 10
    juego_interacciones.casillas_especiales[pos_mina] = {
        "tipo": "trampa",
        "nombre": "Mina de Energía",
        "valor": -50,
        "colocada_por": trampero.get_nombre() 
    }
    
    # La víctima cae en la mina
    victima.teletransportar_a(pos_mina)
    juego_interacciones._procesar_efectos_posicion(victima, pos_mina)

    assert trampero.get_puntaje() == energia_inicial_trampero + 25
    assert "Mina" in str(juego_interacciones.eventos_turno)