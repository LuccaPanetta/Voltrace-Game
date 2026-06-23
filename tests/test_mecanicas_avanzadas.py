import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.juego_web import JuegoOcaWeb
from src.core.game_config import ENERGIA_TRAMPA, ENERGIA_INICIAL, POSICION_META
from src.core.habilidades import Habilidad


@pytest.fixture
def juego_avanzado():
    config = [
        {"nombre": "Viajero", "kit_id": "espectro"},
        {"nombre": "Tanque", "kit_id": "guardian"},
    ]
    juego = JuegoOcaWeb(config, achievement_system=None)
    return juego


def test_casilla_trampa(juego_avanzado):
    p1 = juego_avanzado.jugadores[0]
    energia_inicial = p1.get_puntaje()

    pos_trampa = 5
    juego_avanzado.casillas_especiales[pos_trampa] = {
        "tipo": "trampa",
        "valor": ENERGIA_TRAMPA,
        "nombre": "Trampa Test",
    }

    p1.teletransportar_a(pos_trampa)
    juego_avanzado._procesar_efectos_posicion(p1, pos_trampa)

    assert p1.get_puntaje() == energia_inicial + ENERGIA_TRAMPA


def test_fuga_energia_vs_escudo(juego_avanzado):
    victima = juego_avanzado.jugadores[1]  # Tanque
    energia_inicial = victima.get_puntaje()

    # Aplicar Fuga de Energía a la víctima
    victima.efectos_activos.append({"tipo": "fuga_energia", "turnos": 3, "dano": 25})

    # Aplicar Escudo a la víctima
    victima.efectos_activos.append({"tipo": "escudo", "turnos": 1})

    # Simular inicio de turno
    juego_avanzado._procesar_inicio_turno(victima)

    assert victima.get_puntaje() == energia_inicial


def test_muerte_definitiva_sin_ultimo_aliento(juego_avanzado):
    p1 = juego_avanzado.jugadores[0]

    # Aseguramos que NO tenga Último Aliento
    p1.perks_activos = []

    # Aplicar daño masivo
    daño_letal = -(ENERGIA_INICIAL + 500)
    p1.procesar_energia(daño_letal)

    # Verificaciones
    assert p1.get_puntaje() == 0
    assert p1.esta_activo() is False


def test_caos_victoria_accidental(juego_avanzado):
    lanzador = juego_avanzado.jugadores[0]
    afortunado = juego_avanzado.jugadores[1]

    # Posicionar al afortunado MUY cerca de la meta
    afortunado.teletransportar_a(POSICION_META - 1)

    # Forzamos la habilidad en el juego para no depender del índice
    caos = Habilidad("Caos", "control", "desc", "🎲", 6, 0)
    # Inyectamos la habilidad
    lanzador.habilidades.append(caos)
    idx_caos = len(lanzador.habilidades)

    # Ejecutar Caos
    resultado = juego_avanzado.usar_habilidad_jugador(lanzador.nombre, idx_caos)

    assert resultado["exito"] is True

    # Verificar que el juego terminó
    assert juego_avanzado.ha_terminado() is True

    # Verificar que el ganador es el que cruzó la meta, NO el que lanzó la habilidad
    ganador = juego_avanzado.determinar_ganador()
    assert ganador.nombre == afortunado.nombre


def test_barrera_reflejo_dano(juego_avanzado):
    atacante = juego_avanzado.jugadores[0]
    defensor = juego_avanzado.jugadores[1]

    energia_inicial_atacante = atacante.get_puntaje()
    energia_inicial_defensor = defensor.get_puntaje()

    # Inyectar Barrera
    barrera_fake = Habilidad("Barrera", "defensiva", "desc", "🔮", 5, 0)
    defensor.habilidades.append(barrera_fake)
    idx_barrera = len(defensor.habilidades)
    juego_avanzado.usar_habilidad_jugador(defensor.nombre, idx_barrera)

    # Inyectar Bomba
    bomba_fake = Habilidad("Bomba Energética", "ofensiva", "desc", "💥", 5, 0)
    atacante.habilidades.append(bomba_fake)

    # Posicionar
    atacante.teletransportar_a(10)
    defensor.teletransportar_a(11)

    # Atacar
    juego_avanzado.usar_habilidad_jugador(atacante.nombre, len(atacante.habilidades))

    # Verificaciones
    assert defensor.get_puntaje() == energia_inicial_defensor
    assert atacante.get_puntaje() < energia_inicial_atacante
