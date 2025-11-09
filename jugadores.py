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
        # ATRIBUTOS BÁSICOS Y DE IDENTIFICACIÓN
        self.nombre = nombre
        self.avatar_emoji = '👤'
        self.__posicion = 1 
        self.__puntaje = 600
        self.__activo = True
        self.juego_actual = None
        self.es_caza = False
        self.recompensa_reclamada = False
        
        # SISTEMA DE HABILIDADES Y PM
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
        
        # RASTREADORES DE PARTIDA (Puntuación Final)
        self.colisiones_causadas = 0
        self.tipos_casillas_visitadas = set()
        self.energy_packs_collected = 0
        
        # FLAGS DE ESTADO ESPECIAL
        self.dado_forzado = None               
        self.habilidad_usada_este_turno = False 
        self.dado_lanzado_este_turno = False
        self.oferta_perk_activa = None          
        
        # FLAGS DEL PERK "ÚLTIMO ALIENTO" 
        self._ultimo_aliento_usado = False
        self._ultimo_aliento_notificado = False

        #RASTREADORES DE LOGROS
        self.consecutive_sixes = 0
        
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

        # --- BLOQUE DE PROTECCIÓN (ESCUDO) ---
        if cantidad < 0:
            if any(efecto.get('tipo') == 'escudo' for efecto in self.efectos_activos):
                print(f"DEBUG procesar_energia: {self.nombre} bloqueó {cantidad}E de daño con Escudo.")
                
                # Asegurarse de que juego_actual y eventos_turno existan antes de añadir el evento
                if self.juego_actual and hasattr(self.juego_actual, 'eventos_turno'):
                    self.juego_actual.eventos_turno.append(f"🛡️ {self.nombre} bloqueó {abs(cantidad)} de daño con Escudo.")
                return 0 # No se aplica daño

        if cantidad < 0: # Solo se activa al RECIBIR daño 
            efecto_traspaso = next((efecto for efecto in self.efectos_activos if efecto.get('tipo') == 'traspaso_dolor'), None)
            
            if efecto_traspaso:
                print(f"DEBUG: {self.nombre} tiene Traspaso de Dolor activo.")
                nombre_objetivo = efecto_traspaso.get("objetivo")
                objetivo = self.juego_actual._encontrar_jugador(nombre_objetivo) if self.juego_actual else None
                
                if objetivo and objetivo.esta_activo() and objetivo != self:
                    # Calcular daño a transferir (50% del daño recibido)
                    dano_transferido = int(cantidad * 0.5) # cantidad ya es negativa
                    
                    if self.juego_actual and hasattr(self.juego_actual, 'eventos_turno'):
                        self.juego_actual.eventos_turno.append(f"💔 ¡Traspaso de Dolor! {self.nombre} redirige {abs(dano_transferido)}E de daño a {objetivo.get_nombre()}.")
                    
                    # Aplicar el daño al objetivo.
                    objetivo.procesar_energia(dano_transferido)
                    
                    # Verificar si el objetivo fue eliminado por el traspaso
                    if not objetivo.esta_activo():
                        mensaje_elim = f"💀 ¡{objetivo.get_nombre()} ha sido eliminado por Traspaso de Dolor!"
                        if self.juego_actual and mensaje_elim not in self.juego_actual.eventos_turno:
                            self.juego_actual.eventos_turno.append(mensaje_elim)
                    # Verificar si el objetivo usó Último Aliento
                    elif getattr(objetivo, '_ultimo_aliento_usado', False) and not getattr(objetivo, '_ultimo_aliento_notificado', False):
                        if self.juego_actual:
                            self.juego_actual.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {objetivo.get_nombre()}! (Daño de Traspaso)")
                        objetivo._ultimo_aliento_notificado = True
                
                # El efecto Traspaso de Dolor se consume después de un uso
                self.efectos_activos = [e for e in self.efectos_activos if e.get('tipo') != 'traspaso_dolor']

        esta_bloqueado = any(efecto.get('tipo') == 'bloqueo_energia' for efecto in self.efectos_activos)
        if esta_bloqueado and cantidad > 0:
            print(f"DEBUG procesar_energia: {self.nombre} intentó ganar {cantidad}E pero está bloqueado.")
            return 0 # No se aplica la ganancia

        energia_final_calculada = energia_anterior + cantidad

        if energia_final_calculada <= 0 and \
           "ultimo_aliento" in self.perks_activos and \
           not getattr(self, '_ultimo_aliento_usado', False):

            print(f"DEBUG: {self.nombre} activó Último Aliento.")
            self._ultimo_aliento_usado = True
            self.__puntaje = 50
            energia_cambiada = self.__puntaje - energia_anterior 

            rondas_escudo = 3 
            if "escudo_duradero" in self.perks_activos:
                rondas_escudo += 1
                print(f"DEBUG: Último Aliento activado CON Escudo Duradero (Total {rondas_escudo} rondas).")
            
            turnos_escudo = 3 
            if self.juego_actual and self.juego_actual.jugadores:
                turnos_escudo = len(self.juego_actual.jugadores) * rondas_escudo
            
            print(f"DEBUG: Último Aliento aplicando Escudo por {turnos_escudo} turnos ({rondas_escudo} rondas).")
            self.efectos_activos.append({"tipo": "escudo", "turnos": turnos_escudo})

            return int(energia_cambiada) 

        self.__puntaje = max(0, energia_final_calculada) 
        energia_cambiada = self.__puntaje - energia_anterior 

        if self.__puntaje <= 0 and self.__activo:
            print(f"DEBUG: {self.nombre} eliminado (Energía: {self.__puntaje}).")
            self.__activo = False

        return int(energia_cambiada)
    
    def retroceder_a(self, posicion):
        if self.__activo and posicion >= 0:
            self.__posicion = posicion
    
    def teletransportar_a(self, posicion):
        if self.__activo:
            self.__posicion = max(1, min(posicion, 75))
    
    def get_pm(self):
        return self.pm

    def ganar_pm(self, cantidad, fuente="habilidad"):
        if not self.__activo or cantidad <= 0: return
        cantidad_final = cantidad
        
        fuentes_especiales_pm = ["casilla_pozo_pm", "casilla_chatarreria", "perk_chatarrero"]
        if "acumulador_de_pm" in self.perks_activos and fuente in fuentes_especiales_pm:
            cantidad_final += 1
            self.juego_actual.eventos_turno.append(f"✨ Acumulador: +1 PM extra para {self.get_nombre()}")
            
        self.pm += cantidad_final
        print(f"DEBUG: {self.get_nombre()} ganó {cantidad_final} PM (Fuente: {fuente}). Total: {self.pm}")

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
            'avatar_emoji': self.avatar_emoji,
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
            'perks_activos': self.perks_activos,
            'es_caza': self.es_caza,
            'recompensa_reclamada': self.recompensa_reclamada
        }
    
    def reset_turn_flags(self):
        self.habilidad_usada_este_turno = False
        self.dado_lanzado_este_turno = False
        