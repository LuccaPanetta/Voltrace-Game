# ===================================================================
# ADAPTADOR PARA MACHINE LEARNING - VOLTRACE (src/core/ml_adapter.py)
# ===================================================================


class VoltraceMLAdapter:
    def __init__(self, juego):
        self.juego = juego
        self.meta = 75.0  # Posición de la meta
        self.energia_max_ref = 1000.0  # Referencia para normalizar la energía
        self.pm_max_ref = 20.0  # Referencia para normalizar los Puntos de Mejora

    def obtener_estado_vectorial(self, nombre_bot):
        """
        Convierte el estado actual del juego en una lista plana de números (floats)
        normalizados entre 0.0 y 1.0 para que el modelo predictivo lo procese.
        """
        bot = self.juego._encontrar_jugador(nombre_bot)
        if not bot or not bot.esta_activo():
            return None

        estado = []

        # --- 1. DATOS DEL BOT ---
        # Normalizamos la posición, energía y PM dividiendo por sus máximos esperados
        estado.append(bot.get_posicion() / self.meta)
        estado.append(bot.get_puntaje() / self.energia_max_ref)
        estado.append(bot.get_pm() / self.pm_max_ref)

        # Estado de sus habilidades (1.0 = Lista para usar, 0.0 = En cooldown)
        for hab in bot.habilidades:
            cd = bot.habilidades_cooldown.get(hab.nombre, 0)
            estado.append(1.0 if cd == 0 else 0.0)

        # Rellenamos con ceros si el bot tiene menos de 4 habilidades (para mantener el tamaño del vector estático)
        faltantes = 4 - len(bot.habilidades)
        estado.extend([0.0] * faltantes)

        # --- 2. DATOS DEL RIVAL MÁS CERCANO ---
        # Filtramos a los jugadores que no son el bot y siguen vivos
        rivales = [j for j in self.juego.jugadores if j != bot and j.esta_activo()]

        if rivales:
            # Encontramos al rival con menor distancia absoluta
            rival_mas_cercano = min(
                rivales, key=lambda x: abs(x.get_posicion() - bot.get_posicion())
            )
            estado.append(rival_mas_cercano.get_posicion() / self.meta)
            estado.append(rival_mas_cercano.get_puntaje() / self.energia_max_ref)
        else:
            # Si no hay rivales vivos, rellenamos con ceros
            estado.extend([0.0, 0.0])

        # Devuelve un vector de exactamente 9 números (Ej: [0.12, 0.60, 0.05, 1.0, 0.0, 1.0, 1.0, 0.15, 0.58])
        return estado
