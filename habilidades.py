# ===================================================================
# CONFIGURACIÓN DE HABILIDADES - VOLTRACE (habilidades.py)
# ===================================================================
#
# Este archivo define la estructura de datos para todas las
# habilidades activas disponibles en el juego.
#
# Contiene:
# - Clase Habilidad: La plantilla base para cada habilidad (nombre, tipo,
#   descripción, símbolo, cooldown_base, energia_coste).
# - crear_habilidades: Función que retorna un diccionario
#   organizado por categorías (ofensiva, defensiva, etc.)
#   con todas las instancias de Habilidad, usando constantes de configuración.
#
# ===================================================================

from game_config import (
    COSTO_SABOTAJE, COSTO_BOMBA, COSTO_ROBO, COSTO_TSUNAMI, COSTO_FUGA,
    COSTO_ESCUDO, COSTO_CURACION, COSTO_INVISIBILIDAD, COSTO_BARRERA,
    COSTO_FASE, COSTO_TRASPASO, COSTO_COHETE, COSTO_INTERCAMBIO,
    COSTO_RETROCESO, COSTO_REBOTE, COSTO_DADO_PERFECTO, COSTO_MINA,
    COSTO_DOBLE_TURNO, COSTO_CAOS, COSTO_BLOQUEO, COSTO_SOBRECARGA,
    COSTO_TIRON, COSTO_CONTROL_TOTAL
)

class Habilidad:
    def __init__(self, nombre, tipo, descripcion, simbolo, cooldown_base, energia_coste): 
        self.nombre = nombre
        self.tipo = tipo
        self.descripcion = descripcion
        self.simbolo = simbolo
        self.cooldown_base = cooldown_base 
        self.energia_coste = energia_coste
        self.cooldown = 0

def crear_habilidades():
    return {
        "ofensiva": [
            Habilidad("Sabotaje", "ofensiva", "Haz que un jugador pierda su próximo turno", "⚔️", 6, COSTO_SABOTAJE), 
            Habilidad("Bomba Energética", "ofensiva", "Jugadores en ±3 posiciones pierden energía", "💥", 5, COSTO_BOMBA),
            Habilidad("Robo", "ofensiva", "Roba energía del jugador con más puntos", "🎭", 6, COSTO_ROBO),
            Habilidad("Tsunami", "ofensiva", "Empuja a todos los jugadores hacia atrás", "🌊", 5, COSTO_TSUNAMI),
            Habilidad("Fuga de Energía", "ofensiva", "El oponente pierde energía al inicio de sus próximos turnos.", "🩸", 5, COSTO_FUGA)
        ],
        "defensiva": [
            Habilidad("Escudo Total", "defensiva", "Inmune a todo tipo de daño por varias rondas", "🛡️", 7, COSTO_ESCUDO),
            Habilidad("Curación", "defensiva", "Recupera energía instantáneamente", "🏥", 6, COSTO_CURACION), 
            Habilidad("Invisibilidad", "defensiva", "No te afectan las habilidades de los oponentes por 2 turnos", "👻", 5, COSTO_INVISIBILIDAD),
            Habilidad("Barrera", "defensiva", "Refleja el próximo ataque que recibas por 2 turnos", "🔮", 5, COSTO_BARRERA),
            Habilidad("Transferencia de Fase", "defensiva", "Intangible e inmune a casillas negativas en tu próximo movimiento de dado", "💨", 4, COSTO_FASE),
            Habilidad("Traspaso de Dolor", "defensiva", "El 50% del daño recibido en tus próximos turnos es redirigido a tu objetivo Vinculado.", "💔", 4, COSTO_TRASPASO),
        ],
        "movimiento": [
            Habilidad("Cohete", "movimiento", "Avanza inmediatamente varias casillas", "🚀", 5, COSTO_COHETE),
            Habilidad("Intercambio Forzado", "movimiento", "Intercambias posición con cualquier jugador", "🔄", 6, COSTO_INTERCAMBIO),
            Habilidad("Retroceso", "movimiento", "Haz que un jugador retroceda", "⏪", 4, COSTO_RETROCESO),
            Habilidad("Rebote Controlado", "movimiento", "Retrocede 2 casillas, luego avanza 9 casillas", "↩️", 5, COSTO_REBOTE),
        ],
        "control": [
            Habilidad("Dado Perfecto", "control", "Eliges exactamente cuánto avanzar (1-6)", "🎯", 5, COSTO_DADO_PERFECTO), 
            Habilidad("Mina de Energía", "control", "Coloca una trampa en tu casilla actual.", "💣", 4, COSTO_MINA),
            Habilidad("Doble Turno", "control", "Tirás el doble de dados", "⚡", 7, COSTO_DOBLE_TURNO), 
            Habilidad("Caos", "control", "Todos los jugadores se mueven aleatoriamente", "🎪", 6, COSTO_CAOS), 
            Habilidad("Bloqueo Energético", "control", "Impide que un oponente gane energía por varias rondas", "🚫", 5, COSTO_BLOQUEO),
            Habilidad("Sobrecarga Inestable", "control", "Apuesta tu energía con resultados aleatorios.", "🎲", 4, COSTO_SOBRECARGA),
            Habilidad("Hilos Espectrales", "control", "Aplica 'Vínculo' a un jugador en un rango de 10 casillas.", "🔗", 0, 0),
            Habilidad("Tirón de Cadenas", "control", "Tira del jugador Vinculado hacia ti.", "⛓️", 2, COSTO_TIRON),
            Habilidad("Control Total", "control", "Eliges el dado y movimiento del jugador Vinculado.", "🎮", 7, COSTO_CONTROL_TOTAL),
        ],
    }

# ===================================================================
# --- DEFINICIÓN DE KITS DE HABILIDADES ---
# ===================================================================

KITS_VOLTRACE = {
    "tactico": {
        "nombre": "Táctico",
        "descripcion": "Control y precisión. Débil contra daño directo, pero excelente para controlar oponentes.",
        "habilidades": ["Sabotaje", "Barrera", "Rebote Controlado", "Dado Perfecto"]
    },
    "ingeniero": {
        "nombre": "Ingeniero",
        "descripcion": "Zona y velocidad. Rápido para escapar y poner trampas.",
        "habilidades": ["Bomba Energética", "Invisibilidad", "Cohete", "Mina de Energía"]
    },
    "espectro": {
        "nombre": "Espectro",
        "descripcion": "Caos y evasión. Ignora las reglas del tablero y altera posiciones.",
        "habilidades": ["Fuga de Energía", "Transferencia de Fase", "Intercambio Forzado", "Caos"]
    },
    "guardian": {
        "nombre": "Guardián",
        "descripcion": "Anti-habilidades. Difícil de matar y castiga a quienes dependen de la energía.",
        "habilidades": ["Tsunami", "Escudo Total", "Retroceso", "Bloqueo Energético"]
    },
    "estratega": {
        "nombre": "El Estratega",
        "descripcion": "Alto riesgo, alta recompensa. Sin escape, pero gran control y tempo.",
        "habilidades": ["Robo", "Curación", "Doble Turno", "Sobrecarga Inestable"]
    },
    "marionetista": {
        "nombre": "El Titiritero",
        "descripcion": "Control a distancia. Manipula la posición y las acciones de los oponentes usando Vínculos.",
        "habilidades": ["Hilos Espectrales", "Tirón de Cadenas", "Traspaso de Dolor", "Control Total"]
    }
}