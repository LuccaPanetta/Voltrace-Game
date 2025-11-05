# ===================================================================
# CONFIGURACIÓN DE HABILIDADES - VOLTRACE (habilidades.py)
# ===================================================================
#
# Este archivo define la estructura de datos para todas las
# habilidades activas disponibles en el juego.
#
# Contiene:
# - Clase Habilidad: La plantilla base para cada habilidad (nombre, tipo,
#   descripción, símbolo, cooldown_base).
# - fun_crear_habilidades: Función que retorna un diccionario
#   organizado por categorías (ofensiva, defensiva, etc.)
#   con todas las instancias de Habilidad.
#
# ===================================================================

class Habilidad:
    def __init__(self, nombre, tipo, descripcion, simbolo, cooldown_base): 
        self.nombre = nombre
        self.tipo = tipo
        self.descripcion = descripcion
        self.simbolo = simbolo
        self.cooldown_base = cooldown_base 
        self.cooldown = 0

def crear_habilidades():
    return {
        "ofensiva": [
            Habilidad("Sabotaje", "ofensiva", "Haz que un jugador pierda su próximo turno", "⚔️", 6), 
            Habilidad("Bomba Energética", "ofensiva", "Jugadores en ±3 posiciones pierden 75 energía", "💥", 5),
            Habilidad("Robo", "ofensiva", "Roba 50-150 energía del jugador con más puntos", "🎭", 6),
            Habilidad("Tsunami", "ofensiva", "Empuja a todos los jugadores 3 casillas atrás", "🌊", 5),
            Habilidad("Fuga de Energía", "ofensiva", "El oponente pierde 25 E al inicio de sus próximos 3 turnos.", "🩸", 5)
        ],
        "defensiva": [
            Habilidad("Escudo Total", "defensiva", "Inmune a todo tipo de daño por 3 rondas", "🛡️", 7),
            Habilidad("Curación", "defensiva", "Recupera 150 de energía instantáneamente", "🏥", 6), 
            Habilidad("Invisibilidad", "defensiva", "No te afectan las habilidades de los oponentes por 2 turnos", "👻", 5),
            Habilidad("Barrera", "defensiva", "Refleja el próximo ataque que recibas por 2 turnos", "🔮", 5),
            Habilidad("Transferencia de Fase", "defensiva", "Intangible e inmune a casillas negativas en tu próximo movimiento de dado", "💨", 4),
        ],
        "movimiento": [
            Habilidad("Cohete", "movimiento", "Avanza inmediatamente 3-7 casillas", "🚀", 5),
            Habilidad("Intercambio Forzado", "movimiento", "Intercambias posición con cualquier jugador", "🔄", 6),
            Habilidad("Retroceso", "movimiento", "Haz que un jugador retroceda 5 casillas", "⏪", 4),
            Habilidad("Rebote Controlado", "movimiento", "Retrocede 2 casillas, luego avanza 9 casillas", "↩️", 5),
        ],
        "control": [
            Habilidad("Dado Perfecto", "control", "Eliges exactamente cuánto avanzar (1-6)", "🎯", 5), 
            Habilidad("Mina de Energía", "control", "Permite al jugador colocar una trampa en la casilla exacta donde se encuentra actualmente.", "💣", 4),
            Habilidad("Doble Turno", "control", "Tirás el doble de dados", "⚡", 7), 
            Habilidad("Caos", "control", "Todos los jugadores se mueven aleatoriamente", "🎪", 6), 
            Habilidad("Bloqueo Energético", "control", "Impide que un oponente gane energía por 2 rondas", "🚫", 5),
            Habilidad("Sobrecarga Inestable", "control", "Sacrifica 50 de energía ahora. Próximo turno: 33% -25E, 33% +75E, 33% +150E", "🎲", 4),
        ],
    }
