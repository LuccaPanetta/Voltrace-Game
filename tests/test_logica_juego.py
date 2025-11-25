import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego_web import JuegoOcaWeb
from jugadores import JugadorWeb
from game_config import ENERGIA_INICIAL, POSICION_META

# --- FIXTURES ---
@pytest.fixture
def juego_base():
    """Crea una partida estándar con 2 jugadores para testing."""
    config_jugadores = [
        {'nombre': 'Tester1', 'kit_id': 'tactico', 'avatar_emoji': '🧪'},
        {'nombre': 'Tester2', 'kit_id': 'ingeniero', 'avatar_emoji': '⚙️'}
    ]
    return JuegoOcaWeb(config_jugadores, achievement_system=None)

# --- TESTS UNITARIOS ---

def test_inicializacion_correcta(juego_base):
    assert len(juego_base.jugadores) == 2
    assert juego_base.ronda == 1
    assert juego_base.turno_actual == 0
    
    p1 = juego_base.jugadores[0]
    assert p1.nombre == 'Tester1'
    assert p1.get_puntaje() == ENERGIA_INICIAL
    assert p1.get_posicion() == 1
    # Verificar que se asignaron habilidades según el kit
    assert len(p1.habilidades) == 4 
    assert p1.habilidades[0].nombre == "Sabotaje" # Primera habilidad del Táctico

def test_movimiento_y_energia(juego_base):
    p1 = juego_base.jugadores[0]
    pos_inicial = p1.get_posicion()
    energia_inicial = p1.get_puntaje()
    
    p1.avanzar(5)
    assert p1.get_posicion() == pos_inicial + 5
    
    # Recibir daño
    daño = -50
    p1.procesar_energia(daño)
    assert p1.get_puntaje() == energia_inicial + daño

def test_perk_ultimo_aliento(juego_base):
    p1 = juego_base.jugadores[0]
    # Forzamos que tenga el perk
    p1.perks_activos.append("ultimo_aliento")
    
    # Aplicamos daño letal 
    daño_letal = -(ENERGIA_INICIAL + 100)
    p1.procesar_energia(daño_letal)
    
    # Verificaciones
    assert p1.esta_activo() is True  # No debe morir
    assert p1.get_puntaje() == 50    # Debe revivir con 50
    # Debe tener escudo activo
    tiene_escudo = any(e['tipo'] == 'escudo' for e in p1.efectos_activos)
    assert tiene_escudo is True

def test_condicion_victoria(juego_base):
    p1 = juego_base.jugadores[0]
    
    # Teletransportar a la meta
    p1.teletransportar_a(POSICION_META)
    
    # La función ha_terminado debería devolver True
    assert juego_base.ha_terminado() is True
    
    # Determinar ganador
    ganador = juego_base.determinar_ganador()
    assert ganador.nombre == 'Tester1'

def test_cooldown_habilidades(juego_base):
    p1 = juego_base.jugadores[0]
    habilidad = p1.habilidades[0] # Sabotaje
    
    # Simular uso de habilidad 
    p1.poner_en_cooldown(habilidad, tiene_perk_enfriamiento_rapido=False)
    
    assert p1.habilidades_cooldown[habilidad.nombre] == habilidad.cooldown_base
    
    # Simular paso de turno 
    p1.reducir_cooldowns(1)
    assert p1.habilidades_cooldown[habilidad.nombre] == (habilidad.cooldown_base - 1)

def test_intercambio_posiciones(juego_base):
    p1 = juego_base.jugadores[0]
    p2 = juego_base.jugadores[1]
    
    # Posiciones iniciales distintas
    p1.teletransportar_a(10)
    p2.teletransportar_a(20)
    
    # Ejecutar intercambio 
    pos_p1_antes = p1.get_posicion()
    pos_p2_antes = p2.get_posicion()
    
    p1.teletransportar_a(pos_p2_antes)
    p2.teletransportar_a(pos_p1_antes)
    
    assert p1.get_posicion() == 20
    assert p2.get_posicion() == 10