# ===================================================================
# LÓGICA CENTRAL DEL JUEGO - VOLTRACE (juego_web.py)
# ===================================================================
#
# Este archivo define la clase 'JuegoOcaWeb', que encapsula toda la
# lógica y el estado de una partida individual.
#
# Responsabilidades principales:
# - Inicialización del tablero, jugadores y habilidades.
# - Procesamiento del flujo de turnos (lanzar dado, mover jugador).
# - Activación de casillas especiales y packs de energía.
# - Manejo de colisiones entre jugadores.
# - Lógica de uso de habilidades (todos los métodos '_hab_*').
# - Sistema de perks (compra, selección y activación de efectos).
# - Gestión de eventos globales (Apagón, Sobrecarga, etc.).
# - Determinación del ganador y cálculo de puntajes finales.
#
# ===================================================================

from random import randint, choice, sample
import random
import os
import traceback
from habilidades import Habilidad, crear_habilidades
from perks import PERKS_CONFIG, obtener_perks_por_tier
from jugadores import JugadorWeb
from random import randint, choice, sample
import random
import os
import traceback
from habilidades import Habilidad, crear_habilidades
from perks import PERKS_CONFIG, obtener_perks_por_tier
from jugadores import JugadorWeb

class JuegoOcaWeb:

    # ===================================================================
    # --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
    # ===================================================================
    
    def __init__(self, nombres_jugadores):
        self.jugadores = [JugadorWeb(nombre) for nombre in nombres_jugadores]
        for jugador in self.jugadores:
            jugador.juego_actual = self
        self.posicion_meta = 75
        self.energia_packs = []
        self.perks_ofrecidos = {nombre: set() for nombre in nombres_jugadores} # Para evitar ofrecer el mismo perk varias veces
        self.casillas_especiales = {}
        self.habilidades_disponibles = crear_habilidades()
        self.ronda = 1
        self.turno_actual = 0
        self.fin_juego = False
        self.eventos_turno = []
        self.evento_global_activo = None 
        self.evento_global_duracion = 0
        
        print(f"--- JuegoOcaWeb __init__ --- Jugadores: {nombres_jugadores}")
        print(f"--- JuegoOcaWeb __init__ --- Turno inicial: {self.turno_actual}")

        self._crear_casillas_especiales()
        self._cargar_energia_desde_archivo()
        self._asignar_habilidades_jugadores()

    def _crear_casillas_especiales(self):
        from random import sample, choice # Asegurarse de que están importados
    
        print("--- Creando tablero aleatorio (Casillas Únicas) ---")
        self.casillas_especiales = {}
        
        # 1. DEFINE EL "POOL" DE CASILLAS POSIBLES (CON ATRIBUTO 'ID_UNICO')
        # Añadimos un ID_UNICO para distinguir tipos de efectos (ej. Tesoro Menor vs Tesoro Mayor)
        POOL_DE_CASILLAS = [
            {"tipo": "tesoro", "simbolo": "$", "valor": 70, "nombre": "Tesoro Menor", "id_unico": "tesoro_menor"},
            {"tipo": "trampa", "simbolo": "X", "valor": -60, "nombre": "Trampa de Energía", "id_unico": "trampa_energia"},
            {"tipo": "teletransporte", "simbolo": "T", "avance": (3, 5), "nombre": "Portal Mágico", "id_unico": "portal_magico"},
            {"tipo": "multiplicador", "simbolo": "*2", "nombre": "Amplificador", "id_unico": "amplificador"},
            {"tipo": "intercambio", "simbolo": "S", "nombre": "Cámara de Intercambio", "id_unico": "intercambio"},
            {"tipo": "tesoro", "simbolo": "$$", "valor": 120, "nombre": "Tesoro Mayor", "id_unico": "tesoro_mayor"},
            {"tipo": "pausa", "simbolo": "P", "nombre": "Zona de Pausa", "id_unico": "pausa"},
            {"tipo": "trampa", "simbolo": "XX", "valor": -80, "nombre": "Trampa Peligrosa", "id_unico": "trampa_peligrosa"},
            {"tipo": "turbo", "simbolo": "!", "nombre": "Acelerador", "id_unico": "acelerador"},
            {"tipo": "teletransporte", "simbolo": "T+", "avance": (4, 6), "nombre": "Portal Avanzado", "id_unico": "portal_avanzado"},
            {"tipo": "vampiro", "simbolo": "V", "porcentaje": 10, "nombre": "Drenaje de Energía", "id_unico": "vampiro"},
            {"tipo": "rebote", "simbolo": "R", "nombre": "Trampolín Inverso", "id_unico": "rebote"},
            {"tipo": "retroceso_estrategico", "simbolo": "⚫", "nombre": "Agujero Negro", "id_unico": "agujero_negro"},
            {"tipo": "recurso", "simbolo": "⭐", "nombre": "Pozo de PM", "id_unico": "pozo_pm"},
            {"tipo": "atraccion", "simbolo": "🧲", "nombre": "Imán", "id_unico": "iman"},
            {"tipo": "intercambio_recurso", "simbolo": "⚙️", "nombre": "Chatarrería", "id_unico": "chatarreria"},
        ]

        # 2. DEFINE LAS POSICIONES VÁLIDAS
        posiciones_validas = list(range(4, self.posicion_meta - 1)) # De la 4 a la 73

        # 3. DEFINE CUÁNTAS CASILLAS QUIERES Y CUÁNTOS TIPOS ÚNICOS MÁXIMO
        CANTIDAD_ESPECIALES = 20  
        MAX_TIPOS_UNICOS = len(POOL_DE_CASILLAS) # Máximo 16 tipos únicos
        
        # 4. SELECCIONAR QUÉ TIPOS DE CASILLAS VAMOS A USAR
        # Seleccionar una lista de IDs únicos para garantizar la diversidad
        pool_ids_unicos = [c["id_unico"] for c in POOL_DE_CASILLAS]
        
        # Seleccionar al azar los tipos de casillas que usaremos, limitado por CANTIDAD_ESPECIALES
        tipos_a_usar_ids = sample(pool_ids_unicos, min(CANTIDAD_ESPECIALES, MAX_TIPOS_UNICOS))

        # Crear un mapa de configuración basado solo en los IDs seleccionados
        tipos_config = {c["id_unico"]: c for c in POOL_DE_CASILLAS}
        
        # Lista final de casillas, priorizando la unicidad
        casillas_seleccionadas = []
        
        # 5. Llenar con los tipos únicos (Garantiza que el juego tenga un poco de todo)
        for unique_id in tipos_a_usar_ids:
            casillas_seleccionadas.append(tipos_config[unique_id])

        # 6. Llenar el resto de las ranuras con tipos al azar (sin forzar unicidad de tipo, solo de ID)
        while len(casillas_seleccionadas) < CANTIDAD_ESPECIALES:
            casillas_seleccionadas.append(choice(POOL_DE_CASILLAS))

        # 7. SELECCIONAR POSICIONES AL AZAR Y ASIGNAR CASILLAS
        posiciones_elegidas = sample(posiciones_validas, CANTIDAD_ESPECIALES)

        for pos, casilla_data in zip(posiciones_elegidas, casillas_seleccionadas):
            # Usamos .copy() para evitar que una modificación posterior afecte al POOL original
            self.casillas_especiales[pos] = casilla_data.copy() 
        
        print(f"Tablero creado con {len(self.casillas_especiales)} casillas aleatorias únicas.")

    def _cargar_energia_desde_archivo(self, nombre_archivo="packenergia_75.txt"):
        ruta_archivo = os.path.join(os.path.dirname(__file__), 'data', nombre_archivo)
        self.energia_packs = []
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                for linea in archivo:
                    linea = linea.strip()
                    if linea:
                        try:
                            nombre, posicion, valor = linea.split(',')
                            self.energia_packs.append({
                                'nombre': nombre.strip(),
                                'posicion': int(posicion.strip()),
                                'valor': int(valor.strip())
                            })
                        except ValueError:
                            # Ignorar líneas malformadas en modo web para robustez
                            pass
        except FileNotFoundError:
            # Fallback a packs por defecto si no existe el archivo
            packs_data = [
                (3, 70), (7, -30), (12, 80), (16, 50), (19, -40), (23, 90), (27, -50),
                (31, 60), (34, 120), (38, -60), (42, 80), (45, -70), (48, 100), (52, 70),
                (55, -80), (58, 110), (61, -40), (64, 90), (67, -90), (70, 150), (73, -100)
            ]
            self.energia_packs = [
                {"nombre": f"Pack_{i+1}", "posicion": pos, "valor": val}
                for i, (pos, val) in enumerate(packs_data)
            ]
    
    def _asignar_habilidades_jugadores(self):
        habilidades_usadas = []
        
        for jugador in self.jugadores:
            jugador.habilidades = []
            
            for categoria in ["ofensiva", "defensiva", "movimiento", "control"]:
                habilidades_disponibles = [h for h in self.habilidades_disponibles[categoria] 
                                          if h.nombre not in habilidades_usadas]
                
                if habilidades_disponibles:
                    habilidad_elegida = choice(habilidades_disponibles)
                    jugador.habilidades.append(habilidad_elegida)
                    habilidades_usadas.append(habilidad_elegida.nombre)

        for jugador in self.jugadores:
            jugador.habilidades_cooldown = {h.nombre: 0 for h in jugador.habilidades}

    # ===================================================================
    # --- 2. FLUJO PRINCIPAL DEL JUEGO (EL TURNO) ---
    # ===================================================================

    def ejecutar_turno_dado(self, nombre_jugador):
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador:
            return {"exito": False, "mensaje": "Jugador no encontrado"}
        
        # 1. Procesar Cooldowns, Descuento de Perk y Recarga de Energía (con notificación)
        eventos_inicio_turno = self._procesar_inicio_turno(jugador)
        self.eventos_turno = [] # Limpiar eventos antes de añadir los nuevos
        self.eventos_turno.extend(eventos_inicio_turno)
        
        if jugador.oferta_perk_activa:
            self.eventos_turno.append(f"⚠️ {nombre_jugador} debe elegir un perk antes de lanzar el dado.")
            return {"exito": False, "mensaje": "Debes elegir un perk de la oferta pendiente antes de lanzar el dado.", "oferta_pendiente": True}

        # 2. Verificar si está pausado
        if self._verificar_efecto_activo(jugador, "pausa"):
            self.eventos_turno.append(f"⏸️ {nombre_jugador} pierde su turno por estar pausado")
            self._reducir_efectos_temporales(jugador) # Consume el turno de pausa
            self._avanzar_turno()
            return {"exito": True, "eventos": self.eventos_turno, "pausado": True}

        # 3. Lógica del Dado (Normal, Doble Turno o Dado Perfecto)
        # Verificar si "Doble Turno" (doble_dado) está activo
        es_doble_dado = self._verificar_efecto_activo(jugador, "doble_dado")
        
        if hasattr(jugador, 'dado_forzado') and jugador.dado_forzado:
            dado1 = jugador.dado_forzado
            jugador.dado_forzado = None # Importante: consumir el dado
            self.eventos_turno.append(f"🎯 {nombre_jugador} usó Dado Perfecto: {dado1}")
        else:
            # Si no hay dado forzado, tirar normalmente
            dado1 = randint(1, 6)

        if es_doble_dado:
            dado2 = randint(1, 6)
            dado = dado1 + dado2 
            self.eventos_turno.append(f"🔄 ¡Doble Turno! {nombre_jugador} sacó {dado1} + {dado2} = {dado}")
        else:
            dado = dado1
            # Añadir log solo si no fue Dado Perfecto (para evitar duplicados)
            if not self.eventos_turno or "Dado Perfecto" not in self.eventos_turno[-1]:
                self.eventos_turno.append(f"{nombre_jugador} sacó {dado}")
        
        # 4. Cálculo del Avance
        # Verificar si "Turbo" (multiplicador) está activo
        multiplicador = 2 if self._verificar_efecto_activo(jugador, "turbo") else 1
        avance_total = dado * multiplicador
        
        if multiplicador > 1 and es_doble_dado:
            self.eventos_turno.append(f"⚡ ¡Turbo también! ({dado} x 2) = {avance_total} casillas")
        elif multiplicador > 1:
            self.eventos_turno.append(f"⚡ ¡Turbo activado! ({dado} x 2) = {avance_total} casillas")
        
        # Aplicar Impulso Inestable (Perk Básico)
        if "impulso_inestable" in jugador.perks_activos:
            if random.random() < 0.50:
                avance_total += 1
                self.eventos_turno.append("🌀 Impulso Inestable: +1 casilla!")
            else:
                avance_total = max(0, avance_total - 1) # No ir a posición negativa
                self.eventos_turno.append("🌀 Impulso Inestable: -1 casilla!")
        
        # 5. Mover y Verificar Meta
        jugador.avanzar(avance_total)
        nueva_pos = jugador.get_posicion()
        self.eventos_turno.append(f"{nombre_jugador} se mueve a la posición {nueva_pos}")
        
        # Verificar meta
        if nueva_pos >= self.posicion_meta:
            self.eventos_turno.append(f"🏆 ¡{nombre_jugador} llegó a la meta!")
            self.fin_juego = True
            return {"exito": True, "eventos": self.eventos_turno, "meta_alcanzada": True}
        
        # 6. Procesar Efectos y Finalizar Turno
        # Procesar efectos de la posición (packs, casillas especiales, colisiones)
        self._procesar_efectos_posicion(jugador, nueva_pos)
        
        # Reducir efectos temporales (Consume Turbo, Fase, etc.)
        self._reducir_efectos_temporales(jugador)

        # Limpiar flag de habilidad usada
        if hasattr(jugador, 'habilidad_usada_este_turno'):
            jugador.habilidad_usada_este_turno = False
        
        # 7. Avanzar Turno
        self._avanzar_turno() 
        
        return {"exito": True, "eventos": self.eventos_turno, "dado": dado, "avance": avance_total}

    def _procesar_inicio_turno(self, jugador):
        eventos = []
        reduccion_cooldown = 1
        print(f"DEBUG Procesar Inicio Turno para: {jugador.get_nombre()}") # Log 1: Entra

        # Lógica de Enfriamiento Rápido
        if "enfriamiento_rapido" in jugador.perks_activos:
            reduccion_cooldown += 1
            eventos.append("⏳ Enfriamiento Rápido: ¡Cooldowns reducidos en 1 turno extra!")

        # Aplicar la reducción de cooldowns (antes de verificar pausa)
        jugador.reducir_cooldowns(turnos=reduccion_cooldown)

        # Lógica de Recarga Constante
        if "recarga_constante" in jugador.perks_activos:
            # Llama a la función que ya tiene el bloqueo
            energia_ganada = jugador.procesar_energia(10)
            # Solo añadir evento si realmente ganó energía (no estaba bloqueado)
            if energia_ganada > 0 and jugador.get_puntaje() > 0:
                eventos.append(f"🔋 Recarga Constante: +{energia_ganada} Energía aplicada.")
            elif energia_ganada == 0:
                eventos.append(f"🚫 Recarga Constante bloqueada.")


        print(f"DEBUG Verificando efectos para {jugador.get_nombre()}: {jugador.efectos_activos}") 
        if self._verificar_efecto_activo(jugador, "sobrecarga_pendiente"):
            print(f"DEBUG ¡Efecto 'sobrecarga_pendiente' DETECTADO para {jugador.get_nombre()}!") 
            resultado_sobrecarga = random.choice([-25, 75, 150]) 
            print(f"DEBUG Resultado Sobrecarga: {resultado_sobrecarga}") 

            # Llama a procesar_energia (que ya maneja bloqueo si aplica)
            energia_cambio = jugador.procesar_energia(resultado_sobrecarga)

            # Añade evento SIEMPRE para mostrar el resultado, indicando si fue bloqueado
            if energia_cambio == 0 and resultado_sobrecarga > 0:
                 eventos.append(f"🚫🎲 Resultado Sobrecarga (+{resultado_sobrecarga}) bloqueado.")
            elif resultado_sobrecarga > 0:
                # Usa energia_cambio que es lo que realmente ganó
                eventos.append(f"🎲 Resultado Sobrecarga: ¡Ganaste {energia_cambio or 0} Energía!")
            else: # resultado_sobrecarga < 0
                # Usa resultado_sobrecarga (el valor negativo original) para abs()
                eventos.append(f"🎲 Resultado Sobrecarga: ¡Perdiste {abs(resultado_sobrecarga)} Energía!")

            # Consumir el efecto 'sobrecarga_pendiente'
            self._remover_efecto(jugador, "sobrecarga_pendiente")
            print(f"DEBUG Efecto 'sobrecarga_pendiente' removido para {jugador.get_nombre()}.") 
        else:
            print(f"DEBUG Efecto 'sobrecarga_pendiente' NO detectado para {jugador.get_nombre()}.") 

        # Limpiar flag de habilidad usada para el nuevo turno
        jugador.habilidad_usada_este_turno = False

        return eventos

    def _procesar_efectos_posicion(self, jugador, posicion):
        # Si el jugador está en fase, ignorar efectos negativos de la casilla
        esta_en_fase = self._verificar_efecto_activo(jugador, "fase_activa")
        if self._verificar_efecto_activo(jugador, "fase_activa"):
            casilla_data_fase = self.casillas_especiales.get(posicion)
            tipo_casilla_fase = casilla_data_fase.get("tipo") if casilla_data_fase else None
            tipos_negativos = ["trampa", "pausa", "vampiro", "rebote"] 
            
            if tipo_casilla_fase in tipos_negativos:
                self.eventos_turno.append(f"👻 {jugador.get_nombre()} atraviesa {casilla_data_fase['nombre']} sin efecto.")
                energia_en_casilla = self._buscar_energia_en_posicion(jugador, posicion)
                if energia_en_casilla < 0:
                    self.eventos_turno.append(f"👻 {jugador.get_nombre()} ignora el pack de {energia_en_casilla} energía.")
                    # Si ignora casilla negativa, también ignora colisión
                    return # Salir para ignorar packs negativos y colisiones
                # Si es Tesoro u otro tipo positivo/neutro, continúa

        # --- CASILLAS ESPECIALES ---
        if self.evento_global_activo == "Apagón" and posicion in self.casillas_especiales:
            self.eventos_turno.append(f"🌎 Apagón: Casilla '{self.casillas_especiales[posicion]['nombre']}' desactivada.")

        elif posicion in self.casillas_especiales:
            casilla = self.casillas_especiales[posicion]
            # Asegúrate de no procesar dos veces si ya fue manejado por la lógica de Fase
            self.eventos_turno.append(f"🎯 {jugador.get_nombre()} activó: {casilla['nombre']}")
            
            tipo = casilla.get("tipo") # Usar .get() para seguridad

            jugador.tipos_casillas_visitadas.add(casilla.get("tipo"))

            if tipo == "tesoro":
                energia_intentada = casilla["valor"]
                energia_ganada_real = jugador.procesar_energia(energia_intentada)

                # Comprobar Bloqueo Energético antes de dar el tesoro
                if energia_ganada_real > 0:
                    # Usa el valor real ganado en el mensaje
                    self.eventos_turno.append(f"💰 +{energia_ganada_real} energía")
                    jugador.ganar_pm(2) # PM por recoger tesoro
                elif energia_intentada > 0: # Si intentó ganar pero no pudo (cambio real fue 0)
                    self.eventos_turno.append(f"🚫 {jugador.get_nombre()} no pudo recoger el Tesoro (+{energia_intentada} E) por Bloqueo.")

            elif tipo == "trampa":
                # 1. Obtener valor base de la trampa
                energia_perdida_base = casilla["valor"] 

                # 2. Aplicar Perk 'Aislamiento' (reduce la pérdida)
                if "aislamiento" in jugador.perks_activos:
                    energia_perdida_final = int(energia_perdida_base * 0.80) 
                    self.eventos_turno.append("🛡️ Aislamiento reduce pérdida!")
                else:
                    energia_perdida_final = energia_perdida_base 

                # 3. Aplicar la pérdida de energía
                jugador.procesar_energia(energia_perdida_final) 
                self.eventos_turno.append(f"💀 {energia_perdida_final} energía")
                jugador_afectado = jugador
                if not jugador_afectado.esta_activo(): # ¿Fue eliminado?
                    mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado!"
                    if mensaje_elim not in self.eventos_turno:
                        self.eventos_turno.append(mensaje_elim)
                elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and \
                    not getattr(jugador_afectado, '_ultimo_aliento_notificado', False): # ¿Se activó Último Aliento AHORA?
                    self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                    jugador_afectado._ultimo_aliento_notificado = True

                # 4. Lógica de Recompensa de Mina (Perk Básico)
                if casilla.get("nombre") == "Mina de Energía" and casilla.get("colocada_por"):
                    nombre_propietario = casilla["colocada_por"]
                    propietario = self._encontrar_jugador(nombre_propietario)
                    
                    # Comprobación Crítica: El jugador que CAYÓ debe tener el perk
                    if "recompensa_de_mina" in jugador.perks_activos: 
                        recompensa = abs(energia_perdida_final) // 2 
                        if propietario and propietario.esta_activo():
                            propietario.procesar_energia(recompensa)
                            self.eventos_turno.append(f"💰 Recompensa de Mina: {nombre_propietario} gana {recompensa} energía.")
                        
                        if posicion in self.casillas_especiales:
                            del self.casillas_especiales[posicion]
                            self.eventos_turno.append(f"✅ Mina en pos {posicion} consumida.")

                # 5. Aplicar Perk 'Chatarrero' (si aplica)
                if "chatarrero" in jugador.perks_activos:
                    jugador.ganar_pm(1)
                    self.eventos_turno.append("⚙️ +1 PM (Chatarrero)")

            elif tipo == "teletransporte":
                avance = randint(casilla["avance"][0], casilla["avance"][1])
                nueva_pos = min(jugador.get_posicion() + avance, self.posicion_meta)
                jugador.teletransportar_a(nueva_pos)
                self.eventos_turno.append(f"🌀 Teletransporte: avanzas {avance} a {nueva_pos}")
                # Procesar efectos/colisión en la nueva casilla
                if nueva_pos < self.posicion_meta:
                    self._procesar_efectos_posicion(jugador, nueva_pos) # Recursivo
                    self._verificar_colision(jugador, nueva_pos)

            elif tipo == "multiplicador":
                jugador.efectos_activos.append({"tipo": "multiplicador", "turnos": 1})
                self.eventos_turno.append("×2 Tu próxima energía se duplicará")

            elif tipo == "pausa":
                jugador.efectos_activos.append({"tipo": "pausa", "turnos": 1})
                self.eventos_turno.append("⏸️ Pierdes tu próximo turno")

            elif tipo == "turbo":
                jugador.efectos_activos.append({"tipo": "turbo", "turnos": 1})
                self.eventos_turno.append("⚡ Tu próximo movimiento se duplicará")

            elif tipo == "vampiro":
                # Asegurarse que el cálculo no cause error si el puntaje es negativo (no debería pasar)
                drenaje = max(0, jugador.get_puntaje() * casilla.get("porcentaje", 0) // 100)
                if drenaje > 0:
                    jugador.procesar_energia(-drenaje)
                    self.eventos_turno.append(f"🧛 Pierdes {drenaje} energía ({casilla.get('porcentaje', 0)}%)")

            elif tipo == "intercambio":
                otros = [j for j in self.jugadores if j != jugador and j.esta_activo()]
                if otros:
                    # Intercambia con el más cercano
                    objetivo = min(otros, key=lambda x: abs(x.get_posicion() - jugador.get_posicion()))
                    pos_j_original = jugador.get_posicion() # Guardar posición original
                    pos_o_original = objetivo.get_posicion()

                    # Realizar el intercambio
                    jugador.teletransportar_a(pos_o_original)
                    objetivo.teletransportar_a(pos_j_original)
                    self.eventos_turno.append(f"🔄 Intercambias posición con {objetivo.get_nombre()}. Ahora estás en {pos_o_original} y {objetivo.get_nombre()} en {pos_j_original}.")
                else:
                    self.eventos_turno.append("🔄 No hay nadie con quien intercambiar.")
            elif tipo == "rebote":
                retroceso = randint(5, 10)
                nueva_pos = max(1, jugador.get_posicion() - retroceso) # No ir más allá de 1
                if nueva_pos != jugador.get_posicion():
                    jugador.teletransportar_a(nueva_pos)
                    self.eventos_turno.append(f"↩️ Rebote: retrocedes {retroceso} a {nueva_pos}")
                    # Procesar efectos/colisión en la nueva casilla
                    self._procesar_efectos_posicion(jugador, nueva_pos)
                    self._verificar_colision(jugador, nueva_pos)
                else:
                    self.eventos_turno.append("↩️ Rebote: Ya estás en la casilla 1.")
            elif tipo == "retroceso_estrategico": # Agujero Negro
                if len(self.jugadores) > 1:
                    # Busca al jugador activo con la posición MÁS BAJA
                    jugador_ultimo = min([j for j in self.jugadores if j.esta_activo()], key=lambda x: x.get_posicion())
                    if jugador_ultimo != jugador:
                        nueva_pos = jugador_ultimo.get_posicion()
                        jugador.teletransportar_a(nueva_pos)
                        self.eventos_turno.append(f"⚫ Agujero Negro: Eres enviado a la posición del último jugador ({nueva_pos}).")
                        # Procesar colisión en la nueva casilla (muy importante)
                        self._verificar_colision(jugador, nueva_pos) 
                    else:
                        self.eventos_turno.append(f"⚫ Agujero Negro: ¡Ya ibas último! No pasa nada.")
            
            elif tipo == "recurso": # Pozo de PM
                jugador.ganar_pm(3)
                self.eventos_turno.append(f"⭐ Pozo de PM: ¡Ganas +3 PM!")

            elif tipo == "atraccion": # Imán
                self.eventos_turno.append(f"🧲 Imán: Atraes a los demás jugadores 2 casillas.")
                for j in self.jugadores:
                    if j != jugador and j.esta_activo():
                        pos_actual_j = j.get_posicion()
                        # min() para no pasarse de la meta
                        nueva_pos = min(pos_actual_j + 2, self.posicion_meta) 
                        if nueva_pos != pos_actual_j:
                            j.teletransportar_a(nueva_pos)
                            self.eventos_turno.append(f"🧲 {j.get_nombre()} es atraído a {nueva_pos}.")
                            # Procesar efectos Y colisión en la nueva casilla
                            self._procesar_efectos_posicion(j, nueva_pos)
                            self._verificar_colision(j, nueva_pos)
            
            elif tipo == "intercambio_recurso": # Chatarrería 
                energia_cambio = jugador.procesar_energia(-50)
                jugador.ganar_pm(3)
                # abs(energia_cambio) mostrará 50 (o 40 si tiene Aislamiento)
                self.eventos_turno.append(f"⚙️ Chatarrería: Pierdes {abs(energia_cambio)} E pero ganas +3 PM.")
        
        
        # --- PACKS DE ENERGÍA ---
        # Llamar a _buscar_energia_en_posicion solo si no está en fase Y si la casilla no es negativa (para evitar doble penalización)
        puede_recoger_pack = True
        if esta_en_fase:
            pack_info = next((pack for pack in self.energia_packs if pack['posicion'] == posicion and pack['valor'] != 0), None)
            if pack_info and pack_info['valor'] < 0:
                 self.eventos_turno.append(f"👻 {jugador.get_nombre()} ignora el pack negativo (Fase).")
                 puede_recoger_pack = False # Ignorar pack negativo
            elif pack_info and pack_info['valor'] > 0:
                 self.eventos_turno.append(f"👻 {jugador.get_nombre()} recoge pack positivo (Fase).")
                 # Continuar para recogerlo

        energia_cambio_pack = 0 # Inicializar por si no puede recoger
        if puede_recoger_pack:
            # Esta función ya añade los eventos de ganancia/pérdida/bloqueo/chatarrero
            energia_cambio_pack = self._buscar_energia_en_posicion(jugador, posicion)

            if energia_cambio_pack < 0:
                 jugador_afectado = jugador # Renombrar para que el bloque funcione
                 if not jugador_afectado.esta_activo(): # ¿Fue eliminado?
                     mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por pack de energía)!"
                     # Evitar mensajes duplicados si ya fue eliminado por otra causa en el mismo turno
                     if mensaje_elim not in self.eventos_turno:
                          self.eventos_turno.append(mensaje_elim)
                 elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and \
                      not getattr(jugador_afectado, '_ultimo_aliento_notificado', False): # ¿Se activó Último Aliento AHORA?
                     self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                     jugador_afectado._ultimo_aliento_notificado = True

        # --- COLISIONES ---
        # Procesar solo si no salió antes por la lógica de Fase Activa
        self._verificar_colision(jugador, posicion)

    def _buscar_energia_en_posicion(self, jugador, posicion):
        for i, pack in enumerate(self.energia_packs):
            if pack['posicion'] == posicion and pack['valor'] != 0:
                energia_original = pack['valor']
                energia_modificada = energia_original # Valor base a intentar aplicar

                if self.evento_global_activo == "Sobrecarga":
                    energia_modificada *= 2
                    self.eventos_turno.append("🌎 Sobrecarga: ¡Valor del pack duplicado!")

                # Aplicar perks que modifican el valor ANTES de procesar
                if energia_original > 0 and "eficiencia_energetica" in jugador.perks_activos:
                    energia_modificada = int(energia_original * 1.20)
                    self.eventos_turno.append("⚡ Eficiencia Energética!")
                elif energia_original < 0 and "aislamiento" in jugador.perks_activos:
                    energia_modificada = int(energia_original * 0.80)
                    self.eventos_turno.append("🛡️ Aislamiento!")

                # Llamar a procesar_energia con el valor modificado
                energia_cambio_real = jugador.procesar_energia(energia_modificada)

                if energia_cambio_real > 0: # Ganó energía
                    self.eventos_turno.append(f"💚 +{energia_cambio_real} energía")
                    jugador.ganar_pm(1)
                elif energia_modificada > 0: # Intentó ganar (modificada > 0) pero cambio_real fue 0
                    self.eventos_turno.append(f"🚫 {jugador.get_nombre()} no pudo recoger el pack (+{energia_modificada}) por Bloqueo.")
                elif energia_cambio_real < 0: # Perdió energía
                    self.eventos_turno.append(f"💀 {energia_cambio_real} energía")
                    if "chatarrero" in jugador.perks_activos:
                        jugador.ganar_pm(1)
                        self.eventos_turno.append("⚙️ +1 PM (Chatarrero)")
                        
                jugador_afectado = jugador
                if not jugador_afectado.esta_activo(): # ¿Fue eliminado?
                    mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado!"
                    if mensaje_elim not in self.eventos_turno:
                        self.eventos_turno.append(mensaje_elim)
                elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and \
                    not getattr(jugador_afectado, '_ultimo_aliento_notificado', False): # ¿Se activó Último Aliento AHORA?
                    self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                    jugador_afectado._ultimo_aliento_notificado = True

                # Reducir valor del pack a la mitad (si es reutilizable)
                self.energia_packs[i]['valor'] = energia_original // 2
                if abs(self.energia_packs[i]['valor']) < 10: # Si es muy bajo, eliminarlo
                    self.energia_packs[i]['valor'] = 0

                return energia_cambio_real # Devolver el cambio real

        return 0

    def _verificar_colision(self, jugador_moviendose, posicion):
        if self._verificar_efecto_activo(jugador_moviendose, "fase_activa"):
            self.eventos_turno.append(f"👻 {jugador_moviendose.get_nombre()} atraviesa a otros jugadores sin colisión.")
            return # Salir, no hay colisión
        jugadores_en_posicion = []
        for jugador in self.jugadores:
            if (jugador != jugador_moviendose and
                jugador.get_posicion() == posicion and
                jugador.esta_activo()):
                jugadores_en_posicion.append(jugador)

        if jugadores_en_posicion:
            self.eventos_turno.append("💥 ¡COLISIÓN! Todos pierden energía (o roban)")
            todos_involucrados = jugadores_en_posicion + [jugador_moviendose]

            jugador_moviendose.colisiones_causadas += 1

            # Aplicar efectos y perks
            for j_afectado in todos_involucrados:
                energia_perdida = -100 # Base
                es_el_que_se_movio = (j_afectado == jugador_moviendose)

                if self.evento_global_activo == "Cortocircuito":
                    energia_perdida = -150
                    if not es_el_que_se_movio:
                         self.eventos_turno.append("🌎 ¡Cortocircuito! Colisión más peligrosa.")

                # Verificar si alguien tiene Presencia Intimidante
                if not es_el_que_se_movio:
                    for j_estatico in jugadores_en_posicion: # Podría haber varios en la casilla
                         if "presencia_intimidante" in j_estatico.perks_activos:
                             energia_perdida -= 10 # Pierde 10 extra
                             self.eventos_turno.append(f"  {j_estatico.get_nombre()} intimida a {j_afectado.get_nombre()}!")
                             break 

                # Verificar Escudo o Amortiguación del afectado
                if self._verificar_efecto_activo(j_afectado, "escudo") or \
                   ("sombra_fugaz" in j_afectado.perks_activos and self._verificar_efecto_activo(j_afectado, "invisible")): # Añadir chequeo Sombra Fugaz
                    self.eventos_turno.append(f"  {j_afectado.get_nombre()}: 🛡️ protegido")
                    j_afectado.ganar_pm(2) # PM por sobrevivir
                    continue 

                elif "amortiguacion" in j_afectado.perks_activos:
                    energia_perdida = int(energia_perdida * 0.67) # Pierde 67% aprox
                    self.eventos_turno.append(f"  {j_afectado.get_nombre()}: Amortiguación reduce daño a {energia_perdida}")

                j_afectado.procesar_energia(energia_perdida)
                self.eventos_turno.append(f"  {j_afectado.get_nombre()}: {energia_perdida} energía")
                j_afectado.ganar_pm(2) # PM por sobrevivir 

                # Aplicar Drenaje por Colisión 
                if "drenaje_colision" in j_afectado.perks_activos:
                    energia_robada_total = 0
                    otros_en_colision = [j for j in todos_involucrados if j != j_afectado]
                    for j_robado in otros_en_colision:
                        # Robar solo si el otro no está protegido
                         if not (self._verificar_efecto_activo(j_robado, "escudo") or \
                                 ("sombra_fugaz" in j_robado.perks_activos and self._verificar_efecto_activo(j_robado, "invisible"))):
                            energia_a_robar = min(50, j_robado.get_puntaje()) # Roba hasta 50 o lo que le quede
                            j_robado.procesar_energia(-energia_a_robar)
                            energia_robada_total += energia_a_robar
                            self.eventos_turno.append(f"  {j_afectado.get_nombre()} drena {energia_a_robar} a {j_robado.get_nombre()}")

                    if energia_robada_total > 0:
                        j_afectado.procesar_energia(energia_robada_total)
                        self.eventos_turno.append(f"  {j_afectado.get_nombre()} recupera {energia_robada_total} por Drenaje.")

    def _avanzar_turno(self):
        # Encontrar el siguiente jugador activo
        intentos = 0
        turno_original = self.turno_actual # Guardar turno original

        print(f"--- AVANZAR TURNO --- Desde: {self.jugadores[turno_original].get_nombre()} ({turno_original})")

        while intentos < len(self.jugadores):
            self.turno_actual = (self.turno_actual + 1) % len(self.jugadores)
            print(f"Probando índice: {self.turno_actual}, Jugador: {self.jugadores[self.turno_actual].get_nombre()}, Activo: {self.jugadores[self.turno_actual].esta_activo()}")
            if self.jugadores[self.turno_actual].esta_activo():
                print(f"--- TURNO AVANZADO A --- Jugador: {self.jugadores[self.turno_actual].get_nombre()} ({self.turno_actual})")
                break
            intentos += 1
        
        # Nueva ronda si volvemos al primer jugador
        if self.turno_actual == turno_original and intentos >= len(self.jugadores):
             print("--- ERROR AL AVANZAR TURNO --- No se encontró jugador activo.")
        elif self.turno_actual == 0 and turno_original != 0 and self.jugadores[0].esta_activo() : 
            self.ronda += 1
            print(f"--- NUEVA RONDA --- Ronda: {self.ronda}")
            # 1. Reducir duración del evento activo 
            if self.evento_global_activo:
                self.evento_global_duracion -= 1
                if self.evento_global_duracion <= 0:
                    self.eventos_turno.append(f"🌎 ¡Evento Global '{self.evento_global_activo}' ha terminado!")
                    self.evento_global_activo = None
                else:
                    self.eventos_turno.append(f"🌎 Evento '{self.evento_global_activo}' durará {self.evento_global_duracion} ronda(s) más.")

            # 2. Activar un nuevo evento 
            if not self.evento_global_activo and self.ronda >= 5 and self.ronda % 5 == 0:
                self._activar_evento_global()

    # ===================================================================
    # --- 3. EVENTOS GLOBALES DE RONDA ---
    # ===================================================================

    def _activar_evento_global(self):
        # Lista de eventos confirmados
        eventos_posibles = [
            {"nombre": "Sobrecarga", "duracion": 2},     # Packs valen el doble
            {"nombre": "Apagón", "duracion": 1},         # Casillas especiales no funcionan
            {"nombre": "Mercado Negro", "duracion": 1},  # Perks a mitad de precio
            {"nombre": "Cortocircuito", "duracion": 2},  # Colisiones más peligrosas
            {"nombre": "Interferencia", "duracion": 1}   # No se pueden usar habilidades
        ]
        
        evento_elegido = random.choice(eventos_posibles)
        
        self.evento_global_activo = evento_elegido["nombre"]
        self.evento_global_duracion = evento_elegido["duracion"]
        
        print(f"--- EVENTO GLOBAL ACTIVADO --- {self.evento_global_activo} por {self.evento_global_duracion} rondas")
        
        mensaje_evento = f"🌎 ¡EVENTO GLOBAL: {self.evento_global_activo.upper()}!"
        if self.evento_global_activo == "Sobrecarga":
            mensaje_evento += " ¡Los packs de energía valen el DOBLE por 2 rondas!"
        elif self.evento_global_activo == "Apagón":
            mensaje_evento += " ¡Las casillas especiales se desactivan por 1 ronda!"
        elif self.evento_global_activo == "Mercado Negro":
            mensaje_evento += " ¡Los Packs de Perks cuestan la MITAD de PM por 1 ronda!"
        elif self.evento_global_activo == "Cortocircuito":
            mensaje_evento += " ¡Las colisiones son MÁS PELIGROSAS por 2 rondas!"
        elif self.evento_global_activo == "Interferencia":
            mensaje_evento += " ¡No se pueden usar HABILIDADES por 1 ronda!"
            
        self.eventos_turno.append(mensaje_evento)

    # ===================================================================
    # --- 4. ACCIONES DEL JUGADOR (Habilidades y Perks) ---
    # ===================================================================

    def usar_habilidad_jugador(self, nombre_jugador, indice_habilidad, objetivo=None):
        # 1. Validaciones Iniciales
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador:
            return {"exito": False, "mensaje": "Jugador no encontrado"}
        
        if self.evento_global_activo == "Interferencia":
            return {"exito": False, "mensaje": "🌎 ¡Interferencia! No se pueden usar habilidades durante este evento."}

        # Nueva validación: Chequear si hay una oferta de perk pendiente
        if hasattr(jugador, 'oferta_perk_activa') and jugador.oferta_perk_activa:
            return {"exito": False, "mensaje": "Debes elegir un perk de la oferta pendiente antes de usar una habilidad."}

        if indice_habilidad < 1 or indice_habilidad > len(jugador.habilidades):
            return {"exito": False, "mensaje": "Índice de habilidad inválido"}

        habilidad = jugador.habilidades[indice_habilidad - 1] # Objeto base de la habilidad

        # Leer el cooldown ACTUAL desde el DICCIONARIO DEL JUGADOR, no del objeto habilidad
        cooldown_actual = jugador.habilidades_cooldown.get(habilidad.nombre, 0)
        if cooldown_actual > 0:
            return {"exito": False, "mensaje": f"Habilidad '{habilidad.nombre}' en cooldown por {cooldown_actual} turnos."}

        if getattr(jugador, 'habilidad_usada_este_turno', False):
            return {"exito": False, "mensaje": "Ya usaste una habilidad en este turno."}

        # 2. Despacho a la Función Específica
        try:
            # Limpiar nombre para despacho (incluyendo tildes)
            habilidad_nombre_limpio = habilidad.nombre.lower().replace(' ', '_').replace('é', 'e').replace('ó', 'o').replace('í', 'i')
            func_name = f"_hab_{habilidad_nombre_limpio}"

            dispatcher = getattr(self, func_name, None)

            if not dispatcher:
                # Log de error importante en el servidor
                print(f"!!! ERROR Despacho: No se encontró la función '{func_name}' para la habilidad '{habilidad.nombre}'")
                return {"exito": False, "mensaje": f"Habilidad '{habilidad.nombre}' no implementada correctamente en el servidor."}

            # EJECUTA la función de la habilidad
            resultado_logica = dispatcher(jugador, habilidad, objetivo)
            
            # Usar .get() para evitar KeyError si la función no devuelve 'exito' o 'eventos'
            exito = resultado_logica.get('exito', False)
            eventos_habilidad = resultado_logica.get('eventos', [])

        except Exception as e:
            print(f"!!! ERROR FATAL al ejecutar lógica de {habilidad.nombre}: {e}")
            traceback.print_exc() # Imprime el traceback completo en la consola del servidor
            self.eventos_turno.append(f"!!! ERROR al usar {habilidad.nombre}: {e}")
            return {"exito": False, "mensaje": f"Error interno del servidor al ejecutar {habilidad.nombre}."}

        # 3. Lógica de Cierre (Cooldown, PM, Retorno)
        if exito:
            # Aplicar Cooldown y marcar habilidad como usada en el turno
            if hasattr(jugador, 'habilidades_cooldown'):
                # Usar cooldown_base del objeto habilidad original para reiniciar
                jugador.habilidades_cooldown[habilidad.nombre] = habilidad.cooldown_base
            jugador.habilidad_usada_este_turno = True

            # PM ganados
            pm_ganados = 1
            if "maestria_habilidad" in jugador.perks_activos: 
                pm_ganados += 2
            jugador.ganar_pm(pm_ganados)
            if pm_ganados > 1: 
                self.eventos_turno.append(f"✨ +{pm_ganados} PM (Maestría)")

            # Añadir eventos de la habilidad al log principal
            self.eventos_turno.extend(eventos_habilidad)

            # Preparar retorno (Leer cooldown actualizado después de aplicarlo)
            cooldown_actual_retorno = jugador.habilidades_cooldown.get(habilidad.nombre, habilidad.cooldown_base)
            habilidad_dict_final = {
                'nombre': habilidad.nombre, 'tipo': habilidad.tipo,
                'descripcion': habilidad.descripcion, 'simbolo': habilidad.simbolo,
                'cooldown_base': habilidad.cooldown_base, 'cooldown': cooldown_actual_retorno
            }

            return { 
                "exito": True, 
                "eventos": self.eventos_turno, 
                "habilidad": habilidad_dict_final 
            }
        else:
            # Habilidad fallida (añadir evento de fallo al log)
            if eventos_habilidad: 
                self.eventos_turno.extend(eventos_habilidad)
                
            # Usar el último evento como mensaje de error si existe, si no, un genérico
            mensaje_fallo = eventos_habilidad[-1] if eventos_habilidad else f"No se pudo usar '{habilidad.nombre}'."
            return {"exito": False, "mensaje": mensaje_fallo}

    def comprar_pack_perk(self, nombre_jugador, tipo_pack):
        jugador = self._encontrar_jugador(nombre_jugador)
        pm_actuales = jugador.get_pm() if jugador else 0
        if not jugador or not jugador.esta_activo():
            return {"exito": False, "mensaje": "Jugador no encontrado o inactivo", "oferta": [], "pm_restantes": pm_actuales}

        if hasattr(jugador, 'oferta_perk_activa') and jugador.oferta_perk_activa:
            # Si ya tiene una oferta, reenviarla al cliente para forzar la elección
            return {
                "exito": True,
                "mensaje": "Ya tienes una oferta pendiente. ¡Debes elegir un perk!",
                "oferta": jugador.oferta_perk_activa.get("oferta_detallada", []),
                "coste": jugador.oferta_perk_activa.get("coste_pagado", 0),
                "pm_restantes": jugador.get_pm()
            }

        # Definir costes y composición de los packs
        costes = {"basico": 4, "intermedio": 8, "avanzado": 12}
        composicion = {
            "basico": {"basico": 2},
            "intermedio": {"medio": 2, "basico": 1},
            "avanzado": {"alto": 2}
        }

        if self.evento_global_activo == "Mercado Negro":
            # Reducir costes a la mitad, asegurando que sea al menos 1
            costes = {
                "basico": max(1, costes["basico"] // 2),
                "intermedio": max(1, costes["intermedio"] // 2),
                "avanzado": max(1, costes["avanzado"] // 2)
            }

        if tipo_pack not in costes:
            return {"exito": False, "mensaje": "Tipo de pack inválido", "oferta": [], "pm_restantes": jugador.get_pm()}

        coste_pack = costes[tipo_pack]

        # Cobrar PM primero
        if not jugador.gastar_pm(coste_pack):
            return {"exito": False, "mensaje": f"No tienes suficientes PM ({jugador.get_pm()}/{coste_pack})", "oferta": [], "pm_restantes": jugador.get_pm()}

        self.eventos_turno.append(f"💰 {nombre_jugador} gastó {coste_pack} PM en un Pack {tipo_pack.capitalize()}.")

        perks_disponibles_tier = {}
        habilidades_jugador = {h.nombre for h in jugador.habilidades}

        for tier in ["basico", "medio", "alto"]:
            perks_tier = obtener_perks_por_tier(tier) # Usa la función importada de perks.py
            perks_disponibles_tier[tier] = []
            for perk_id in perks_tier:
                # Omitir si ya lo tiene activo
                if perk_id in jugador.perks_activos: continue
                
                perk_config = PERKS_CONFIG.get(perk_id)
                if not perk_config: continue

                # Leer el requisito directamente de la configuración del perk
                req_hab = perk_config.get("requires_habilidad")
                if req_hab and req_hab not in habilidades_jugador:
                    continue # Saltar este perk si no tiene la habilidad requerida

                perks_disponibles_tier[tier].append(perk_id)

        # Seleccionar perks aleatorios según la composición del pack
        oferta_final_ids = []
        composicion_pack = composicion[tipo_pack]
        total_a_ofrecer = sum(composicion_pack.values())

        for tier, cantidad in composicion_pack.items():
            candidatos = perks_disponibles_tier.get(tier, [])
            # Evitar seleccionar el mismo ID dos veces si hay pocos candidatos
            candidatos_validos = [pid for pid in candidatos if pid not in oferta_final_ids]
            cantidad_real = min(cantidad, len(candidatos_validos))
            if cantidad_real > 0:
                elegidos = random.sample(candidatos_validos, cantidad_real)
                oferta_final_ids.extend(elegidos)

        # Rellenar si faltan perks (con tiers alternativos)
        tiers_alternativos = ["basico", "medio", "alto"]
        random.shuffle(tiers_alternativos)
        while len(oferta_final_ids) < total_a_ofrecer:
            relleno_encontrado = False
            for tier_alt in tiers_alternativos:
                # Candidatos alternativos que no estén ya en la oferta
                candidatos_alt = [pid for pid in perks_disponibles_tier.get(tier_alt, []) if pid not in oferta_final_ids]
                if candidatos_alt:
                    oferta_final_ids.append(random.choice(candidatos_alt))
                    relleno_encontrado = True
                    break # Salir del loop de tiers alternativos al encontrar uno
            if not relleno_encontrado: break # Salir del while si no quedan candidatos en ningún tier

        # Preparar la oferta detallada para el cliente
        oferta_detallada = []
        for perk_id in oferta_final_ids:
            perk_data = PERKS_CONFIG.get(perk_id)
            if perk_data:
                # Copiar para no modificar el original y añadir 'id'
                perk_info_oferta = perk_data.copy()
                perk_info_oferta['id'] = perk_id
                oferta_detallada.append(perk_info_oferta)

        # Mensaje de oferta
        mensaje_oferta = f"Elige 1 Perk del Pack {tipo_pack.capitalize()} (Coste: {coste_pack} PM):"
        if tipo_pack == "avanzado" and len(oferta_detallada) == 2:
            mensaje_oferta = f"Elige 1 Perk del Pack Avanzado (Coste: {coste_pack} PM): Se ofrecen 2 de Tier Alto."
        elif len(oferta_detallada) < total_a_ofrecer:
            mensaje_oferta += " (Algunos perks no estaban disponibles o ya los tienes)"

        # Guardar la oferta pendiente en el jugador
        if hasattr(jugador, 'oferta_perk_activa'):
            jugador.oferta_perk_activa = {
                "oferta_detallada": oferta_detallada,
                "coste_pagado": coste_pack
            }

        # Devolver éxito, oferta, coste original Y PM restantes
        return {
            "exito": True,
            "mensaje": mensaje_oferta,
            "oferta": oferta_detallada,
            "coste": coste_pack,
            "pm_restantes": jugador.get_pm()
        }

    def activar_perk_seleccionado(self, nombre_jugador, perk_id, coste_esperado_pack):
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador or not jugador.esta_activo():
            # Devuelve los PM actuales si el jugador no es válido
            pm_actuales = jugador.get_pm() if jugador else 0
            return {"exito": False, "mensaje": "Jugador no encontrado o inactivo", "pm_restantes": pm_actuales}

        perk_config = PERKS_CONFIG.get(perk_id)
        if not perk_config:
            # Devuelve PM si el perk es inválido (error inesperado)
            jugador.ganar_pm(coste_esperado_pack)
            self.eventos_turno.append(f"⚠️ Error: Perk {perk_id} inválido. {coste_esperado_pack} PM devueltos.")
            return {"exito": False, "mensaje": "Perk seleccionado inválido. PM devueltos.", "pm_restantes": jugador.get_pm()}

        mensaje_exito = "" 

        # Lógica de activación 
        if perk_id == "descuento_habilidad":
            habilidades_candidatas = [h for h in jugador.habilidades if h.cooldown_base > 1]
            if habilidades_candidatas:
                habilidad_afectada = random.choice(habilidades_candidatas)
                # Guardar el perk con la habilidad afectada (ID único)
                perk_activado_id = f"descuento_{habilidad_afectada.nombre.lower().replace(' ', '_')}"
                jugador.perks_activos.append(perk_activado_id)
                mensaje_exito = f"¡Perk '{perk_config['nombre']}' activado para {habilidad_afectada.nombre}!"
                self.eventos_turno.append(f"⭐ {nombre_jugador} activó: Descuento (-1 CD a {habilidad_afectada.nombre})")
            else:
                # Si no hay habilidades elegibles, devolver PM
                jugador.ganar_pm(coste_esperado_pack)
                self.eventos_turno.append(f"⚠️ No hay habilidades elegibles para Descuento. {coste_esperado_pack} PM devueltos.")
                return {"exito": False, "mensaje": "No tienes habilidades elegibles para 'Descuento'. PM devueltos.", "pm_restantes": jugador.get_pm()}
        else:
            # Perks normales
            jugador.perks_activos.append(perk_id)
            mensaje_exito = f"¡Perk '{perk_config['nombre']}' activado!"
            self.eventos_turno.append(f"⭐ {nombre_jugador} activó el Perk: {perk_config['nombre']}")

        jugador.oferta_perk_activa = None 
        
        # Devolver éxito y PM actualizados
        return {"exito": True, "mensaje": mensaje_exito, "pm_restantes": jugador.get_pm()}

    # ===================================================================
    # --- 5. LÓGICA DE HABILIDADES (El bloque "_hab_") ---
    # ===================================================================
    
    def _hab_transferencia_de_fase(self, jugador, habilidad, objetivo):
        eventos = []
        # Aplicar un efecto temporal que se verificará en _procesar_efectos_posicion y _verificar_colision
        jugador.efectos_activos.append({"tipo": "fase_activa", "turnos": 1}) 
        eventos.append("👻 Transferencia de Fase: Serás intangible e inmune a casillas negativas en tu próximo movimiento de dado.")
        return {"exito": True, "eventos": eventos}
    
    def _hab_bloqueo_energetico(self, jugador, habilidad, objetivo):
        eventos = []
        if not objetivo:
            eventos.append("Debes especificar un jugador objetivo.")
            return {"exito": False, "eventos": eventos}
        
        jugador_objetivo = self._encontrar_jugador(objetivo)
        if not jugador_objetivo or not jugador_objetivo.esta_activo():
            eventos.append(f"Objetivo '{objetivo}' no válido.")
            return {"exito": False, "eventos": eventos}
            
        # Comprobar protecciones (Escudo/Barrera podrían bloquearlo)
        if self._verificar_efecto_activo(jugador_objetivo, "escudo"):
             self._reducir_efectos_temporales(jugador_objetivo, tipo_efecto="escudo", reducir_todo=False)
             eventos.append(f"🛡️ {jugador_objetivo.get_nombre()} bloqueó el Bloqueo Energético.")
             return {"exito": False, "eventos": eventos}
        elif self._verificar_efecto_activo(jugador_objetivo, "barrera"):
             self._remover_efecto(jugador_objetivo, "barrera") # Barrera se consume pero no refleja
             eventos.append(f"🔮 {jugador_objetivo.get_nombre()} disipó el Bloqueo Energético con Barrera.")
             return {"exito": False, "eventos": eventos}

        # Aplicar el efecto de bloqueo (dura 2 rondas)
        duracion_turnos = 2
        jugador_objetivo.efectos_activos.append({"tipo": "bloqueo_energia", "turnos": duracion_turnos})
        eventos.append(f"🚫 {jugador_objetivo.get_nombre()} no podrá ganar energía durante {duracion_turnos} turnos.")
        
        return {"exito": True, "eventos": eventos}
    
    def _hab_sobrecarga_inestable(self, jugador, habilidad, objetivo):
        eventos = []
        costo_inicial = 50
        
        # Comprobar si tiene energía para el costo inicial
        if jugador.get_puntaje() < costo_inicial:
            eventos.append(f"No tienes suficiente energía ({costo_inicial} E) para Sobrecarga.")
            return {"exito": False, "eventos": eventos}
            
        # Cobrar costo inicial
        jugador.procesar_energia(-costo_inicial)
        eventos.append(f"🎲 Sobrecarga Inestable: Pagaste {costo_inicial} E. El resultado se aplicará en tu próximo turno.")
        
        # Aplicar efecto temporal que se resolverá en _procesar_inicio_turno
        jugador.efectos_activos.append({"tipo": "sobrecarga_pendiente", "turnos": 1})
        
        return {"exito": True, "eventos": eventos}
    
    def _hab_sabotaje(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)
        if not obj:
            eventos.append("Objetivo inválido.")
            return {"exito": False, "eventos": eventos}
        
        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(obj, tipo_efecto="escudo", reducir_todo=False)
            eventos.append(f"🛡️ {obj.get_nombre()} bloqueó el Sabotaje con su escudo.")
            return {"exito": False, "eventos": eventos}
        
        if self._puede_ser_afectado(obj, habilidad):
            turnos_pausa = 2 if "sabotaje_persistente" in jugador.perks_activos else 1
            obj.efectos_activos.append({"tipo": "pausa", "turnos": turnos_pausa})
            eventos.append(f"⚔️ {obj.get_nombre()} perderá su{'s próximos' if turnos_pausa > 1 else ' próximo'} {turnos_pausa} turno{'s' if turnos_pausa > 1 else ''}!")
            return {"exito": True, "eventos": eventos}
        else:
            eventos.append("Objetivo protegido (invisible).")
            return {"exito": False, "eventos": eventos}

    def _hab_bomba_energetica(self, jugador, habilidad, objetivo):
        eventos = []
        pos_j = jugador.get_posicion()
        rango_bomba = 5 if "bomba_fragmentacion" in jugador.perks_activos else 3
        dano_bomba = 75 # Daño base
        afectados, protegidos = [], []

        for j in self.jugadores:
            # Iterar sobre cada jugador 'j' que NO es el lanzador
            if j != jugador and j.esta_activo() and abs(j.get_posicion() - pos_j) <= rango_bomba:

                # Verificar si 'j' puede ser afectado (invisible, Anticipación)
                # Pasamos la habilidad para la verificación de Anticipación
                if self._puede_ser_afectado(j, habilidad):
                    # Comprobar Barrera (refleja el daño)
                    if self._verificar_efecto_activo(j, "barrera"):
                        eventos.append(f"🔮 {j.get_nombre()} refleja el daño de la Bomba.")
                        # Aplicar daño al lanzador
                        energia_cambio_reflejo = jugador.procesar_energia(-dano_bomba)
                        eventos.append(f"💥 ¡Recibes {energia_cambio_reflejo} de daño reflejado!")
                        self._remover_efecto(j, "barrera") # Barrera se consume

                        jugador_afectado = jugador
                        if not jugador_afectado.esta_activo():
                            mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por reflejo de Bomba)!"
                            if mensaje_elim not in self.eventos_turno: self.eventos_turno.append(mensaje_elim)
                        elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and not getattr(jugador_afectado, '_ultimo_aliento_notificado', False):
                            self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                            jugador_afectado._ultimo_aliento_notificado = True
                        continue # Pasar al siguiente jugador

                    # Comprobar Escudo (bloquea el daño)
                    elif self._verificar_efecto_activo(j, "escudo"):
                         protegidos.append(j.get_nombre())
                         self._reducir_efectos_temporales(j, tipo_efecto="escudo", reducir_todo=False) # Escudo se consume
                         eventos.append(f"🛡️ {j.get_nombre()} bloqueó la Bomba.")
                         continue # Pasar al siguiente jugador

                    # Si no está protegido, aplicar daño
                    else:
                        energia_cambio_directo = j.procesar_energia(-dano_bomba)
                        afectados.append(j.get_nombre()) # Añadir a afectados ANTES de verificar eliminación

                        jugador_afectado = j
                        if not jugador_afectado.esta_activo():
                            mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por Bomba)!"
                            if mensaje_elim not in self.eventos_turno: self.eventos_turno.append(mensaje_elim)
                        elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and not getattr(jugador_afectado, '_ultimo_aliento_notificado', False):
                            self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                            jugador_afectado._ultimo_aliento_notificado = True

                        # Lógica de empuje (Bomba Fragmentación) - Solo si el objetivo aún está activo
                        if "bomba_fragmentacion" in jugador.perks_activos and jugador_afectado.esta_activo():
                            empuje = 1
                            if "desvio_cinetico" in j.perks_activos: empuje = 0 # Anula empuje

                            if empuje > 0:
                                direccion = 1 if j.get_posicion() > pos_j else -1
                                pos_nueva_empujon = max(1, min(j.get_posicion() + (direccion * empuje), self.posicion_meta))
                                if pos_nueva_empujon != j.get_posicion():
                                    j.teletransportar_a(pos_nueva_empujon)
                                    eventos.append(f"💨 {j.get_nombre()} es empujado a {pos_nueva_empujon}.")
                                    # Procesar efectos/colisión en la nueva casilla
                                    self._procesar_efectos_posicion(j, pos_nueva_empujon)
                                    self._verificar_colision(j, pos_nueva_empujon)
                else:
                    # Si _puede_ser_afectado devolvió False 
                    protegidos.append(j.get_nombre())
                    # El evento de protección/esquiva ya se añadió en _puede_ser_afectado

        if afectados:
            eventos.append(f"💥 Afectados por Bomba: {', '.join(afectados)} (-{dano_bomba} E)")
        if protegidos:
             eventos.append(f"🛡️/👻 Protegidos/Esquivaron Bomba: {', '.join(protegidos)}")

        return {"exito": True, "eventos": eventos}

    def _hab_robo(self, jugador, habilidad, objetivo):
        eventos = []
        otros = [j for j in self.jugadores if j != jugador and j.esta_activo()]
        if not otros:
            eventos.append("No hay otros jugadores activos para robar.")
            return {"exito": False, "eventos": eventos}

        # Roba al más rico
        obj = max(otros, key=lambda x: x.get_puntaje())

        # Verificar si el objetivo puede ser afectado (invisible, Anticipación)
        if not self._puede_ser_afectado(obj, habilidad):
            if self.eventos_turno: eventos.extend(self.eventos_turno[-1:]) # Copia el último evento
            return {"exito": False, "eventos": eventos}

        # Calcular cantidad a robar
        cantidad_base = 75
        cantidad_robo = cantidad_base + 30 if "robo_oportunista" in jugador.perks_activos else cantidad_base
        energia_a_robar = min(cantidad_robo, obj.get_puntaje()) # No robar más de lo que tiene

        if energia_a_robar <= 0:
             eventos.append(f"{obj.get_nombre()} no tiene energía para robar.")
             return {"exito": False, "eventos": eventos}

        # Comprobar Barrera del objetivo (refleja)
        if self._verificar_efecto_activo(obj, "barrera"):
            eventos.append(f"🔮 {obj.get_nombre()} refleja el Robo.")
            # Aplicar pérdida al ladrón
            energia_cambio_reflejo = jugador.procesar_energia(-energia_a_robar)
            eventos.append(f"💥 ¡Recibes {energia_cambio_reflejo} de daño reflejado!")
            self._remover_efecto(obj, "barrera") # Barrera se consume

            jugador_afectado = jugador
            if not jugador_afectado.esta_activo():
                mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por reflejo de Robo)!"
                if mensaje_elim not in self.eventos_turno: self.eventos_turno.append(mensaje_elim)
            elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and not getattr(jugador_afectado, '_ultimo_aliento_notificado', False):
                self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                jugador_afectado._ultimo_aliento_notificado = True
            return {"exito": False, "eventos": eventos} # Robo fallido por reflejo

        # Comprobar Escudo del objetivo (bloquea)
        elif self._verificar_efecto_activo(obj, "escudo"):
            eventos.append(f"🛡️ {obj.get_nombre()} bloqueó el Robo (Escudo consumido).")
            self._reducir_efectos_temporales(obj, tipo_efecto="escudo", reducir_todo=False)
            return {"exito": False, "eventos": eventos} # Robo fallido por escudo

        # Si no está protegido, realizar el robo
        else:
            # Quitar energía al objetivo
            energia_cambio_obj = obj.procesar_energia(-energia_a_robar)
            # Dar energía al ladrón (verificar bloqueo del ladrón)
            energia_cambio_jugador = jugador.procesar_energia(energia_a_robar)

            if energia_cambio_jugador > 0:
                 eventos.append(f"🎭 Robas {energia_cambio_jugador} energía a {obj.get_nombre()}.")
            elif energia_a_robar > 0: # Si intentó ganar pero estaba bloqueado
                 eventos.append(f"🚫 {jugador.get_nombre()} no pudo recibir la energía robada por Bloqueo.")

            jugador_afectado = obj
            if not jugador_afectado.esta_activo():
                mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por Robo)!"
                if mensaje_elim not in self.eventos_turno: self.eventos_turno.append(mensaje_elim)
            elif getattr(jugador_afectado, '_ultimo_aliento_usado', False) and not getattr(jugador_afectado, '_ultimo_aliento_notificado', False):
                self.eventos_turno.append(f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos).")
                jugador_afectado._ultimo_aliento_notificado = True

            return {"exito": True, "eventos": eventos}

    def _hab_tsunami(self, jugador, habilidad, objetivo):
        eventos = []
        # El perk 'maremoto' pertenece al LANZADOR (jugador) y define el empuje base
        empuje_base = 5 if "maremoto" in jugador.perks_activos else 3 
        afectados = []
        
        for j in self.jugadores:
            # Iteramos sobre cada jugador 'j' que NO es el lanzador
            if j != jugador and j.esta_activo():
                
                empuje_final_jugador = empuje_base # Empuje por defecto para este jugador
                
                if "desvio_cinetico" in j.perks_activos:
                    reduccion = empuje_final_jugador // 2 # División entera
                    empuje_final_jugador -= reduccion
                    eventos.append(f"🏃‍♂️ {j.get_nombre()} desvía parte del Tsunami (Empuje reducido a {empuje_final_jugador}).")

                # Aplicar el empuje final calculado para este jugador 'j'
                nueva = max(1, j.get_posicion() - empuje_final_jugador) 
                if nueva != j.get_posicion(): 
                    j.teletransportar_a(nueva)
                    afectados.append(f"{j.get_nombre()} a {nueva}")
                    # Procesar efectos/colisión en la nueva casilla SIEMPRE después del movimiento
                    self._procesar_efectos_posicion(j, nueva)
                    self._verificar_colision(j, nueva)

        if afectados:
            eventos.append(f"🌊 Tsunami empuja (máx {empuje_base} casillas): {', '.join(afectados)}")
        else:
            eventos.append("🌊 Tsunami no afectó a nadie.")
            
        return {"exito": True, "eventos": eventos}

    def _hab_escudo_total(self, jugador, habilidad, objetivo):
        eventos = []
        turnos_duracion = len(self.jugadores) * 3 # 3 rondas
        jugador.efectos_activos.append({"tipo": "escudo", "turnos": turnos_duracion})
        eventos.append(f"🛡️ ¡Protección activada por 3 rondas ({turnos_duracion} turnos)!")
        return {"exito": True, "eventos": eventos}

    def _hab_curacion(self, jugador, habilidad, objetivo):
        eventos = []
        energia_intentada = 75
        energia_ganada_real = jugador.procesar_energia(energia_intentada)
        if energia_ganada_real > 0:
            eventos.append(f"🏥 +{energia_ganada_real} energía")
        elif energia_intentada > 0:
            eventos.append(f"🚫 Curación bloqueada para {jugador.get_nombre()}.")
        return {"exito": True, "eventos": eventos}

    def _hab_invisibilidad(self, jugador, habilidad, objetivo):
        eventos = []
        jugador.efectos_activos.append({"tipo": "invisible", "turnos": 2})
        eventos.append("👻 Invisible por 2 turnos (Evita colisiones y ser objetivo).")
        return {"exito": True, "eventos": eventos}

    def _hab_barrera(self, jugador, habilidad, objetivo):
        eventos = []
        jugador.efectos_activos.append({"tipo": "barrera", "turnos": 2}) # Dura hasta que se usa
        eventos.append("🔮 Barrera activada (Refleja la próxima habilidad negativa).")
        return {"exito": True, "eventos": eventos}

    def _hab_cohete(self, jugador, habilidad, objetivo):
        eventos = []
        avance = randint(3, 17)
        nueva = min(jugador.get_posicion() + avance, self.posicion_meta)
        jugador.teletransportar_a(nueva) 
        eventos.append(f"🚀 Cohete: Avanzas {avance} casillas a la posición {nueva}.")
        if nueva < self.posicion_meta:
            self._procesar_efectos_posicion(jugador, nueva)
            self._verificar_colision(jugador, nueva)
        if nueva >= self.posicion_meta:
            self.fin_juego = True
            eventos.append(f"🏆 ¡{jugador.get_nombre()} llegó a la meta con Cohete!")
        return {"exito": True, "eventos": eventos}

    def _hab_intercambio_forzado(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)
        if not obj or not obj.esta_activo():
            eventos.append("Objetivo inválido o no activo.")
            return {"exito": False, "eventos": eventos}
        if not self._puede_ser_afectado(obj, habilidad): # Revisa invisibilidad
             eventos.append(f"{obj.get_nombre()} está protegido.")
             return {"exito": False, "eventos": eventos}

        pos_j, pos_o = jugador.get_posicion(), obj.get_posicion()
        jugador.teletransportar_a(pos_o)
        obj.teletransportar_a(pos_j)
        eventos.append(f"🔄 Intercambias posición con {obj.get_nombre()}.")
        # Procesar efectos de las nuevas casillas para ambos
        self._procesar_efectos_posicion(jugador, pos_o)
        self._verificar_colision(jugador, pos_o)
        self._procesar_efectos_posicion(obj, pos_j)
        self._verificar_colision(obj, pos_j)
        return {"exito": True, "eventos": eventos}

    def _hab_retroceso(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)
        if not obj or not obj.esta_activo():
            eventos.append("Objetivo inválido o no activo.")
            return {"exito": False, "eventos": eventos}
        if not self._puede_ser_afectado(obj, habilidad): 
             eventos.append(f"{obj.get_nombre()} está protegido (invisible).")
             return {"exito": False, "eventos": eventos}
        
        # El perk 'retroceso_brutal' pertenece al LANZADOR (jugador)
        empuje_base = 7 if "retroceso_brutal" in jugador.perks_activos else 5
        empuje_final = empuje_base # Empuje por defecto

        if "desvio_cinetico" in obj.perks_activos:
            reduccion = empuje_final // 2 
            empuje_final -= reduccion
            eventos.append(f"🏃‍♂️ {obj.get_nombre()} desvía parte del Retroceso (Empuje reducido a {empuje_final}).")

        nueva = max(1, obj.get_posicion() - empuje_final) # No retroceder más allá de 1
        if nueva != obj.get_posicion():
            obj.teletransportar_a(nueva)
            eventos.append(f"⏪ {obj.get_nombre()} retrocede {empuje_final} casillas a {nueva}.")
            # Procesar efectos/colisión en la nueva casilla
            self._procesar_efectos_posicion(obj, nueva)
            self._verificar_colision(obj, nueva)
        else:
            eventos.append(f"⏪ {obj.get_nombre()} ya está en la casilla 1.")
            
        return {"exito": True, "eventos": eventos}

    def _hab_rebote_controlado(self, jugador, habilidad, objetivo):
        eventos = []
        pos_actual = jugador.get_posicion()
        pos_intermedia = max(1, pos_actual - 2) 
        jugador.teletransportar_a(pos_intermedia)
        eventos.append(f"↩️ Rebote: Retrocedes 2 casillas a {pos_intermedia}.")

        pos_final = min(pos_intermedia + 9, self.posicion_meta)
        jugador.teletransportar_a(pos_final)
        eventos.append(f"⬆️ Controlado: Avanzas 9 casillas a {pos_final}.")
        
        self._procesar_efectos_posicion(jugador, pos_final)
        self._verificar_colision(jugador, pos_final)
        
        if pos_final >= self.posicion_meta:
            self.fin_juego = True
            eventos.append(f"🏆 ¡Llegaste a la meta con Rebote Controlado!")
        return {"exito": True, "eventos": eventos}

    def _hab_dado_perfecto(self, jugador, habilidad, objetivo):
        eventos = []
        try:
            valor = int(objetivo)
            if not (1 <= valor <= 6): raise ValueError
        except (ValueError, TypeError):
            eventos.append("Valor inválido para Dado Perfecto (debe ser 1-6).")
            return {"exito": False, "eventos": eventos}

        # Almacena el valor para que ejecutar_turno_dado lo use
        jugador.dado_forzado = valor 
        eventos.append(f"🎯 Preparaste un Dado Perfecto con valor {valor}.")
        return {"exito": True, "eventos": eventos}

    def _hab_mina_de_energia(self, jugador, habilidad, objetivo):
        eventos = []
        pos_actual = jugador.get_posicion()

        # Validación 1: No en la Meta
        if pos_actual >= self.posicion_meta:
            eventos.append("No puedes poner una mina en la Meta.")
            return {"exito": False, "eventos": eventos}
        
        # Validación 2: Casilla no ocupada por otra especial
        if pos_actual in self.casillas_especiales:
            eventos.append(f"La posición {pos_actual} ya tiene una casilla especial.")
            return {"exito": False, "eventos": eventos}

        # Colocar la Mina
        self.casillas_especiales[pos_actual] = {
            "nombre": "Mina de Energía", 
            "tipo": "trampa", 
            "simbolo": "💣",
            "valor": -50, 
            "colocada_por": jugador.get_nombre() # Guardar quién la puso
        }
        eventos.append(f"💣 Mina Colocada en {pos_actual} (-50 E).")
        
        # Devuelve éxito y los eventos generados
        return {"exito": True, "eventos": eventos}

    def _hab_doble_turno(self, jugador, habilidad, objetivo):
        # Ahora aplica el efecto 'doble_dado' para que ejecute_turno_dado lo use
        eventos = []
        jugador.efectos_activos.append({"tipo": "doble_dado", "turnos": 1})
        eventos.append(f"🔄 Lanzarás dos dados este turno.")
        return {"exito": True, "eventos": eventos}

    def _hab_caos(self, jugador, habilidad, objetivo):
        eventos = ["🎪 Caos: ¡Todos los jugadores se mueven aleatoriamente!"]
        for j in self.jugadores:
            if j.esta_activo():
                mov = randint(1, 6)
                # Usar avanzar para respetar límites, luego teletransportar al resultado
                pos_actual = j.get_posicion()
                nueva_pos_calc = min(pos_actual + mov, self.posicion_meta)
                j.teletransportar_a(nueva_pos_calc)
                eventos.append(f"🌀 {j.get_nombre()} avanza {mov} a {nueva_pos_calc}.")
                # Procesar efectos en la nueva casilla
                if nueva_pos_calc < self.posicion_meta:
                    self._procesar_efectos_posicion(j, nueva_pos_calc)
                    self._verificar_colision(j, nueva_pos_calc)
        return {"exito": True, "eventos": eventos}

    # ===================================================================
    # --- 6. LÓGICA DE FIN DE JUEGO Y ESTADO ---
    # ===================================================================

    def ha_terminado(self):
        # Verificar si alguien llegó a la meta
        for jugador in self.jugadores:
            if jugador.get_posicion() >= self.posicion_meta:
                return True
        
        # Verificar si quedan menos de 2 jugadores activos
        activos = sum(1 for j in self.jugadores if j.esta_activo())
        return activos < 2
    
    def determinar_ganador(self):
        if not self.jugadores:
            return None # No hay jugadores, no hay ganador

        # --- Loop 1: Calcular puntaje base y encontrar max_casillas ---
        max_casillas = 0
        for j in self.jugadores:
            if j.esta_activo():
                # Calcular y guardar el puntaje base (sin bonus de casilla)
                j._puntaje_base_final = self._calcular_puntaje_final_avanzado(j)
                
                # Contar tipos de casillas visitadas
                count = len(getattr(j, 'tipos_casillas_visitadas', set()))
                if count > max_casillas:
                    max_casillas = count
            else:
                # Jugadores inactivos tienen puntaje base 0
                j._puntaje_base_final = 0

        # --- Loop 2: Aplicar bonus de casilla y encontrar ganador ---
        BONUS_CASILLA = 100
        ganador_final = None
        max_score = -float('inf') # Empezar con el score más bajo posible

        for j in self.jugadores:
            # Obtener el puntaje base calculado en el loop anterior
            puntaje_final = getattr(j, '_puntaje_base_final', 0)
            
            # Aplicar el bonus si este jugador es uno de los máximos exploradores
            if max_casillas > 0 and len(getattr(j, 'tipos_casillas_visitadas', set())) == max_casillas:
                puntaje_final += BONUS_CASILLA
                # Solo añadir el evento si el juego no ha terminado aún (evita spam si se llama múltiples veces)
                if not self.fin_juego: 
                    self.eventos_turno.append(f"🏆 ¡BONUS Explorador! {j.get_nombre()} gana +{BONUS_CASILLA} puntos.")
            
            # Guardar el puntaje final CON bonus en el jugador
            j._puntaje_final_con_bonus = puntaje_final
            
            # Comprobar si este jugador es el nuevo ganador 
            if puntaje_final >= max_score: # Usar >= para manejar empates simples (último gana)
                max_score = puntaje_final
                ganador_final = j
                
        # Asegurarse de marcar el juego como terminado si aún no lo estaba
        self.fin_juego = True 
        
        return ganador_final

    def _calcular_puntaje_final_avanzado(self, jugador):
        # --- 1. PUNTUACIÓN BASE Y VELOCIDAD ---
        puntaje_energia = jugador.get_puntaje() * 1
        puntaje_posicion = jugador.get_posicion() * 1
        
        # Bono por llegar a la meta (Casilla 75)
        puntaje_meta = 100 if jugador.get_posicion() >= 75 and jugador.get_puntaje() > 0 else 0
        
        # --- 2. INTERACCIÓN Y CONFLICTO ---
        # Colisiones Causadas
        colisiones_causadas = getattr(jugador, 'colisiones_causadas', 0)
        puntaje_colisiones = colisiones_causadas * 15 
        
        # --- 3. RECURSOS E INVERSIÓN (AJUSTADO) ---
        
        # Puntos de Mando (PM) Sobrantes
        pm_sobrantes = getattr(jugador, 'pm', 0)
        puntaje_pm = pm_sobrantes * 5 
        
        # Perks Activos
        perks_activos = getattr(jugador, 'perks_activos', [])
        puntaje_perks = len(perks_activos) * 20 
        
        # --- CÁLCULO PARCIAL (Sin el Bonus de Casillas Especiales) ---
        puntaje_parcial = (
            puntaje_energia +
            puntaje_posicion +
            puntaje_meta +
            puntaje_colisiones +
            puntaje_pm +
            puntaje_perks
        )
        
        # Almacenamos el puntaje base para luego sumarle el bonus de casilla especial
        jugador._puntaje_base_final = puntaje_parcial 
        
        return puntaje_parcial
    
    def obtener_estadisticas_finales(self):
        estadisticas = []
        ganador_obj = None

        if self.ha_terminado():
            ganador_obj = self.determinar_ganador() # Obtiene el objeto JugadorWeb

            for jugador in self.jugadores:
                # Obtener el puntaje final calculado (con bonus)
                puntaje = getattr(jugador, '_puntaje_final_con_bonus', 0) 

                estadisticas.append({
                    'nombre': jugador.get_nombre(),
                    # Asegúrate de usar el puntaje final con bonus
                    '_puntaje_final_con_bonus': puntaje, 
                    # Añade otros campos que el cliente necesite para mostrar
                    'posicion': jugador.get_posicion(), 
                    'energia_final': jugador.get_puntaje(), 
                })

        # Devolver un diccionario que contenga el nombre del ganador y la lista de stats
        return {
            'ganador': ganador_obj.get_nombre() if ganador_obj else None, 
            'lista_final': estadisticas
        }

    # ===================================================================
    # --- 7. FUNCIONES DE UTILIDAD (Helpers) ---
    # ===================================================================

    def obtener_jugador_actual(self):
        if self.fin_juego or not self.jugadores or self.turno_actual >= len(self.jugadores):
            return None
        jugador_en_turno = self.jugadores[self.turno_actual]
        return jugador_en_turno
    
    def obtener_turno_actual(self):
        if self.fin_juego or not self.jugadores or self.turno_actual >= len(self.jugadores):
            print(f"--- OBTENER TURNO: Devolviendo None (fin_juego={self.fin_juego}, num_jugadores={len(self.jugadores)}, turno_idx={self.turno_actual})") # Log añadido
            return None

        # Asegurarse que el jugador en turno_actual existe y está activo
        jugador_en_turno = self.jugadores[self.turno_actual]
        if not jugador_en_turno.esta_activo():
            print(f"--- OBTENER TURNO: Jugador {jugador_en_turno.get_nombre()} inactivo, buscando siguiente...")
            return None 

        nombre_turno = jugador_en_turno.get_nombre()
        print(f"--- OBTENER TURNO --- Índice: {self.turno_actual}, Nombre: {nombre_turno}")
        return nombre_turno
    
    def obtener_estado_jugadores(self):
        return [jugador.to_dict() for jugador in self.jugadores]
    
    def obtener_estado_tablero(self):
        tablero = {}
        
        # Agregar jugadores al tablero
        for jugador in self.jugadores:
            pos = jugador.get_posicion()
            if pos not in tablero:
                tablero[pos] = {"jugadores": [], "casilla_especial": None, "energia": None}
            
            tablero[pos]["jugadores"].append({
                "nombre": jugador.get_nombre(),
                "energia": jugador.get_puntaje(),
                "activo": jugador.esta_activo()
            })
        
        # Agregar casillas especiales
        for pos, datos in self.casillas_especiales.items():
            if pos not in tablero:
                tablero[pos] = {"jugadores": [], "casilla_especial": None, "energia": None}
            tablero[pos]["casilla_especial"] = datos
        
        # Agregar packs de energía
        for pack in self.energia_packs:
            pos = pack["posicion"]
            if pack["valor"] != 0:
                if pos not in tablero:
                    tablero[pos] = {"jugadores": [], "casilla_especial": None, "energia": None}
                tablero[pos]["energia"] = pack["valor"]
        
        return tablero
    
    def marcar_jugador_inactivo(self, nombre_jugador):
        jugador = self._encontrar_jugador(nombre_jugador)
        if jugador and jugador.esta_activo():
            jugador.set_activo(False)
            jugador.efectos_activos = [] # Limpiar efectos
            self.eventos_turno.append(f"🔌 {nombre_jugador} se ha desconectado y queda inactivo.")
            print(f"--- JUGADOR INACTIVO --- Nombre: {nombre_jugador}")
            return True
        return False
        
    def _encontrar_jugador(self, nombre):
        for jugador in self.jugadores:
            if jugador.get_nombre() == nombre:
                return jugador
        return None
    
    def _verificar_efecto_activo(self, jugador, tipo_efecto):
        return any(efecto["tipo"] == tipo_efecto for efecto in jugador.efectos_activos)
    
    def _reducir_efectos_temporales(self, jugador, tipo_efecto=None, reducir_todo=True):
        nuevos_efectos = []
        efectos_a_ignorar = ['barrera'] # Efectos que NO se reducen por turno

        for efecto in jugador.efectos_activos:
            tipo = efecto.get('tipo')
            
            # Mantener efectos defensivos sin reducir
            if tipo in efectos_a_ignorar:
                nuevos_efectos.append(efecto)
                continue 

            # Reducir si es el efecto específico O si se deben reducir todos
            reducir_este = False
            if tipo_efecto and tipo == tipo_efecto: # Si buscamos uno específico
                reducir_este = True
            elif reducir_todo and tipo not in efectos_a_ignorar: # Si reducimos todos (excepto defensivos)
                reducir_este = True

            if reducir_este:
                efecto['turnos'] -= 1
            
            # Mantener el efecto solo si aún tiene turnos
            if efecto.get('turnos', 0) > 0:
                nuevos_efectos.append(efecto)
                
        jugador.efectos_activos = nuevos_efectos
    
    def _puede_ser_afectado(self, objetivo, habilidad_usada=None):
        # Verificar Anticipación PRIMERO si se pasó una habilidad ofensiva
        if habilidad_usada and habilidad_usada.tipo == "ofensiva" and "anticipacion" in objetivo.perks_activos:
            if random.random() < 0.20: 
                # Añadir evento solo si la esquiva ocurre
                self.eventos_turno.append(f"🛡️ ¡{objetivo.get_nombre()} esquivó {habilidad_usada.nombre}!")
                return False # No puede ser afectado

        # Verificar Escudo o Sombra Fugaz 
        if self._verificar_efecto_activo(objetivo, "escudo") or \
           ("sombra_fugaz" in objetivo.perks_activos and self._verificar_efecto_activo(objetivo, "invisible")):
            self.eventos_turno.append(f"🛡️ {objetivo.get_nombre()} está protegido.")
            return False

        # Si no esquivó ni estaba protegido, puede ser afectado
        return True
    
    def _remover_efecto(self, jugador, tipo_efecto):
        jugador.efectos_activos = [e for e in jugador.efectos_activos if e.get("tipo") != tipo_efecto]

