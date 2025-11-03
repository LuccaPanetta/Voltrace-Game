# ===================================================================
# CONFIGURACIÓN DE PERKS - VOLTRACE (perks.py)
# ===================================================================
#
# Este archivo define la configuración de todos los perks (habilidades pasivas)
# disponibles en el juego.
#
# Contiene:
# - PERKS_CONFIG: Un diccionario principal que mapea IDs de perks
#   a sus datos (nombre, tier, descripción, requisitos).
# - Funciones de utilidad:
#   - obtener_perk_por_id: Para buscar un perk específico.
#   - obtener_perks_por_tier: Para filtrar perks por su tier (básico, medio, alto).
#
# ===================================================================

PERKS_CONFIG = {
    # === TIER BÁSICO ===
    "recarga_constante": {
        "id": "recarga_constante",
        "nombre": "Recarga Constante",
        "tier": "basico",
        "desc": "Ganas +10 de energía al inicio de cada uno de tus turnos."
    },
    "recompensa_de_mina": {
        "id": "recompensa_de_mina",
        "nombre": "Recompensa de Mina",
        "tier": "basico",
        "desc": "Si un oponente cae en tu Mina de Energía (💣), ganas la mitad de la energía que pierden.",
        "requires_habilidad": "Mina de Energía" 
    },
    "impulso_inestable": {
        "id": "impulso_inestable",
        "nombre": "Impulso Inestable",
        "tier": "basico",
        "desc": "Tras tirar dado, 50% de +1 casilla, 50% de -1 casilla."
    },
    "chatarrero": {
        "id": "chatarrero",
        "nombre": "Chatarrero",
        "tier": "basico",
        "desc": "Ganas +1 PM al caer en Trampa o recoger pack negativo."
    },
    "presencia_intimidante": {
        "id": "presencia_intimidante",
        "nombre": "Presencia Intimidante",
        "tier": "basico",
        "desc": "Jugadores que colisionan contigo (cuando tú no te mueves) pierden 10 energía extra."
    },
    "descuento_habilidad": {
        "id": "descuento_habilidad",
        "nombre": "Descuento en Habilidad",
        "tier": "basico",
        "desc": "Una de tus habilidades (al azar) tiene su cooldown reducido en 1 turno adicional."

    },
    "maremoto": {
        "id": "maremoto",
        "nombre": "Maremoto",
        "tier": "basico",
        "desc": "Si tienes 'Tsunami', empuja 5 casillas atrás (vs 3).",
        "requires_habilidad": "Tsunami" 
    },
    "acumulador_de_pm": {
        "id": "acumulador_de_pm",
        "nombre": "Acumulador de PM",
        "tier": "basico",
        "desc": "Ganas +1 PM adicional cada vez que obtienes PM de cualquier fuente."
    },
    "retroceso_brutal": {
        "id": "retroceso_brutal",
        "nombre": "Retroceso Brutal",
        "tier": "basico",
        "desc": "Si tienes 'Retroceso', empuja 7 casillas atrás (vs 5).",
        "requires_habilidad": "Retroceso" 
    },

    # === TIER MEDIO ===
    "aislamiento": {
        "id": "aislamiento",
        "nombre": "Aislamiento",
        "tier": "medio",
        "desc": "Pierdes un 20% menos de energía por trampas y packs negativos."
    },
    "amortiguacion": {
        "id": "amortiguacion",
        "nombre": "Amortiguación",
        "tier": "medio",
        "desc": "Reduce la energía perdida por colisiones en un 33% (pierdes 67 vs 100)."
    },
    "eficiencia_energetica": {
        "id": "eficiencia_energetica",
        "nombre": "Eficiencia Energética",
        "tier": "medio",
        "desc": "Recoges un 20% más de energía de los packs positivos."
    },
    "anticipacion": {
        "id": "anticipacion",
        "nombre": "Anticipación",
        "tier": "medio",
        "desc": "Tienes un 20% de probabilidad de esquivar habilidad ofensiva enemiga."
    },
    "robo_oportunista": {
        "id": "robo_oportunista",
        "nombre": "Robo Oportunista",
        "tier": "medio",
        "desc": "Si tienes 'Robo', roba +30 de energía adicional (80-180 vs 50-150).",
        "requires_habilidad": "Robo" 
    },
    "escudo_duradero": {
        "id": "escudo_duradero",
        "nombre": "Escudo Duradero",
        "tier": "medio",
        "desc": "Si tienes 'Escudo Total', dura 1 turno adicional (4 total).",
        "requires_habilidad": "Escudo Total"
    },
     "bomba_fragmentacion": {
        "id": "bomba_fragmentacion",
        "nombre": "Bomba de Fragmentación",
        "tier": "medio",
        "desc": "Si tienes 'Bomba Energética', su rango aumenta de 3 a 5 casillas y, además del daño, empuja a los afectados 1 casilla.",
        "requires_habilidad": "Bomba Energética" 
    },
    "sombra_fugaz": {
        "id": "sombra_fugaz",
        "nombre": "Sombra Fugaz",
        "tier": "medio",
        "desc": "Si tienes 'Invisibilidad', no causas ni te afectan las colisiones.",
        "requires_habilidad": "Invisibilidad" 
    },
    "dado_cargado": {
        "id": "dado_cargado",
        "nombre": "Dado Cargado",
        "tier": "medio",
        "desc": "Si tienes 'Dado Perfecto': eligiendo 1-3 ganas +10 energía, eligiendo 4-6 ganas +1 PM.",
        "requires_habilidad": "Dado Perfecto"
    },
    "desvio_cinetico": {
        "id": "desvio_cinetico",
        "nombre": "Desvío Cinético",
        "tier": "medio",
        "desc": "Reduce a la mitad (redondeado hacia abajo) el movimiento forzado por habilidades de oponentes."
    },
    "maestro_del_azar": {
        "id": "maestro_del_azar",
        "nombre": "Maestro del Azar",
        "tier": "medio",
        "desc": "Si tienes 'Caos', tú te mueves el doble de tu resultado aleatorio.",
        "requires_habilidad": "Caos" 
    },

    # === TIER ALTO ===
    "maestria_habilidad": {
        "id": "maestria_habilidad",
        "nombre": "Maestría de Habilidad",
        "tier": "alto",
        "desc": "Ganas +2 PM extra al usar una habilidad con éxito."
    },
    "ultimo_aliento": {
        "id": "ultimo_aliento",
        "nombre": "Último Aliento",
        "tier": "alto",
        "desc": "Al llegar a 0 E por primera vez, sobrevive con 50 E y gana Escudo Total (3 rondas)."
    },
    "enfriamiento_rapido": {
        "id": "enfriamiento_rapido",
        "nombre": "Enfriamiento Rápido",
        "tier": "alto",
        "desc": "Reduce el cooldown base de todas tus habilidades en 1 turno (mínimo 1)."
    },
    "drenaje_colision": {
        "id": "drenaje_colision",
        "nombre": "Drenaje por Colisión",
        "tier": "alto",
        "desc": "Cuando colisionas, robas 50 energía a cada otro jugador involucrado."
    },
    "sabotaje_persistente": {
        "id": "sabotaje_persistente",
        "nombre": "Sabotaje Persistente",
        "tier": "alto",
        "desc": "Si tienes 'Sabotaje', hace que el objetivo pierda 2 turnos (vs 1).",
        "requires_habilidad": "Sabotaje" 
    }
}

def obtener_perk_por_id(perk_id):
    return PERKS_CONFIG.get(perk_id)

def obtener_perks_por_tier(tier):
    return [pid for pid, pdata in PERKS_CONFIG.items() if pdata["tier"] == tier]