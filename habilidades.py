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
# - fun_crear_habilidades: Función que retorna un diccionario
#   organizado por categorías (ofensiva, defensiva, etc.)
#   con todas las instancias de Habilidad.
#
# ===================================================================

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
            Habilidad("Sabotaje", "ofensiva", "Haz que un jugador pierda su próximo turno", "⚔️", 6, 90), 
            Habilidad("Bomba Energética", "ofensiva", "Jugadores en ±3 posiciones pierden 75 energía", "💥", 5, 60),
            Habilidad("Robo", "ofensiva", "Roba 50-150 energía del jugador con más puntos", "🎭", 6, 65),
            Habilidad("Tsunami", "ofensiva", "Empuja a todos los jugadores 3 casillas atrás", "🌊", 5, 50),
            Habilidad("Fuga de Energía", "ofensiva", "El oponente pierde 25 E al inicio de sus próximos 3 turnos.", "🩸", 5, 35)
        ],
        "defensiva": [
            Habilidad("Escudo Total", "defensiva", "Inmune a todo tipo de daño por 3 rondas", "🛡️", 7, 80),
            Habilidad("Curación", "defensiva", "Recupera 150 de energía instantáneamente", "🏥", 6, 70), 
            Habilidad("Invisibilidad", "defensiva", "No te afectan las habilidades de los oponentes por 2 turnos", "👻", 5, 50),
            Habilidad("Barrera", "defensiva", "Refleja el próximo ataque que recibas por 2 turnos", "🔮", 5, 45),
            Habilidad("Transferencia de Fase", "defensiva", "Intangible e inmune a casillas negativas en tu próximo movimiento de dado", "💨", 4, 25),
            Habilidad("Traspaso de Dolor", "defensiva", "El 50% del daño recibido en tu próximo turno es redirigido a tu objetivo Vinculado.", "💔", 4, 50),
        ],
        "movimiento": [
            Habilidad("Cohete", "movimiento", "Avanza inmediatamente 3-7 casillas", "🚀", 5, 40),
            Habilidad("Intercambio Forzado", "movimiento", "Intercambias posición con cualquier jugador", "🔄", 6, 75),
            Habilidad("Retroceso", "movimiento", "Haz que un jugador retroceda 5 casillas", "⏪", 4, 40),
            Habilidad("Rebote Controlado", "movimiento", "Retrocede 2 casillas, luego avanza 9 casillas", "↩️", 5, 45),
        ],
        "control": [
            Habilidad("Dado Perfecto", "control", "Eliges exactamente cuánto avanzar (1-6)", "🎯", 5, 40), 
            Habilidad("Mina de Energía", "control", "Permite al jugador colocar una trampa en la casilla exacta donde se encuentra actualmente.", "💣", 4, 35),
            Habilidad("Doble Turno", "control", "Tirás el doble de dados", "⚡", 7, 100), 
            Habilidad("Caos", "control", "Todos los jugadores se mueven aleatoriamente", "🎪", 6, 50), 
            Habilidad("Bloqueo Energético", "control", "Impide que un oponente gane energía por 2 rondas", "🚫", 5, 55),
            Habilidad("Sobrecarga Inestable", "control", "Apuesta tu energía. Próximo turno: 33% pierdes 25E, 33% ganas 75E, 33% ganas 150E.", "🎲", 4, 50),
            Habilidad("Hilos Espectrales", "control", "Aplica 'Vínculo' a un jugador (4 turnos) en un rango de 6 casillas.", "🔗", 0, 30),
            Habilidad("Tirón de Cadenas", "control", "Tira del jugador Vinculado 3 casillas hacia ti.", "⛓️", 2, 40),
            Habilidad("Control Total", "control", "Eliges el dado (1-6) y movimiento del jugador Vinculado en su próximo turno.", "🎮", 7, 120),
        ],
    }

# ===================================================================
# --- 5. DEFINICIÓN DE KITS DE HABILIDADES ---
# ===================================================================
#
# Define los 5 kits únicos del juego.
# La lógica del juego leerá esto para asignar habilidades.
#
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