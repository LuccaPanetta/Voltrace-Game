import pytest
import sys
import os

# Asegurar imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego_web import JuegoOcaWeb
from game_config import COSTO_SABOTAJE, DANO_BOMBA


@pytest.fixture
def juego_combate():
    config = [
        {"nombre": "Atacante", "kit_id": "tactico"},  # idx 0
        {"nombre": "Defensor", "kit_id": "guardian"},  # idx 1
        {"nombre": "Tercero", "kit_id": "ingeniero"},  # idx 2
    ]
    juego = JuegoOcaWeb(config, achievement_system=None)

    for j in juego.jugadores:
        j.procesar_energia(500)  # Tienen mucha energía
        j.ganar_pm(10)

    return juego


def test_habilidad_sabotaje(juego_combate):
    atacante = juego_combate.jugadores[0]
    victima = juego_combate.jugadores[1]

    # Buscamos la habilidad "Sabotaje"
    sabotaje = next(h for h in atacante.habilidades if h.nombre == "Sabotaje")

    # Usar habilidad
    resultado = juego_combate.usar_habilidad_jugador(
        atacante.nombre,
        atacante.habilidades.index(sabotaje) + 1,
        objetivo=victima.nombre,
    )

    assert resultado["exito"] is True
    # Verificar que la víctima tiene el efecto 'pausa'
    tiene_pausa = any(e["tipo"] == "pausa" for e in victima.efectos_activos)
    assert tiene_pausa is True


def test_bomba_energetica_area(juego_combate):
    lanzador = juego_combate.jugadores[2]  # Ingeniero tiene bomba
    vecino_cercano = juego_combate.jugadores[1]
    vecino_lejano = juego_combate.jugadores[0]

    # Posicionar jugadores
    lanzador.teletransportar_a(10)
    vecino_cercano.teletransportar_a(12)  # Distancia 2
    vecino_lejano.teletransportar_a(20)  # Distancia 10

    energia_antes_cercano = vecino_cercano.get_puntaje()
    energia_antes_lejano = vecino_lejano.get_puntaje()

    bomba = next(h for h in lanzador.habilidades if h.nombre == "Bomba Energética")

    # Usar bomba (no requiere objetivo específico, es zonal)
    resultado = juego_combate.usar_habilidad_jugador(
        lanzador.nombre, lanzador.habilidades.index(bomba) + 1
    )

    assert resultado["exito"] is True

    # El cercano debió perder energía
    assert vecino_cercano.get_puntaje() == energia_antes_cercano - DANO_BOMBA
    # El lejano debió quedar igual
    assert vecino_lejano.get_puntaje() == energia_antes_lejano


def test_intercambio_forzado(juego_combate):
    from habilidades import Habilidad, COSTO_INTERCAMBIO

    intercambio = Habilidad(
        "Intercambio Forzado", "movimiento", "desc", "🔄", 5, COSTO_INTERCAMBIO
    )

    p1 = juego_combate.jugadores[0]
    p2 = juego_combate.jugadores[1]

    # Inyectamos la habilidad a la fuerza para testear la lógica
    p1.habilidades.append(intercambio)
    idx_habilidad = len(p1.habilidades)

    p1.teletransportar_a(5)
    p2.teletransportar_a(50)

    resultado = juego_combate.usar_habilidad_jugador(
        p1.nombre, idx_habilidad, objetivo=p2.nombre
    )

    assert resultado["exito"] is True
    assert p1.get_posicion() == 50
    assert p2.get_posicion() == 5


def test_invisibilidad_proteccion(juego_combate):
    atacante = juego_combate.jugadores[0]
    defensor = juego_combate.jugadores[2]  # Ingeniero tiene invisibilidad

    # efensor activa invisibilidad
    invis = next(h for h in defensor.habilidades if h.nombre == "Invisibilidad")
    juego_combate.usar_habilidad_jugador(
        defensor.nombre, defensor.habilidades.index(invis) + 1
    )

    assert any(e["tipo"] == "invisible" for e in defensor.efectos_activos)

    # Atacante intenta usar Sabotaje
    sabotaje = next(h for h in atacante.habilidades if h.nombre == "Sabotaje")
    resultado = juego_combate.usar_habilidad_jugador(
        atacante.nombre,
        atacante.habilidades.index(sabotaje) + 1,
        objetivo=defensor.nombre,
    )

    assert resultado["exito"] is False

    # En caso de fallo, el servidor devuelve el motivo en 'mensaje'
    mensaje_respuesta = resultado.get("mensaje", "")
    assert "protegido" in mensaje_respuesta or "Invisible" in mensaje_respuesta

    # Verificar que NO se aplicó la pausa
    tiene_pausa = any(e["tipo"] == "pausa" for e in defensor.efectos_activos)
    assert tiene_pausa is False
