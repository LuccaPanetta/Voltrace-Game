# ===================================================================
# CLASE DEL JUGADOR - VOLTRACE (jugadores.py)
# ===================================================================
#
# Este archivo define la clase 'JugadorWeb'.
# Representa el estado de un jugador individual *dentro* de una partida.
#
# Responsabilidades:
# - Almacenar atributos (nombre, posición, puntaje, PM, perks_activos).
# - Gestionar habilidades (cooldowns, efectos_activos).
# - Métodos para modificar estado (procesar_energia, avanzar).
# - Manejar la lógica de gasto/ganancia de Puntos de Mando (PM).
# - Lógica de perks pasivos (ej. 'ultimo_aliento', 'acumulador_de_pm').
# - Serialización de su estado a un diccionario (to_dict).
#
# ===================================================================

from perks import PERKS_CONFIG

class JugadorWeb:
    def __init__(self, nombre):
        # 1. ATRIBUTOS BÁSICOS Y DE IDENTIFICACIÓN
        self.nombre = nombre
        self.__posicion = 1 
        self.__puntaje = 600
        self.__activo = True
        self.juego_actual = None
        
        # 2. SISTEMA DE HABILIDADES Y PM
        self.habilidades = []       
        self.habilidades_cooldown = {} 
        self.efectos_activos = [] 
        self.pm = 0 
        self.perks_activos = []
        self.habilidades_usadas_en_partida = 0
        self.tesoros_recogidos = 0
        self.trampas_evitadas = True
        self.dado_perfecto_usado = 0 
        self.game_messages_sent_this_match = 0 
        
        # 3. RASTREADORES DE PARTIDA (Puntuación Final)
        self.colisiones_causadas = 0
        self.tipos_casillas_visitadas = set()
        self.energy_packs_collected = 0
        
        # 4. FLAGS DE ESTADO ESPECIAL
        self.dado_forzado = None               
        self.habilidad_usada_este_turno = False 
        self.dado_lanzado_este_turno = False
        self.oferta_perk_activa = None          
        
        # 5. FLAGS DEL PERK "ÚLTIMO ALIENTO" 
        self._ultimo_aliento_usado = False
        self._ultimo_aliento_notificado = False
        
        print(f"JugadorWeb '{nombre}' inicializado.")
        
    def get_nombre(self):
        return self.nombre
    
    def limpiar_oferta_perk(self):
        self.oferta_perk_activa = None
    
    def get_posicion(self):
        return self.__posicion

    def get_puntaje(self):
        return self.__puntaje

    def esta_activo(self):
        return self.__activo
    
    def set_activo(self, estado: bool):
        self.__activo = estado
        if not estado:
            # Si se está desactivando, limpiar sus efectos
            self.efectos_activos = [] 
        print(f"DEBUG: {self.nombre} set_activo = {estado}")
    
    def avanzar(self, posiciones):
        if self.__activo:
            self.__posicion += posiciones
            
    def procesar_energia(self, cantidad):
        energia_anterior = self.__puntaje
        energia_cambiada = 0 # Inicializar cambio

        # Usar verificación directa en efectos_activos
        esta_bloqueado = any(efecto.get('tipo') == 'bloqueo_energia' for efecto in self.efectos_activos)

        if esta_bloqueado and cantidad > 0:
            print(f"DEBUG procesar_energia: {self.nombre} intentó ganar {cantidad}E pero está bloqueado.")
            # No se aplica la ganancia, el cambio es 0
            energia_cambiada = 0
            return int(energia_cambiada) # Devolver 0 porque no hubo cambio

        # Calcular energía tentativa si no está bloqueado o si pierde energía
        energia_final_calculada = energia_anterior + cantidad

        # Se activa SI la energía va a ser 0 o menos, Y el perk está activo, Y no se ha usado ya
        if energia_final_calculada <= 0 and \
        "ultimo_aliento" in self.perks_activos and \
        not getattr(self, '_ultimo_aliento_usado', False):

            print(f"DEBUG: {self.nombre} activó Último Aliento.") # Log útil
            # Marcar como usado
            self._ultimo_aliento_usado = True

            # Sobrevive con 50 de energía
            self.__puntaje = 50
            energia_cambiada = self.__puntaje - energia_anterior # Calcula el cambio real 

            # Comprobar si el perk "Escudo Duradero" debe extender el escudo de "Último Aliento"
            rondas_escudo = 3 # Rondas base de Último Aliento
            
            if "escudo_duradero" in self.perks_activos:
                rondas_escudo += 1 # El perk añade 1 ronda
                print(f"DEBUG: Último Aliento activado CON Escudo Duradero (Total {rondas_escudo} rondas).")
            
            turnos_escudo = 3 # Fallback por si acaso
            if self.juego_actual and self.juego_actual.jugadores:
                # Calcular turnos totales basados en las rondas 
                turnos_escudo = len(self.juego_actual.jugadores) * rondas_escudo
            
            print(f"DEBUG: Último Aliento aplicando Escudo por {turnos_escudo} turnos ({rondas_escudo} rondas).")
            self.efectos_activos.append({"tipo": "escudo", "turnos": turnos_escudo})

            return int(energia_cambiada) # Devolver el cambio real

        self.__puntaje = max(0, energia_final_calculada) # Aplicar cambio y asegurar que no sea < 0
        energia_cambiada = self.__puntaje - energia_anterior # Calcular cambio real

        if self.__puntaje <= 0 and self.__activo:
            print(f"DEBUG: {self.nombre} eliminado (Energía: {self.__puntaje}).") # Log útil
            self.__activo = False

        # Devolver siempre un entero representando el cambio neto de energía
        return int(energia_cambiada)
    
    def retroceder_a(self, posicion):
        if self.__activo and posicion >= 0:
            self.__posicion = posicion
    
    def teletransportar_a(self, posicion):
        if self.__activo:
            self.__posicion = max(1, min(posicion, 75))
    
    def get_pm(self):
        return self.pm

    def ganar_pm(self, cantidad):
        if not self.__activo or cantidad <= 0: return
        cantidad_final = cantidad
        if "acumulador_de_pm" in self.perks_activos:
            cantidad_final += 1
            self.juego_actual.eventos_turno.append(f"✨ Acumulador: +1 PM extra para {self.get_nombre()}")
        self.pm += cantidad_final
        print(f"DEBUG: {self.get_nombre()} ganó {cantidad_final} PM. Total: {self.pm}")

    def gastar_pm(self, cantidad):
        print(f"DEBUG gastar_pm: Intentando gastar {cantidad} PM. Actuales: {self.pm}")
        if self.pm >= cantidad: 
            self.pm -= cantidad
            print(f"DEBUG gastar_pm: Gasto exitoso. PM restantes: {self.pm}")
            return True
        else:
            print(f"DEBUG gastar_pm: Fondos insuficientes.") 
            return False
    
    def reducir_cooldowns(self, turnos=1):
        if not self.__activo: return # No reducir si está eliminado

        for nombre_habilidad in list(self.habilidades_cooldown.keys()):
            if self.habilidades_cooldown[nombre_habilidad] > 0:
                self.habilidades_cooldown[nombre_habilidad] -= turnos 
                self.habilidades_cooldown[nombre_habilidad] = max(0, self.habilidades_cooldown[nombre_habilidad])

    def poner_en_cooldown(self, habilidad, tiene_perk_enfriamiento_rapido):
        cooldown_final = habilidad.cooldown_base

        # 1. Aplicar Perk "Enfriamiento Rápido" 
        if tiene_perk_enfriamiento_rapido:
            cooldown_final = max(1, cooldown_final - 1) # Reducir en 1, mínimo 1

        # 2. Aplicar Perk "Descuento en Habilidad" 
        perk_descuento_id = f"descuento_{habilidad.nombre.lower().replace(' ', '_')}"
        if perk_descuento_id in self.perks_activos:
            cooldown_final = max(1, cooldown_final - 1) # Reducir 1 ADICIONAL, mínimo 1
            print(f"DEBUG: Aplicando Descuento Específico a {habilidad.nombre}") 

        # Asignar cooldown final calculado
        self.habilidades_cooldown[habilidad.nombre] = cooldown_final

    def to_dict(self):
        return {
            'nombre': self.nombre, 
            'posicion': self.__posicion,
            'puntaje': self.__puntaje,
            'activo': self.__activo,
            'habilidades': [
                {
                    'nombre': h.nombre,
                    'tipo': h.tipo,
                    'descripcion': h.descripcion,
                    'simbolo': h.simbolo,
                    'cooldown': self.habilidades_cooldown.get(h.nombre, 0)
                } for h in self.habilidades
            ],
            'efectos_activos': self.efectos_activos,
            'pm': self.pm, 
            'perks_activos': self.perks_activos
        }
    
    def reset_turn_flags(self):
        self.habilidad_usada_este_turno = False
        self.dado_lanzado_este_turno = False
        