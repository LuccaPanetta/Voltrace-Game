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
import logging
import traceback
import threading

from src.core.habilidades import Habilidad, crear_habilidades, KITS_VOLTRACE
from src.core.perks import PERKS_CONFIG, obtener_perks_por_tier
from src.core.jugadores import JugadorWeb
from src.core.game_config import (
    POSICION_META,
    ENERGIA_TESORO_MENOR,
    ENERGIA_TESORO_MAYOR,
    ENERGIA_TRAMPA,
    ENERGIA_TRAMPA_PELIGROSA,
    ENERGIA_PEAJE,
    ENERGIA_CHATARRERIA_COSTO,
    VALOR_CURACION,
    DANO_BOMBA,
    DANO_FUGA_DOT,
    DURACION_FUGA,
    DURACION_ESCUDO_RONDAS,
    DURACION_BLOQUEO_RONDAS,
    RECOMPENSA_CAZA_ENERGIA,
    RECOMPENSA_CAZA_PM,
    BONUS_EXPLORADOR,
    COSTO_PACK_BASICO,
    COSTO_PACK_INTERMEDIO,
    COSTO_PACK_AVANZADO,
    MID_GAME_RONDA,
)

logger = logging.getLogger("voltrace")


class JuegoOcaWeb:

    # ===================================================================
    # --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
    # ===================================================================
    def __init__(self, jugadores_config, achievement_system=None):
        self.jugadores = []
        for config in jugadores_config:
            jugador = JugadorWeb(config["nombre"])
            jugador.kit_seleccionado = config.get("kit_id", "tactico")
            jugador.avatar_emoji = config.get("avatar_emoji", "👤")
            jugador.juego_actual = self
            self.jugadores.append(jugador)

        self.posicion_meta = POSICION_META
        self.energia_packs = []
        self.perks_ofrecidos = {config["nombre"]: set() for config in jugadores_config}
        self.casillas_especiales = {}
        self.habilidades_disponibles = crear_habilidades()
        self.ronda = 1
        self.turno_actual = 0
        self.fin_juego = False
        self.eventos_turno = []
        self.evento_global_activo = None
        self.evento_global_duracion = 0
        self.ultimo_en_mid_game = None
        self.achievement_system = achievement_system

        # Log para mostrar la configuración
        logger.info(
            f"JuegoOcaWeb iniciado - Jugadores: {len(self.jugadores)} - Turno: {self.turno_actual}"
        )

        self._crear_casillas_especiales()
        self._cargar_energia_desde_archivo()
        self._asignar_habilidades_jugadores()

    def _crear_casillas_especiales(self):
        from random import sample, choice  # Asegurarse de que están importados

        logger.debug("Creando tablero aleatorio (Casillas Únicas)")
        self.casillas_especiales = {}

        # DEFINE EL "POOL" DE CASILLAS POSIBLES
        POOL_DE_CASILLAS = [
            {
                "tipo": "tesoro",
                "simbolo": "💰",
                "valor": ENERGIA_TESORO_MENOR,
                "nombre": "Tesoro Menor",
                "id_unico": "tesoro_menor",
            },
            {
                "tipo": "trampa",
                "simbolo": "❌",
                "valor": ENERGIA_TRAMPA,
                "nombre": "Trampa de Energía",
                "id_unico": "trampa_energia",
            },
            {
                "tipo": "teletransporte",
                "simbolo": "🌀",
                "avance": (2, 5),
                "nombre": "Portal Mágico",
                "id_unico": "portal_magico",
            },
            {
                "tipo": "multiplicador",
                "simbolo": "✨",
                "nombre": "Amplificador",
                "id_unico": "amplificador",
            },
            {
                "tipo": "intercambio",
                "simbolo": "🔄",
                "nombre": "Cámara de Intercambio",
                "id_unico": "intercambio",
            },
            {
                "tipo": "tesoro",
                "simbolo": "🤑",
                "valor": ENERGIA_TESORO_MAYOR,
                "nombre": "Tesoro Mayor",
                "id_unico": "tesoro_mayor",
            },
            {
                "tipo": "pausa",
                "simbolo": "💸",
                "nombre": "Peaje Costoso",
                "id_unico": "pausa",
                "valor_energia": ENERGIA_PEAJE,
                "valor_pm": -3,
            },
            {
                "tipo": "trampa",
                "simbolo": "☠️",
                "valor": ENERGIA_TRAMPA_PELIGROSA,
                "nombre": "Trampa Peligrosa",
                "id_unico": "trampa_peligrosa",
            },
            {
                "tipo": "turbo",
                "simbolo": "⚡",
                "nombre": "Acelerador",
                "id_unico": "acelerador",
            },
            {
                "tipo": "teletransporte",
                "simbolo": "💠",
                "avance": (5, 8),
                "nombre": "Portal Avanzado",
                "id_unico": "portal_avanzado",
            },
            {
                "tipo": "vampiro",
                "simbolo": "🧛",
                "porcentaje": 15,
                "nombre": "Drenaje de Energía",
                "id_unico": "vampiro",
            },
            {
                "tipo": "rebote",
                "simbolo": "↩️",
                "nombre": "Trampolín Inverso",
                "id_unico": "rebote",
            },
            {
                "tipo": "retroceso_estrategico",
                "simbolo": "⚫",
                "nombre": "Agujero Negro",
                "id_unico": "agujero_negro",
                "retroceso": 20,
            },
            {
                "tipo": "recurso",
                "simbolo": "⭐",
                "nombre": "Pozo de PM",
                "id_unico": "pozo_pm",
            },
            {
                "tipo": "atraccion",
                "simbolo": "🧲",
                "nombre": "Imán",
                "id_unico": "iman",
            },
            {
                "tipo": "intercambio_recurso",
                "simbolo": "⚙️",
                "nombre": "Chatarrería",
                "id_unico": "chatarreria",
            },
        ]

        # DEFINE LAS POSICIONES VÁLIDAS
        posiciones_validas = list(range(4, self.posicion_meta - 1))

        # DEFINE CUÁNTAS CASILLAS QUIERES Y CUÁNTOS TIPOS ÚNICOS MÁXIMO
        CANTIDAD_ESPECIALES = 20
        MAX_TIPOS_UNICOS = len(POOL_DE_CASILLAS)  # Máximo 16 tipos únicos

        # SELECCIONAR QUÉ TIPOS DE CASILLAS VAMOS A USAR
        pool_ids_unicos = [c["id_unico"] for c in POOL_DE_CASILLAS]

        # Seleccionar al azar los tipos de casillas que usaremos, limitado por CANTIDAD_ESPECIALES
        tipos_a_usar_ids = sample(
            pool_ids_unicos, min(CANTIDAD_ESPECIALES, MAX_TIPOS_UNICOS)
        )

        # Crear un mapa de configuración basado solo en los IDs seleccionados
        tipos_config = {c["id_unico"]: c for c in POOL_DE_CASILLAS}

        # Lista final de casillas, priorizando la unicidad
        casillas_seleccionadas = []

        # Llenar con los tipos únicos
        for unique_id in tipos_a_usar_ids:
            casillas_seleccionadas.append(tipos_config[unique_id])

        # Llenar el resto de las ranuras con tipos al azar
        while len(casillas_seleccionadas) < CANTIDAD_ESPECIALES:
            casillas_seleccionadas.append(choice(POOL_DE_CASILLAS))

        # SELECCIONAR POSICIONES AL AZAR Y ASIGNAR CASILLAS
        posiciones_elegidas = sample(posiciones_validas, CANTIDAD_ESPECIALES)

        for pos, casilla_data in zip(posiciones_elegidas, casillas_seleccionadas):
            self.casillas_especiales[pos] = casilla_data.copy()

        logger.info(
            f"Tablero creado con {len(self.casillas_especiales)} casillas aleatorias únicas."
        )

    def _cargar_energia_desde_archivo(self, nombre_archivo="packenergia_75.txt"):
        ruta_archivo = os.path.join(os.path.dirname(__file__), "data", nombre_archivo)
        self.energia_packs = []
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                for linea in archivo:
                    linea = linea.strip()
                    if linea:
                        try:
                            nombre, posicion, valor = linea.split(",")
                            self.energia_packs.append(
                                {
                                    "nombre": nombre.strip(),
                                    "posicion": int(posicion.strip()),
                                    "valor": int(valor.strip()),
                                }
                            )
                        except ValueError:
                            # Ignorar líneas malformadas en modo web para robustez
                            pass
        except FileNotFoundError:
            # Fallback a packs por defecto si no existe el archivo
            packs_data = [
                (3, 70),
                (7, -30),
                (12, 80),
                (16, 50),
                (19, -40),
                (23, 90),
                (27, -50),
                (31, 60),
                (34, 120),
                (38, -60),
                (42, 80),
                (45, -70),
                (48, 100),
                (52, 70),
                (55, -80),
                (58, 110),
                (61, -40),
                (64, 90),
                (67, -90),
                (70, 150),
                (73, -100),
            ]
            self.energia_packs = [
                {"nombre": f"Pack_{i+1}", "posicion": pos, "valor": val}
                for i, (pos, val) in enumerate(packs_data)
            ]

    def _asignar_habilidades_jugadores(self):
        logger.debug("Asignando habilidades basadas en KITS seleccionados")

        # Crear un mapa de todos los objetos Habilidad por nombre
        mapa_habilidades = {}
        habilidades_por_categoria = self.habilidades_disponibles

        for categoria in habilidades_por_categoria.values():
            for habilidad_obj in categoria:
                mapa_habilidades[habilidad_obj.nombre] = habilidad_obj

        # Asignar habilidades a cada jugador según su kit
        for jugador in self.jugadores:
            # Lee el kit_id que guardamos
            kit_id = getattr(jugador, "kit_seleccionado", "tactico")
            # Obtiene la config del kit desde la constante importada
            kit_config = KITS_VOLTRACE.get(kit_id, KITS_VOLTRACE["tactico"])

            nombres_habilidades_kit = kit_config["habilidades"]

            jugador.habilidades = []  # Limpiar por si acaso

            for nombre_hab in nombres_habilidades_kit:
                habilidad_obj = mapa_habilidades.get(nombre_hab)
                if habilidad_obj:
                    jugador.habilidades.append(habilidad_obj)
                else:
                    logger.warning(
                        f"ADVERTENCIA: Habilidad '{nombre_hab}' del kit '{kit_id}' no encontrada."
                    )

            # Poner todas las habilidades asignadas en cooldown 0
            jugador.habilidades_cooldown = {h.nombre: 0 for h in jugador.habilidades}

            logger.info(
                f"Jugador {jugador.get_nombre()} recibe Kit '{kit_config['nombre']}' con {len(jugador.habilidades)} habilidades."
            )

    # ===================================================================
    # --- 2. FLUJO PRINCIPAL DEL JUEGO (EL TURNO) ---
    # ===================================================================

    def paso_1_lanzar_y_mover(self, nombre_jugador):
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador:
            return {"exito": False, "mensaje": "Jugador no encontrado"}

        # Marcar que el dado fue lanzado ANTES de cualquier otra lógica.
        if hasattr(jugador, "dado_lanzado_este_turno"):
            jugador.dado_lanzado_este_turno = True

        # Procesar Cooldowns y Efectos de Inicio de Turno
        eventos_inicio_turno = self._procesar_inicio_turno(jugador)
        self.eventos_turno = []  # Limpiar eventos
        self.eventos_turno.extend(eventos_inicio_turno)

        if jugador.oferta_perk_activa:
            if hasattr(jugador, "dado_lanzado_este_turno"):
                jugador.dado_lanzado_este_turno = False  # Revertir
            self.eventos_turno.append(f"⚠️ {nombre_jugador} debe elegir un perk.")
            return {
                "exito": False,
                "mensaje": "Debes elegir un perk de la oferta pendiente.",
                "oferta_pendiente": True,
            }

        efecto_control = self._obtener_efecto_activo(jugador, "movimiento_forzado")

        # Lógica del Dado
        dado_final = 0
        es_doble_dado = self._verificar_efecto_activo(jugador, "doble_dado")
        consecutive_sixes_count = 0

        if efecto_control:
            # CASO A: El jugador está 'Controlado'
            valor_dado_forzado = efecto_control.get(
                "dado_forzado", 1
            )  # Usar 1 si falla
            controlador = efecto_control.get("controlador", "El Titiritero")

            dado_final = valor_dado_forzado
            jugador.consecutive_sixes = 0  # No cuenta como racha

            self.eventos_turno.append(
                f"🎮 ¡Control Total! {controlador} te fuerza a moverte {dado_final} casillas."
            )

            # Consumir el efecto
            self._remover_efecto(jugador, "movimiento_forzado")

        else:
            # Comprobar "Pausa" (Sabotaje, etc.) DESPUÉS
            if self._verificar_efecto_activo(jugador, "pausa"):
                # Si está pausado, el turno termina
                self.eventos_turno.append(
                    f"⏸️ {nombre_jugador} pierde su turno por estar pausado"
                )
                self._reducir_efectos_temporales(jugador)  # Consume el turno de pausa
                self._avanzar_turno()  # Avanza el turno INMEDIATAMENTE
                return {"exito": True, "eventos": self.eventos_turno, "pausado": True}

            # Si no está ni controlado ni pausado, proceder con dado normal

            # CASO B: ¿Usó "Dado Perfecto"?
            if hasattr(jugador, "dado_forzado") and jugador.dado_forzado:
                dado1 = jugador.dado_forzado
                jugador.dado_forzado = None
                dado_final = dado1

                self.eventos_turno.append(
                    f"🎯 {nombre_jugador} usó Dado Perfecto: {dado1}"
                )
                jugador.consecutive_sixes = 0

                if "dado_cargado" in jugador.perks_activos:
                    if 1 <= dado1 <= 3:
                        energia_ganada = jugador.procesar_energia(10)
                        if energia_ganada > 0:
                            self.eventos_turno.append(
                                f"⚡ (Dado Cargado): ¡Ganas +{energia_ganada} Energía!"
                            )
                        else:
                            self.eventos_turno.append(
                                f"🚫 (Dado Cargado): Bloqueado (+10 Energía)."
                            )
                    elif 4 <= dado1 <= 6:
                        jugador.ganar_pm(1, fuente="perk_dado_cargado")
                        self.eventos_turno.append(f"✨ (Dado Cargado): ¡Ganas +1 PM!")

            # CASO C: Tirada Normal
            else:
                dado1 = randint(1, 6)
                dado_final = dado1

                if dado1 == 6:
                    jugador.consecutive_sixes += 1
                    consecutive_sixes_count = jugador.consecutive_sixes
                    if consecutive_sixes_count >= 2:
                        self.eventos_turno.append(
                            f"🔥 ¡Racha! {nombre_jugador} sacó {consecutive_sixes_count} seises seguidos."
                        )
                else:
                    jugador.consecutive_sixes = 0

                if es_doble_dado:
                    dado2 = randint(1, 6)
                    dado_final = dado1 + dado2
                    self.eventos_turno.append(
                        f"🔄 ¡Doble Turno! {nombre_jugador} sacó {dado1} + {dado2} = {dado_final}"
                    )
                else:
                    if consecutive_sixes_count < 2:
                        self.eventos_turno.append(f"{nombre_jugador} sacó {dado_final}")

        # Cálculo del Avance
        multiplicador = 2 if self._verificar_efecto_activo(jugador, "turbo") else 1
        avance_total = dado_final * multiplicador

        if multiplicador > 1 and es_doble_dado:
            self.eventos_turno.append(
                f"⚡ ¡Turbo también! ({dado_final} x 2) = {avance_total} casillas"
            )
        elif multiplicador > 1:
            self.eventos_turno.append(
                f"⚡ ¡Turbo activado! ({dado_final} x 2) = {avance_total} casillas"
            )

        # Aplicar Impulso Inestable
        if "impulso_inestable" in jugador.perks_activos:
            if random.random() < 0.50:
                avance_total += 2
                self.eventos_turno.append("🌀 Impulso Inestable: +2 casillas!")
            else:
                avance_total = max(0, avance_total - 1)
                self.eventos_turno.append("🌀 Impulso Inestable: -1 casilla!")

        # Mover y Verificar Meta
        pos_inicial = jugador.get_posicion()  # Guardamos de dónde sale
        jugador.avanzar(avance_total)
        pos_final = jugador.get_posicion()
        self.eventos_turno.append(
            f"{nombre_jugador} se mueve a la posición {pos_final}"
        )

        meta_alcanzada = False
        if pos_final >= self.posicion_meta:
            self.eventos_turno.append(f"🏆 ¡{nombre_jugador} llegó a la meta!")
            self.fin_juego = True
            meta_alcanzada = True

        # Devolver solo los datos del movimiento
        return {
            "exito": True,
            "eventos": self.eventos_turno,
            "dado": dado_final,
            "avance": avance_total,
            "pos_inicial": pos_inicial,
            "pos_final": pos_final,
            "meta_alcanzada": meta_alcanzada,
            "pausado": False,
            "consecutive_sixes": consecutive_sixes_count,
        }

    def paso_2_procesar_casilla_y_avanzar(self, nombre_jugador):
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador:
            return {"exito": False, "mensaje": "Jugador no encontrado"}

        self.eventos_turno = []  # Limpiar eventos para la 2da fase

        posicion_actual = jugador.get_posicion()

        # Ejecutar la lógica de la casilla SÓLO SI AÚN NO ESTÁ EN LA META
        if posicion_actual < self.posicion_meta:
            posicion_procesada = -1

            while (
                posicion_actual < self.posicion_meta
                and posicion_actual != posicion_procesada
            ):

                posicion_procesada = posicion_actual
                self._procesar_efectos_posicion(jugador, posicion_procesada)
                self._verificar_colision(jugador, posicion_procesada)
                posicion_actual = jugador.get_posicion()

                if posicion_actual == posicion_procesada:
                    break

        # Reducir efectos temporales
        self._reducir_efectos_temporales(jugador)

        fue_por_dado = getattr(jugador, "dado_lanzado_este_turno", False)

        fue_por_dado = getattr(jugador, "dado_lanzado_este_turno", False)

        jugador.reset_turn_flags()
        jugador.limpiar_oferta_perk()

        # Avanzar Turno SOLO SI FUE POR UN DADO
        if not self.fin_juego and fue_por_dado:
            logger.debug("Fin de Paso 2 (Dado). Avanzando turno.")
            self._avanzar_turno()
        elif not self.fin_juego:
            logger.debug("Fin de Paso 2 (Habilidad). No se avanza el turno.")

        return {"exito": True, "eventos": self.eventos_turno}

    def _procesar_inicio_turno(self, jugador):
        eventos = []

        reduccion_cooldown = 1

        logger.debug(f"Procesar Inicio Turno para: {jugador.get_nombre()}")

        # Aplicar la reducción de cooldowns
        jugador.reducir_cooldowns(turnos=reduccion_cooldown)

        efecto_fuga = next(
            (
                efecto
                for efecto in jugador.efectos_activos
                if efecto.get("tipo") == "fuga_energia"
            ),
            None,
        )
        if efecto_fuga:
            dano = efecto_fuga.get("dano", 25)
            # Aplicar daño
            cambio_energia_real = jugador.procesar_energia(-dano)

            if cambio_energia_real == 0 and dano > 0:  # Si el daño fue 0
                eventos.append(
                    f"🛡️ {jugador.get_nombre()} bloqueó el daño de Fuga de Energía."
                )
            else:
                eventos.append(
                    f"🩸 {jugador.get_nombre()} pierde {abs(cambio_energia_real)} E por Fuga de Energía."
                )

            # Comprobar si Último Aliento se activó ANTES de declarar la muerte
            if getattr(jugador, "_ultimo_aliento_usado", False) and not getattr(
                jugador, "_ultimo_aliento_notificado", False
            ):
                self.eventos_turno.append(
                    f"❤️‍🩹 ¡Último Aliento salvó a {jugador.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                )
                jugador._ultimo_aliento_notificado = True  # Marcar como notificado
            # Si no fue salvado Y está inactivo, AHORA sí mostrar mensaje de eliminación
            elif not jugador.esta_activo():
                mensaje_elim = (
                    f"💀 ¡{jugador.get_nombre()} ha sido eliminado por Fuga de Energía!"
                )
                if mensaje_elim not in self.eventos_turno:
                    self.eventos_turno.append(mensaje_elim)

        # Lógica de Recarga Constante
        if "recarga_constante" in jugador.perks_activos:
            # Solo dar energía si el jugador sigue activo DESPUÉS del daño
            if jugador.esta_activo():
                energia_ganada = jugador.procesar_energia(10)
                if energia_ganada > 0:
                    eventos.append(
                        f"🔋 Recarga Constante: +{energia_ganada} Energía aplicada."
                    )
                elif energia_ganada == 0:
                    eventos.append(f"🚫 Recarga Constante bloqueada.")
            else:
                eventos.append(f"🔋 Recarga Constante no se aplica (jugador inactivo).")

        logger.debug(
            f"Verificando efectos para {jugador.get_nombre()}: {jugador.efectos_activos}"
        )
        if self._verificar_efecto_activo(jugador, "sobrecarga_pendiente"):
            logger.debug(
                f"¡Efecto 'sobrecarga_pendiente' DETECTADO para {jugador.get_nombre()}!"
            )
            resultado_sobrecarga = random.choice([-25, 75, 150])
            logger.debug(f"Resultado Sobrecarga: {resultado_sobrecarga}")

            energia_cambio = jugador.procesar_energia(resultado_sobrecarga)

            if energia_cambio == 0 and resultado_sobrecarga > 0:
                eventos.append(
                    f"🚫🎲 Resultado Sobrecarga (+{resultado_sobrecarga}) bloqueado."
                )
            elif resultado_sobrecarga > 0:
                eventos.append(
                    f"🎲 Resultado Sobrecarga: ¡Ganaste {energia_cambio or 0} Energía!"
                )
            else:  # resultado_sobrecarga < 0
                eventos.append(
                    f"🎲 Resultado Sobrecarga: ¡Perdiste {abs(resultado_sobrecarga)} Energía!"
                )

            self._remover_efecto(jugador, "sobrecarga_pendiente")
            logger.debug(
                f"Efecto 'sobrecarga_pendiente' removido para {jugador.get_nombre()}."
            )
        else:
            logger.debug(
                f"Efecto 'sobrecarga_pendiente' NO detectado para {jugador.get_nombre()}."
            )

        return eventos

    def _procesar_efectos_posicion(self, jugador, posicion):
        # Si el jugador está en fase, ignorar efectos negativos de la casilla
        esta_en_fase = self._verificar_efecto_activo(jugador, "fase_activa")
        if self._verificar_efecto_activo(jugador, "fase_activa"):
            casilla_data_fase = self.casillas_especiales.get(posicion)
            tipo_casilla_fase = (
                casilla_data_fase.get("tipo") if casilla_data_fase else None
            )
            tipos_negativos = [
                "trampa",
                "pausa",
                "vampiro",
                "rebote",
                "intercambio_recurso",
                "retroceso_estrategico",
            ]

            if tipo_casilla_fase in tipos_negativos:
                self.eventos_turno.append(
                    f"👻 {jugador.get_nombre()} atraviesa {casilla_data_fase['nombre']} sin efecto."
                )
                energia_en_casilla = self._buscar_energia_en_posicion(jugador, posicion)
                if energia_en_casilla < 0:
                    self.eventos_turno.append(
                        f"👻 {jugador.get_nombre()} ignora el pack de {energia_en_casilla} energía."
                    )
                    # Si ignora casilla negativa, también ignora colisión
                    return  # Salir para ignorar packs negativos y colisiones
                # Si es Tesoro u otro tipo positivo/neutro, continúa

        # --- CASILLAS ESPECIALES ---
        if (
            self.evento_global_activo == "Apagón"
            and posicion in self.casillas_especiales
        ):
            self.eventos_turno.append(
                f"🌎 Apagón: Casilla '{self.casillas_especiales[posicion]['nombre']}' desactivada."
            )

        elif posicion in self.casillas_especiales:
            casilla = self.casillas_especiales[posicion]
            # Asegúrate de no procesar dos veces si ya fue manejado por la lógica de Fase
            self.eventos_turno.append(
                f"🎯 {jugador.get_nombre()} activó: {casilla['nombre']}"
            )

            tipo = casilla.get("tipo")  # Usar .get() para seguridad

            jugador.tipos_casillas_visitadas.add(casilla.get("tipo"))

            if tipo == "tesoro":
                energia_intentada = casilla["valor"]

                energia_modificada = energia_intentada  # Empezar con el valor base

                if self._verificar_efecto_activo(jugador, "multiplicador"):
                    energia_modificada *= 2
                    self.eventos_turno.append(
                        "✨ ¡Multiplicador! Valor del tesoro duplicado."
                    )
                    self._remover_efecto(jugador, "multiplicador")

                elif self.evento_global_activo == "Sobrecarga":
                    energia_modificada *= 2
                    self.eventos_turno.append(
                        "🌎 Sobrecarga: ¡Valor del tesoro duplicado!"
                    )

                if (
                    energia_intentada > 0
                    and "eficiencia_energetica" in jugador.perks_activos
                ):
                    energia_modificada = int(energia_modificada * 1.20)
                    self.eventos_turno.append(
                        "⚡ Eficiencia Energética: +20% en Tesoro!"
                    )

                energia_ganada_real = jugador.procesar_energia(energia_modificada)

                # Comprobar Bloqueo Energético antes de dar el tesoro
                if energia_ganada_real > 0:
                    self.eventos_turno.append(f"💰 +{energia_ganada_real} energía")
                    jugador.ganar_pm(
                        2, fuente="casilla_tesoro"
                    )  # PM por recoger tesoro
                    jugador.tesoros_recogidos += 1
                elif energia_intentada > 0:  # Si intentó ganar pero no pudo
                    self.eventos_turno.append(
                        f"🚫 {jugador.get_nombre()} no pudo recoger el Tesoro (+{energia_intentada} E) por Bloqueo."
                    )

            elif tipo == "trampa":
                jugador.trampas_evitadas = False
                esta_invisible_con_perk = (
                    "sombra_fugaz" in jugador.perks_activos
                    and self._verificar_efecto_activo(jugador, "invisible")
                )
                if esta_invisible_con_perk:
                    self.eventos_turno.append(
                        f"👻 {jugador.get_nombre()} atraviesa la trampa (Sombra Fugaz)."
                    )
                    return
                # Obtener valor base de la trampa
                energia_perdida_base = casilla["valor"]

                energia_perdida_final = energia_perdida_base

                # Aplicar la pérdida de energía
                jugador.procesar_energia(energia_perdida_final)
                self.eventos_turno.append(f"💀 {energia_perdida_final} energía")
                jugador_afectado = jugador
                if not jugador_afectado.esta_activo():
                    mensaje_elim = (
                        f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado!"
                    )
                    if mensaje_elim not in self.eventos_turno:
                        self.eventos_turno.append(mensaje_elim)
                elif getattr(
                    jugador_afectado, "_ultimo_aliento_usado", False
                ) and not getattr(
                    jugador_afectado, "_ultimo_aliento_notificado", False
                ):
                    self.eventos_turno.append(
                        f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                    )
                    jugador_afectado._ultimo_aliento_notificado = True

                # Lógica de Recompensa de Mina
                if casilla.get("nombre") == "Mina de Energía" and casilla.get(
                    "colocada_por"
                ):
                    nombre_propietario = casilla["colocada_por"]
                    propietario = self._encontrar_jugador(nombre_propietario)

                    if (
                        propietario
                        and "recompensa_de_mina" in propietario.perks_activos
                    ):
                        recompensa = abs(energia_perdida_final) // 2
                        if propietario.esta_activo():
                            propietario.procesar_energia(recompensa)
                            self.eventos_turno.append(
                                f"💰 Recompensa de Mina: {nombre_propietario} gana {recompensa} energía."
                            )

                    if posicion in self.casillas_especiales:
                        del self.casillas_especiales[posicion]
                        self.eventos_turno.append(
                            f"✅ Mina en pos {posicion} consumida."
                        )

                # Aplicar Perk 'Chatarrero'
                if "chatarrero" in jugador.perks_activos:
                    jugador.ganar_pm(1, fuente="perk_chatarrero")
                    self.eventos_turno.append("⚙️ +1 PM (Chatarrero)")

            elif tipo == "teletransporte":
                avance = randint(casilla["avance"][0], casilla["avance"][1])
                nueva_pos = min(jugador.get_posicion() + avance, self.posicion_meta)
                jugador.teletransportar_a(nueva_pos)
                self.eventos_turno.append(
                    f"🌀 Teletransporte: avanzas {avance} a {nueva_pos}"
                )

            elif tipo == "multiplicador":
                duracion_turnos = 1
                jugador.efectos_activos.append(
                    {"tipo": "multiplicador", "turnos": duracion_turnos}
                )
                self.eventos_turno.append(
                    f"×2 Tu próxima energía se duplicará (Efecto dura {duracion_turnos} turno)"
                )

            elif tipo == "pausa":
                energia_perdida = casilla.get("valor_energia", -75)
                pm_perdidos = casilla.get("valor_pm", -3)

                energia_perdida_real = energia_perdida

                jugador.procesar_energia(energia_perdida_real)
                self.eventos_turno.append(
                    f"💸 Peaje Costoso: Pierdes {abs(energia_perdida_real)} E."
                )

                jugador.gastar_pm(abs(pm_perdidos))
                self.eventos_turno.append(
                    f"💸 Peaje Costoso: Pierdes {abs(pm_perdidos)} PM."
                )

            elif tipo == "turbo":
                duracion_turnos = 1
                jugador.efectos_activos.append(
                    {"tipo": "turbo", "turnos": duracion_turnos}
                )
                self.eventos_turno.append(
                    f"⚡ Tu próximo movimiento se duplicará (Efecto dura {duracion_turnos} turno)"
                )

            elif tipo == "vampiro":
                drenaje = max(
                    0, jugador.get_puntaje() * casilla.get("porcentaje", 0) // 100
                )
                if drenaje > 0:
                    jugador.procesar_energia(-drenaje)
                    self.eventos_turno.append(
                        f"🧛 Pierdes {drenaje} energía ({casilla.get('porcentaje', 0)}%)"
                    )

            elif tipo == "intercambio":
                otros = [j for j in self.jugadores if j != jugador and j.esta_activo()]
                if otros:
                    objetivo = random.choice(otros)

                    pos_j_original = jugador.get_posicion()
                    pos_o_original = objetivo.get_posicion()

                    jugador.teletransportar_a(pos_o_original)
                    objetivo.teletransportar_a(pos_j_original)
                    self.eventos_turno.append(
                        f"🔄 Intercambias posición con {objetivo.get_nombre()} (al azar). Ahora estás en {pos_o_original} y {objetivo.get_nombre()} en {pos_j_original}."
                    )
                else:
                    self.eventos_turno.append("🔄 No hay nadie con quien intercambiar.")

            elif tipo == "rebote":
                retroceso = randint(5, 10)
                nueva_pos = max(1, jugador.get_posicion() - retroceso)
                if nueva_pos != jugador.get_posicion():
                    jugador.teletransportar_a(nueva_pos)
                    self.eventos_turno.append(
                        f"↩️ Rebote: retrocedes {retroceso} a {nueva_pos}"
                    )
                else:
                    self.eventos_turno.append("↩️ Rebote: Ya estás en la casilla 1.")

            elif tipo == "retroceso_estrategico":  # Agujero Negro
                retroceso_fijo = casilla.get("retroceso", 20)
                pos_actual = jugador.get_posicion()
                nueva_pos = max(1, pos_actual - retroceso_fijo)

                if nueva_pos != pos_actual:
                    jugador.teletransportar_a(nueva_pos)
                    self.eventos_turno.append(
                        f"⚫ Agujero Negro: Retrocedes {retroceso_fijo} casillas a {nueva_pos}."
                    )
                    self._verificar_colision(jugador, nueva_pos)
                else:
                    self.eventos_turno.append(
                        f"⚫ Agujero Negro: Retrocedes {pos_actual - 1} casillas a {nueva_pos}."
                    )

            elif tipo == "recurso":  # Pozo de PM
                jugador.ganar_pm(3, fuente="casilla_pozo_pm")
                self.eventos_turno.append(f"⭐ Pozo de PM: ¡Ganas +3 PM!")

            elif tipo == "atraccion":  # Imán
                self.eventos_turno.append(
                    f"🧲 Imán: Atrae a los demás jugadores 2 casillas."
                )
                pos_iman = jugador.get_posicion()

                for j in self.jugadores:
                    if j != jugador and j.esta_activo():
                        pos_actual_j = j.get_posicion()

                        if pos_actual_j > pos_iman:
                            direccion = -1
                        else:
                            direccion = 1

                        movimiento_max = 2
                        if abs(pos_actual_j - pos_iman) == 1:
                            movimiento_max = 1

                        nueva_pos = pos_actual_j + (direccion * movimiento_max)

                        if nueva_pos != pos_actual_j:
                            j.teletransportar_a(nueva_pos)
                            self.eventos_turno.append(
                                f"🧲 {j.get_nombre()} es atraído a {nueva_pos}."
                            )
                            self._procesar_efectos_posicion(j, nueva_pos)
                            self._verificar_colision(j, nueva_pos)

            elif tipo == "intercambio_recurso":  # Chatarrería
                energia_cambio = jugador.procesar_energia(ENERGIA_CHATARRERIA_COSTO)
                jugador.ganar_pm(3, fuente="casilla_chatarreria")  # Fuente específica
                self.eventos_turno.append(
                    f"⚙️ Chatarrería: Pierdes {abs(energia_cambio)} E pero ganas +3 PM."
                )

        # --- PACKS DE ENERGÍA ---
        puede_recoger_pack = True
        if esta_en_fase:
            pack_info = next(
                (
                    pack
                    for pack in self.energia_packs
                    if pack["posicion"] == posicion and pack["valor"] != 0
                ),
                None,
            )
            if pack_info and pack_info["valor"] < 0:
                self.eventos_turno.append(
                    f"👻 {jugador.get_nombre()} ignora el pack negativo (Fase)."
                )
                puede_recoger_pack = False
            elif pack_info and pack_info["valor"] > 0:
                self.eventos_turno.append(
                    f"👻 {jugador.get_nombre()} recoge pack positivo (Fase)."
                )

        energia_cambio_pack = 0
        if puede_recoger_pack:
            energia_cambio_pack = self._buscar_energia_en_posicion(jugador, posicion)

            if energia_cambio_pack < 0:
                jugador_afectado = jugador
                if not jugador_afectado.esta_activo():
                    mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por pack de energía)!"
                    if mensaje_elim not in self.eventos_turno:
                        self.eventos_turno.append(mensaje_elim)
                elif getattr(
                    jugador_afectado, "_ultimo_aliento_usado", False
                ) and not getattr(
                    jugador_afectado, "_ultimo_aliento_notificado", False
                ):
                    self.eventos_turno.append(
                        f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                    )
                    jugador_afectado._ultimo_aliento_notificado = True

    def _buscar_energia_en_posicion(self, jugador, posicion):
        for i, pack in enumerate(self.energia_packs):
            if pack["posicion"] == posicion and pack["valor"] != 0:
                energia_original = pack["valor"]
                energia_modificada = energia_original  # Valor base a intentar aplicar

                # Verificar el efecto del JUGADOR o el evento GLOBAL
                if self._verificar_efecto_activo(jugador, "multiplicador"):
                    energia_modificada *= 2
                    self.eventos_turno.append(
                        "✨ ¡Multiplicador! Valor del pack duplicado."
                    )
                    # Consumir el efecto
                    self._remover_efecto(jugador, "multiplicador")

                elif self.evento_global_activo == "Sobrecarga":
                    energia_modificada *= 2
                    self.eventos_turno.append(
                        "🌎 Sobrecarga: ¡Valor del pack duplicado!"
                    )

                # Aplicar perks que modifican el valor ANTES de procesar
                if (
                    energia_original > 0
                    and "eficiencia_energetica" in jugador.perks_activos
                ):
                    energia_modificada = int(energia_modificada * 1.20)
                    self.eventos_turno.append("⚡ Eficiencia Energética!")

                esta_invisible_con_perk = (
                    "sombra_fugaz" in jugador.perks_activos
                    and self._verificar_efecto_activo(jugador, "invisible")
                )

                if esta_invisible_con_perk and energia_modificada < 0:
                    self.eventos_turno.append(
                        f"👻 {jugador.get_nombre()} atraviesa el pack de energía negativa (Sombra Fugaz)."
                    )
                    return 0

                # Llamar a procesar_energia con el valor modificado
                energia_cambio_real = jugador.procesar_energia(energia_modificada)

                jugador.energy_packs_collected += 1

                if energia_cambio_real > 0:  # Ganó energía
                    self.eventos_turno.append(f"💚 +{energia_cambio_real} energía")
                    jugador.ganar_pm(1, fuente="pack_energia")
                elif energia_modificada > 0:  # Intentó ganar pero cambio_real fue 0
                    self.eventos_turno.append(
                        f"🚫 {jugador.get_nombre()} no pudo recoger el pack (+{energia_modificada}) por Bloqueo."
                    )
                elif energia_cambio_real < 0:  # Perdió energía
                    self.eventos_turno.append(f"💀 {energia_cambio_real} energía")
                    if "chatarrero" in jugador.perks_activos:
                        jugador.ganar_pm(1, fuente="perk_chatarrero")
                        self.eventos_turno.append("⚙️ +1 PM (Chatarrero)")

                jugador_afectado = jugador
                if not jugador_afectado.esta_activo():  # ¿Fue eliminado?
                    mensaje_elim = (
                        f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado!"
                    )
                    if mensaje_elim not in self.eventos_turno:
                        self.eventos_turno.append(mensaje_elim)
                elif getattr(
                    jugador_afectado, "_ultimo_aliento_usado", False
                ) and not getattr(
                    jugador_afectado, "_ultimo_aliento_notificado", False
                ):  # ¿Se activó Último Aliento AHORA?
                    self.eventos_turno.append(
                        f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                    )
                    jugador_afectado._ultimo_aliento_notificado = True

                # Reducir valor del pack a la mitad
                self.energia_packs[i]["valor"] = energia_original // 2
                if (
                    abs(self.energia_packs[i]["valor"]) < 10
                ):  # Si es muy bajo, eliminarlo
                    self.energia_packs[i]["valor"] = 0

                return energia_cambio_real  # Devolver el cambio real

        return 0

    def _verificar_colision(self, jugador_moviendose, posicion):
        # Comprobar si el jugador que se mueve es intangible
        esta_en_fase = self._verificar_efecto_activo(jugador_moviendose, "fase_activa")
        esta_invisible_con_perk = (
            "sombra_fugaz" in jugador_moviendose.perks_activos
            and self._verificar_efecto_activo(jugador_moviendose, "invisible")
        )

        if esta_en_fase or esta_invisible_con_perk:
            mensaje_efecto = "Fase" if esta_en_fase else "Sombra Fugaz"
            self.eventos_turno.append(
                f"👻 {jugador_moviendose.get_nombre()} atraviesa a otros jugadores sin colisión ({mensaje_efecto})."
            )
            return
        jugadores_en_posicion = []
        for jugador in self.jugadores:
            if (
                jugador != jugador_moviendose
                and jugador.get_posicion() == posicion
                and jugador.esta_activo()
            ):
                jugadores_en_posicion.append(jugador)

        if jugadores_en_posicion:
            self.eventos_turno.append("💥 ¡COLISIÓN! Todos pierden energía (o roban)")
            todos_involucrados = jugadores_en_posicion + [jugador_moviendose]

            jugador_moviendose.colisiones_causadas += 1

            # Aplicar efectos y perks
            for j_afectado in todos_involucrados:
                energia_perdida = -100  # Base
                es_el_que_se_movio = j_afectado == jugador_moviendose

                if self.evento_global_activo == "Cortocircuito":
                    energia_perdida = -150
                    if not es_el_que_se_movio:
                        self.eventos_turno.append(
                            "🌎 ¡Cortocircuito! Colisión más peligrosa."
                        )

                # Verificar si alguien tiene Presencia Intimidante
                if es_el_que_se_movio:
                    for (
                        j_estatico
                    ) in jugadores_en_posicion:  # Iterar sobre los que estaban quietos
                        if "presencia_intimidante" in j_estatico.perks_activos:
                            penalizacion_extra = 25
                            energia_perdida -= penalizacion_extra
                            self.eventos_turno.append(
                                f"  {j_estatico.get_nombre()} intimida a {j_afectado.get_nombre()} (-{penalizacion_extra} E extra)!"
                            )
                            break  # Solo se aplica una vez

                # Verificar Escudo o Amortiguación del afectado
                if self._verificar_efecto_activo(j_afectado, "escudo") or (
                    "sombra_fugaz" in j_afectado.perks_activos
                    and self._verificar_efecto_activo(j_afectado, "invisible")
                ):  # Añadir chequeo Sombra Fugaz
                    self.eventos_turno.append(
                        f"  {j_afectado.get_nombre()}: 🛡️ protegido"
                    )
                    j_afectado.ganar_pm(
                        2, fuente="colision"
                    )  # Colisión NO activa Acumulador
                    if self.achievement_system and self._verificar_efecto_activo(
                        j_afectado, "escudo"
                    ):
                        try:
                            threading.Thread(
                                target=self.achievement_system.check_achievement,
                                args=(
                                    j_afectado.get_nombre(),
                                    "game_event",
                                    {"event_name": "muralla_humana"},
                                ),
                            ).start()
                        except Exception as e:
                            logger.error(
                                f"ERROR al verificar logro 'muralla_humana' en hilo: {e}",
                                exc_info=True,
                            )

                elif "amortiguacion" in j_afectado.perks_activos:
                    energia_perdida = int(energia_perdida * 0.67)  # Pierde 67% aprox
                    self.eventos_turno.append(
                        f"  {j_afectado.get_nombre()}: Amortiguación reduce daño a {energia_perdida}"
                    )

                j_afectado.procesar_energia(energia_perdida)
                self.eventos_turno.append(
                    f"  {j_afectado.get_nombre()}: {energia_perdida} energía"
                )
                j_afectado.ganar_pm(
                    2, fuente="colision"
                )  # Colisión NO activa Acumulador

                if j_afectado == jugador_moviendose:
                    # El jugador que se mueve fue dañado. Los atacantes son los estáticos.
                    for j_atacante in jugadores_en_posicion:
                        self._procesar_recompensa_caza(
                            atacante=j_atacante, objetivo=j_afectado
                        )
                else:
                    # El jugador estático fue dañado. El atacante es el que se mueve.
                    self._procesar_recompensa_caza(
                        atacante=jugador_moviendose, objetivo=j_afectado
                    )

                # Aplicar Drenaje por Colisión
                if "drenaje_colision" in j_afectado.perks_activos:
                    energia_robada_total = 0
                    otros_en_colision = [
                        j for j in todos_involucrados if j != j_afectado
                    ]
                    for j_robado in otros_en_colision:
                        # Robar solo si el otro no está protegido
                        if not (
                            self._verificar_efecto_activo(j_robado, "escudo")
                            or (
                                "sombra_fugaz" in j_robado.perks_activos
                                and self._verificar_efecto_activo(j_robado, "invisible")
                            )
                        ):
                            energia_a_robar = min(
                                50, j_robado.get_puntaje()
                            )  # Roba hasta 50 o lo que le quede
                            j_robado.procesar_energia(-energia_a_robar)
                            energia_robada_total += energia_a_robar
                            self.eventos_turno.append(
                                f"  {j_afectado.get_nombre()} drena {energia_a_robar} a {j_robado.get_nombre()}"
                            )

                    if energia_robada_total > 0:
                        j_afectado.procesar_energia(energia_robada_total)
                        self.eventos_turno.append(
                            f"  {j_afectado.get_nombre()} recupera {energia_robada_total} por Drenaje."
                        )

    def _avanzar_turno(self):
        intentos = 0
        turno_original = self.turno_actual
        nueva_ronda = False

        logger.debug(
            f"AVANZAR TURNO - Desde: {self.jugadores[turno_original].get_nombre()} ({turno_original})"
        )

        # Bucle para encontrar el siguiente jugador activo
        while intentos < len(self.jugadores):
            nuevo_turno_idx = (self.turno_actual + 1) % len(self.jugadores)

            # Si el nuevo índice es menor que el actual,
            if nuevo_turno_idx < self.turno_actual:
                nueva_ronda = True

            self.turno_actual = nuevo_turno_idx
            # logger.debug(f"Probando índice: {self.turno_actual}...") # Descomentar si necesitas debug intenso

            if self.jugadores[self.turno_actual].esta_activo():
                logger.info(
                    f"TURNO AVANZADO A: {self.jugadores[self.turno_actual].get_nombre()} ({self.turno_actual})"
                )
                break  # Encontramos al siguiente

            intentos += 1

        # Manejo de Log
        if intentos >= len(self.jugadores):
            if self.jugadores[self.turno_actual].esta_activo():
                logger.info("AVANZAR TURNO: Solo queda 1 jugador activo.")
                # Si solo queda 1 jugador, la ronda también avanza
                nueva_ronda = True
            else:
                logger.error("ERROR AL AVANZAR TURNO: No se encontró jugador activo.")
                return  # Salir si no hay jugadores

        # Lógica de Ronda
        if nueva_ronda and self.jugadores[self.turno_actual].esta_activo():
            self.ronda += 1
            logger.info(f"--- NUEVA RONDA: {self.ronda} ---")

            for j in self.jugadores:
                j.es_caza = False

            # Asignar nueva Caza
            if self.ronda >= 5:
                jugador_lider = None
                max_pos = -1
                jugadores_activos_no_meta = [
                    j
                    for j in self.jugadores
                    if j.esta_activo() and j.get_posicion() < self.posicion_meta
                ]

                if jugadores_activos_no_meta:
                    # Encontrar al jugador con la posición más alta
                    jugador_lider = max(
                        jugadores_activos_no_meta, key=lambda x: x.get_posicion()
                    )

                if jugador_lider:
                    jugador_lider.es_caza = True
                    self.eventos_turno.append(
                        f"🎯 ¡SE BUSCA! {jugador_lider.get_nombre()} es la Caza de esta ronda. ¡Atácalo por una recompensa!"
                    )

            # Definir la ronda de "mitad de partida"
            if self.ronda == MID_GAME_RONDA and self.ultimo_en_mid_game is None:
                try:
                    jugadores_activos = [j for j in self.jugadores if j.esta_activo()]
                    if jugadores_activos:
                        # Encontrar al jugador activo con la posición más baja
                        jugador_ultimo = min(
                            jugadores_activos, key=lambda x: x.get_posicion()
                        )
                        self.ultimo_en_mid_game = jugador_ultimo.get_nombre()
                        logger.info(
                            f"LOGRO (Comeback King): {self.ultimo_en_mid_game} registrado como último en ronda {MID_GAME_RONDA}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error al registrar 'comeback_king': {e}", exc_info=True
                    )

            # Reducir duración del evento activo
            if self.evento_global_activo:
                self.evento_global_duracion -= 1
                if self.evento_global_duracion <= 0:
                    self.eventos_turno.append(
                        f"🌎 ¡Evento Global '{self.evento_global_activo}' ha terminado!"
                    )
                    self.evento_global_activo = None
                else:
                    self.eventos_turno.append(
                        f"🌎 Evento '{self.evento_global_activo}' durará {self.evento_global_duracion} ronda(s) más."
                    )

            # Activar un nuevo evento
            if (
                not self.evento_global_activo
                and self.ronda >= 5
                and self.ronda % 5 == 0
            ):
                self._activar_evento_global()

    # ===================================================================
    # --- 3. EVENTOS GLOBALES DE RONDA ---
    # ===================================================================

    def _activar_evento_global(self):
        # Lista de eventos confirmados
        eventos_posibles = [
            {"nombre": "Sobrecarga", "duracion": 2},  # Packs valen el doble
            {"nombre": "Apagón", "duracion": 1},  # Casillas especiales no funcionan
            {"nombre": "Mercado Negro", "duracion": 1},  # Perks a mitad de precio
            {"nombre": "Cortocircuito", "duracion": 2},  # Colisiones más peligrosas
            {"nombre": "Interferencia", "duracion": 1},  # No se pueden usar habilidades
        ]

        evento_elegido = random.choice(eventos_posibles)

        self.evento_global_activo = evento_elegido["nombre"]
        self.evento_global_duracion = evento_elegido["duracion"]

        logger.info(
            f"EVENTO GLOBAL ACTIVADO: {self.evento_global_activo} por {self.evento_global_duracion} rondas"
        )

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
        # Validaciones Iniciales
        self.eventos_turno = []
        jugador = self._encontrar_jugador(nombre_jugador)

        if self._verificar_efecto_activo(jugador, "pausa"):
            return {
                "exito": False,
                "mensaje": "No puedes usar habilidades mientras estás pausado.",
            }

        if not jugador:
            return {"exito": False, "mensaje": "Jugador no encontrado"}

        if self.evento_global_activo == "Interferencia":
            return {
                "exito": False,
                "mensaje": "🌎 ¡Interferencia! No se pueden usar habilidades durante este evento.",
            }

        if hasattr(jugador, "oferta_perk_activa") and jugador.oferta_perk_activa:
            return {
                "exito": False,
                "mensaje": "Debes elegir un perk de la oferta pendiente antes de usar una habilidad.",
            }

        if indice_habilidad < 1 or indice_habilidad > len(jugador.habilidades):
            return {"exito": False, "mensaje": "Índice de habilidad inválido"}

        habilidad = jugador.habilidades[
            indice_habilidad - 1
        ]  # Objeto base de la habilidad

        # Leer el cooldown ACTUAL
        cooldown_actual = jugador.habilidades_cooldown.get(habilidad.nombre, 0)
        if cooldown_actual > 0:
            return {
                "exito": False,
                "mensaje": f"Habilidad '{habilidad.nombre}' en cooldown por {cooldown_actual} turnos.",
            }

        costo_energia = getattr(habilidad, "energia_coste", 0)
        if jugador.get_puntaje() < costo_energia:
            return {
                "exito": False,
                "mensaje": f"No tienes suficiente energía. (Costo: {costo_energia} E, Tienes: {jugador.get_puntaje()} E)",
            }

        # REGLA: Prevenir Habilidad + Habilidad
        if getattr(jugador, "habilidad_usada_este_turno", False):
            return {"exito": False, "mensaje": "Ya usaste una habilidad en este turno."}

        # REGLA: Prevenir Dado + Habilidad
        if getattr(jugador, "dado_lanzado_este_turno", False):
            return {
                "exito": False,
                "mensaje": "Ya lanzaste el dado este turno. No puedes usar una habilidad.",
            }

        # Despacho a la Función Específica
        try:
            # Limpiar nombre para despacho (incluyendo tildes)
            habilidad_nombre_limpio = (
                habilidad.nombre.lower()
                .replace(" ", "_")
                .replace("é", "e")
                .replace("ó", "o")
                .replace("í", "i")
            )
            func_name = f"_hab_{habilidad_nombre_limpio}"

            dispatcher = getattr(self, func_name, None)

            if not dispatcher:
                # Log de error importante en el servidor
                logger.error(
                    f"ERROR Despacho: No se encontró la función '{func_name}' para la habilidad '{habilidad.nombre}'"
                )
                return {
                    "exito": False,
                    "mensaje": f"Habilidad '{habilidad.nombre}' no implementada correctamente en el servidor.",
                }

            # EJECUTA la función de la habilidad
            resultado_logica = dispatcher(jugador, habilidad, objetivo)

            # Usar .get() para evitar KeyError si la función no devuelve 'exito' o 'eventos'
            exito = resultado_logica.get("exito", False)
            eventos_habilidad = resultado_logica.get("eventos", [])

        except Exception as e:
            logger.error(
                f"ERROR FATAL al ejecutar lógica de {habilidad.nombre}: {e}",
                exc_info=True,
            )
            self.eventos_turno.append(f"!!! ERROR al usar {habilidad.nombre}: {e}")
            return {
                "exito": False,
                "mensaje": f"Error interno del servidor al ejecutar {habilidad.nombre}.",
            }

        # 3. Lógica de Cierre
        if exito:
            if costo_energia > 0:
                jugador.procesar_energia(-costo_energia)
            jugador.habilidades_usadas_en_partida += 1
            jugador.habilidad_usada_este_turno = True

            # Aplicar Cooldown
            if hasattr(jugador, "habilidades_cooldown"):
                # ¡Llamar a la función del jugador que aplica los perks!
                tiene_perk_enfriamiento = "enfriamiento_rapido" in jugador.perks_activos
                jugador.poner_en_cooldown(habilidad, tiene_perk_enfriamiento)

            # PM ganados
            pm_ganados_base = 1
            pm_bonus_perk = 0

            if "maestria_habilidad" in jugador.perks_activos:
                pm_bonus_perk = 2  # El perk da +2

            pm_total_ganados = pm_ganados_base + pm_bonus_perk
            jugador.ganar_pm(pm_total_ganados)  # Gana el total

            if pm_bonus_perk > 0:
                # Log específico para el perk
                self.eventos_turno.append(
                    f"✨ +{pm_bonus_perk} PM extra (Maestría de Habilidad)"
                )

            # Añadir eventos de la habilidad al log principal
            self.eventos_turno.extend(eventos_habilidad)

            # Preparar retorno
            cooldown_actual_retorno = jugador.habilidades_cooldown.get(
                habilidad.nombre, habilidad.cooldown_base
            )
            habilidad_dict_final = {
                "nombre": habilidad.nombre,
                "tipo": habilidad.tipo,
                "descripcion": habilidad.descripcion,
                "simbolo": habilidad.simbolo,
                "cooldown_base": habilidad.cooldown_base,
                "cooldown": cooldown_actual_retorno,
            }

            respuesta = {
                "exito": True,
                "eventos": self.eventos_turno,
                "habilidad": habilidad_dict_final,
            }

            # Propagar los flags especiales si existen en el resultado_logica
            if resultado_logica.get("es_movimiento"):
                respuesta["es_movimiento"] = True
                respuesta["resultado_movimiento"] = resultado_logica.get(
                    "resultado_movimiento"
                )

            elif resultado_logica.get("es_movimiento_doble"):
                respuesta["es_movimiento_doble"] = True
                respuesta["resultado_movimiento_jugador"] = resultado_logica.get(
                    "resultado_movimiento_jugador"
                )
                respuesta["resultado_movimiento_objetivo"] = resultado_logica.get(
                    "resultado_movimiento_objetivo"
                )

            elif resultado_logica.get("es_movimiento_otro"):
                respuesta["es_movimiento_otro"] = True
                respuesta["resultado_movimiento"] = resultado_logica.get(
                    "resultado_movimiento"
                )

            elif resultado_logica.get("es_movimiento_multiple"):
                respuesta["es_movimiento_multiple"] = True
                respuesta["movimientos"] = resultado_logica.get("movimientos")

            # Burbujear la celda actualizada si existe
            if resultado_logica.get("celda_actualizada"):
                respuesta["celda_actualizada"] = resultado_logica.get(
                    "celda_actualizada"
                )

            return respuesta

        else:
            # Habilidad fallida
            if eventos_habilidad:
                self.eventos_turno.extend(eventos_habilidad)

            # Usar el último evento como mensaje de error si existe, si no, un genérico
            mensaje_fallo = (
                eventos_habilidad[-1]
                if eventos_habilidad
                else f"No se pudo usar '{habilidad.nombre}'."
            )
            return {"exito": False, "mensaje": mensaje_fallo}

    def comprar_pack_perk(self, nombre_jugador, tipo_pack):
        jugador = self._encontrar_jugador(nombre_jugador)
        pm_actuales = jugador.get_pm() if jugador else 0
        if not jugador or not jugador.esta_activo():
            return {
                "exito": False,
                "mensaje": "Jugador no encontrado o inactivo",
                "oferta": [],
                "pm_restantes": pm_actuales,
            }

        if hasattr(jugador, "oferta_perk_activa") and jugador.oferta_perk_activa:
            # Si ya tiene una oferta, reenviarla al cliente para forzar la elección
            return {
                "exito": True,
                "mensaje": "Ya tienes una oferta pendiente. ¡Debes elegir un perk!",
                "oferta": jugador.oferta_perk_activa.get("oferta_detallada", []),
                "coste": jugador.oferta_perk_activa.get("coste_pagado", 0),
                "pm_restantes": jugador.get_pm(),
            }

        # Definir costes y composición de los packs
        costes = {
            "basico": COSTO_PACK_BASICO,
            "intermedio": COSTO_PACK_INTERMEDIO,
            "avanzado": COSTO_PACK_AVANZADO,
        }
        composicion = {
            "basico": {"basico": 2},
            "intermedio": {"medio": 2, "basico": 1},
            "avanzado": {"alto": 2},
        }

        if self.evento_global_activo == "Mercado Negro":
            # Reducir costes a la mitad, asegurando que sea al menos 1
            costes = {
                "basico": max(1, costes["basico"] // 2),
                "intermedio": max(1, costes["intermedio"] // 2),
                "avanzado": max(1, costes["avanzado"] // 2),
            }

        if tipo_pack not in costes:
            return {
                "exito": False,
                "mensaje": "Tipo de pack inválido",
                "oferta": [],
                "pm_restantes": jugador.get_pm(),
            }

        coste_pack = costes[tipo_pack]

        # Verificar PM ANTES de calcular la oferta
        if pm_actuales < coste_pack:
            return {
                "exito": False,
                "mensaje": f"No tienes suficientes PM ({jugador.get_pm()}/{coste_pack})",
                "oferta": [],
                "pm_restantes": jugador.get_pm(),
            }

        # Calcular la oferta ANTES de cobrar
        perks_disponibles_tier = {}
        habilidades_jugador = {h.nombre for h in jugador.habilidades}

        for tier in ["basico", "medio", "alto"]:
            perks_tier = obtener_perks_por_tier(
                tier
            )  # Usa la función importada de perks.py
            perks_disponibles_tier[tier] = []
            for perk_id in perks_tier:
                # Omitir si ya lo tiene activo
                if perk_id in jugador.perks_activos:
                    continue

                if perk_id == "descuento_habilidad":
                    # Contar cuántas habilidades ELEGIBLES tiene
                    habilidades_elegibles = [
                        h for h in jugador.habilidades if h.cooldown_base > 1
                    ]
                    # Contar cuántos descuentos ESPECÍFICOS ya tiene
                    descuentos_activos = [
                        p for p in jugador.perks_activos if p.startswith("descuento_")
                    ]

                    # Si ya tiene tantos descuentos como habilidades, no ofrecerlo
                    if len(descuentos_activos) >= len(habilidades_elegibles):
                        continue

                perk_config = PERKS_CONFIG.get(perk_id)
                if not perk_config:
                    continue

                # Leer el requisito directamente de la configuración del perk
                req_hab = perk_config.get("requires_habilidad")
                if req_hab and req_hab not in habilidades_jugador:
                    continue  # Saltar este perk si no tiene la habilidad requerida

                perks_disponibles_tier[tier].append(perk_id)

        # Seleccionar perks aleatorios según la composición del pack
        oferta_final_ids = []
        composicion_pack = composicion[tipo_pack]
        total_a_ofrecer = sum(composicion_pack.values())

        for tier, cantidad in composicion_pack.items():
            candidatos = perks_disponibles_tier.get(tier, [])
            # Evitar seleccionar el mismo ID dos veces si hay pocos candidatos
            candidatos_validos = [
                pid for pid in candidatos if pid not in oferta_final_ids
            ]
            cantidad_real = min(cantidad, len(candidatos_validos))
            if cantidad_real > 0:
                elegidos = random.sample(candidatos_validos, cantidad_real)
                oferta_final_ids.extend(elegidos)

        # Rellenar si faltan perks
        tiers_alternativos = ["basico", "medio", "alto"]
        random.shuffle(tiers_alternativos)
        while len(oferta_final_ids) < total_a_ofrecer:
            relleno_encontrado = False
            for tier_alt in tiers_alternativos:
                # Candidatos alternativos que no estén ya en la oferta
                candidatos_alt = [
                    pid
                    for pid in perks_disponibles_tier.get(tier_alt, [])
                    if pid not in oferta_final_ids
                ]
                if candidatos_alt:
                    oferta_final_ids.append(random.choice(candidatos_alt))
                    relleno_encontrado = True
                    break  # Salir del loop de tiers alternativos al encontrar uno
            if not relleno_encontrado:
                break  # Salir del while si no quedan candidatos en ningún tier

        # Comprobar si la oferta está vacía
        if len(oferta_final_ids) == 0:
            # No cobrar PM y devolver error
            return {
                "exito": False,
                "mensaje": "¡Ya posees todos los perks disponibles de este pack!",
                "oferta": [],
                "pm_restantes": jugador.get_pm(),
            }

        # Cobrar los PM
        if not jugador.gastar_pm(coste_pack):
            return {
                "exito": False,
                "mensaje": f"No tienes suficientes PM ({jugador.get_pm()}/{coste_pack})",
                "oferta": [],
                "pm_restantes": jugador.get_pm(),
            }

        self.eventos_turno.append(
            f"💰 {nombre_jugador} gastó {coste_pack} PM en un Pack {tipo_pack.capitalize()}."
        )

        perks_disponibles_tier = {}
        habilidades_jugador = {h.nombre for h in jugador.habilidades}

        for tier in ["basico", "medio", "alto"]:
            perks_tier = obtener_perks_por_tier(
                tier
            )  # Usa la función importada de perks.py
            perks_disponibles_tier[tier] = []
            for perk_id in perks_tier:
                # Omitir si ya lo tiene activo
                if perk_id in jugador.perks_activos:
                    continue

                if perk_id == "descuento_habilidad":
                    # Contar cuántas habilidades ELEGIBLES tiene
                    habilidades_elegibles = [
                        h for h in jugador.habilidades if h.cooldown_base > 1
                    ]
                    # Contar cuántos descuentos ESPECÍFICOS ya tiene
                    descuentos_activos = [
                        p for p in jugador.perks_activos if p.startswith("descuento_")
                    ]

                    # Si ya tiene tantos descuentos como habilidades, no ofrecerlo
                    if len(descuentos_activos) >= len(habilidades_elegibles):
                        continue

                perk_config = PERKS_CONFIG.get(perk_id)
                if not perk_config:
                    continue

                # Leer el requisito directamente de la configuración del perk
                req_hab = perk_config.get("requires_habilidad")
                if req_hab and req_hab not in habilidades_jugador:
                    continue  # Saltar este perk si no tiene la habilidad requerida

                perks_disponibles_tier[tier].append(perk_id)

        # Seleccionar perks aleatorios según la composición del pack
        oferta_final_ids = []
        composicion_pack = composicion[tipo_pack]
        total_a_ofrecer = sum(composicion_pack.values())

        for tier, cantidad in composicion_pack.items():
            candidatos = perks_disponibles_tier.get(tier, [])
            # Evitar seleccionar el mismo ID dos veces si hay pocos candidatos
            candidatos_validos = [
                pid for pid in candidatos if pid not in oferta_final_ids
            ]
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
                candidatos_alt = [
                    pid
                    for pid in perks_disponibles_tier.get(tier_alt, [])
                    if pid not in oferta_final_ids
                ]
                if candidatos_alt:
                    oferta_final_ids.append(random.choice(candidatos_alt))
                    relleno_encontrado = True
                    break  # Salir del loop de tiers alternativos al encontrar uno
            if not relleno_encontrado:
                break  # Salir del while si no quedan candidatos en ningún tier

        # Preparar la oferta detallada para el cliente
        oferta_detallada = []
        for perk_id in oferta_final_ids:
            perk_data = PERKS_CONFIG.get(perk_id)
            if perk_data:
                # Copiar para no modificar el original y añadir 'id'
                perk_info_oferta = perk_data.copy()
                perk_info_oferta["id"] = perk_id
                oferta_detallada.append(perk_info_oferta)

        # Mensaje de oferta
        mensaje_oferta = (
            f"Elige 1 Perk del Pack {tipo_pack.capitalize()} (Coste: {coste_pack} PM):"
        )
        if tipo_pack == "avanzado" and len(oferta_detallada) == 2:
            mensaje_oferta = f"Elige 1 Perk del Pack Avanzado (Coste: {coste_pack} PM): Se ofrecen 2 de Tier Alto."
        elif len(oferta_detallada) < total_a_ofrecer:
            mensaje_oferta += " (Algunos perks no estaban disponibles o ya los tienes)"

        # Guardar la oferta pendiente en el jugador
        if hasattr(jugador, "oferta_perk_activa"):
            jugador.oferta_perk_activa = {
                "oferta_detallada": oferta_detallada,
                "coste_pagado": coste_pack,
            }

        # Devolver éxito, oferta, coste original Y PM restantes
        return {
            "exito": True,
            "mensaje": mensaje_oferta,
            "oferta": oferta_detallada,
            "coste": coste_pack,
            "pm_restantes": jugador.get_pm(),
        }

    def activar_perk_seleccionado(self, nombre_jugador, perk_id, coste_esperado_pack):
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador or not jugador.esta_activo():
            # Devuelve los PM actuales si el jugador no es válido
            pm_actuales = jugador.get_pm() if jugador else 0
            return {
                "exito": False,
                "mensaje": "Jugador no encontrado o inactivo",
                "pm_restantes": pm_actuales,
            }

        perk_config = PERKS_CONFIG.get(perk_id)
        if not perk_config:
            jugador.ganar_pm(coste_esperado_pack)
            self.eventos_turno.append(
                f"⚠️ Error: Perk {perk_id} inválido. {coste_esperado_pack} PM devueltos."
            )
            return {
                "exito": False,
                "mensaje": "Perk seleccionado inválido. PM devueltos.",
                "pm_restantes": jugador.get_pm(),
            }

        mensaje_exito = ""

        # Lógica de activación
        if perk_id == "descuento_habilidad":
            descuentos_activos = {
                p for p in jugador.perks_activos if p.startswith("descuento_")
            }

            habilidades_candidatas = []
            for h in jugador.habilidades:
                if h.cooldown_base > 1:
                    # Crear el ID del perk de descuento para esta habilidad
                    perk_id_habilidad = (
                        f"descuento_{h.nombre.lower().replace(' ', '_')}"
                    )
                    # Añadir solo si NO está en la lista de descuentos activos
                    if perk_id_habilidad not in descuentos_activos:
                        habilidades_candidatas.append(h)

            if habilidades_candidatas:
                habilidad_afectada = random.choice(habilidades_candidatas)
                # Guardar el perk con la habilidad afectada
                perk_activado_id = (
                    f"descuento_{habilidad_afectada.nombre.lower().replace(' ', '_')}"
                )
                jugador.perks_activos.append(perk_activado_id)
                mensaje_exito = f"¡Perk '{perk_config['nombre']}' activado para {habilidad_afectada.nombre}!"
                self.eventos_turno.append(
                    f"⭐ {nombre_jugador} activó: Descuento (-1 CD a {habilidad_afectada.nombre})"
                )
            else:
                # Si no hay habilidades elegibles, devolver PM
                jugador.ganar_pm(coste_esperado_pack)
                self.eventos_turno.append(
                    f"⚠️ No hay habilidades elegibles para Descuento. {coste_esperado_pack} PM devueltos."
                )
                return {
                    "exito": False,
                    "mensaje": "No tienes habilidades elegibles para 'Descuento'. PM devueltos.",
                    "pm_restantes": jugador.get_pm(),
                }
        else:
            # Perks normales
            jugador.perks_activos.append(perk_id)
            mensaje_exito = f"¡Perk '{perk_config['nombre']}' activado!"
            self.eventos_turno.append(
                f"⭐ {nombre_jugador} activó el Perk: {perk_config['nombre']}"
            )

        jugador.oferta_perk_activa = None

        # Devolver éxito y PM actualizados
        return {
            "exito": True,
            "mensaje": mensaje_exito,
            "pm_restantes": jugador.get_pm(),
        }

    def _cancelar_oferta_perk(self, nombre_jugador):
        jugador = self._encontrar_jugador(nombre_jugador)
        if not jugador:
            return {"exito": False, "pm_restantes": 0}

        oferta_activa = getattr(jugador, "oferta_perk_activa", None)

        if oferta_activa:
            coste_pagado = oferta_activa.get("coste_pagado", 0)
            if coste_pagado > 0:
                # Devolver los PM
                jugador.ganar_pm(coste_pagado, fuente="reembolso_perk")
                self.eventos_turno.append(
                    f"↩️ Oferta de perk cancelada. {coste_pagado} PM devueltos a {nombre_jugador}."
                )

            # Limpiar la oferta
            jugador.limpiar_oferta_perk()  # Llama a jugador.oferta_perk_activa = None

            return {
                "exito": True,
                "pm_restantes": jugador.get_pm(),
                "mensaje": "Oferta cancelada. PM devueltos.",
            }

        # No había oferta activa, no hacer nada
        return {"exito": True, "pm_restantes": jugador.get_pm()}

    # ===================================================================
    # --- 5. LÓGICA DE HABILIDADES ---
    # ===================================================================

    def _hab_transferencia_de_fase(self, jugador, habilidad, objetivo):
        eventos = []
        duracion_turnos = 1
        jugador.efectos_activos.append(
            {"tipo": "fase_activa", "turnos": duracion_turnos}
        )
        eventos.append(
            "👻 Transferencia de Fase: Serás intangible e inmune a casillas negativas en tu próximo movimiento de dado."
        )
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

        if not self._puede_ser_afectado(jugador_objetivo, habilidad):
            return {"exito": False, "eventos": self.eventos_turno}

        # Comprobar protecciones
        if self._verificar_efecto_activo(jugador_objetivo, "escudo"):
            self._reducir_efectos_temporales(
                jugador_objetivo, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(
                f"🛡️ {jugador_objetivo.get_nombre()} bloqueó el Bloqueo Energético."
            )
            return {"exito": False, "eventos": eventos}

        elif self._verificar_efecto_activo(jugador_objetivo, "barrera"):
            self._remover_efecto(
                jugador_objetivo, "barrera"
            )  # Barrera se consume pero no refleja
            eventos.append(
                f"🔮 {jugador_objetivo.get_nombre()} disipó el Bloqueo Energético con Barrera."
            )
            return {"exito": False, "eventos": eventos}

        # Aplicar el efecto de bloqueo
        rondas_duracion = DURACION_BLOQUEO_RONDAS
        turnos_duracion = rondas_duracion * len(self.jugadores)
        jugador_objetivo.efectos_activos.append(
            {"tipo": "bloqueo_energia", "turnos": turnos_duracion}
        )
        eventos.append(
            f"🚫 {jugador_objetivo.get_nombre()} no podrá ganar energía durante {rondas_duracion} rondas."
        )

        return {"exito": True, "eventos": eventos}

    def _hab_sobrecarga_inestable(self, jugador, habilidad, objetivo):
        eventos = []
        costo_real = getattr(habilidad, "energia_coste", 50)  # Lee el costo real
        eventos.append(
            f"🎲 Sobrecarga Inestable: Pagaste {costo_real} E. El resultado se aplicará en tu próximo turno."
        )

        duracion_turnos = 1
        jugador.efectos_activos.append(
            {"tipo": "sobrecarga_pendiente", "turnos": duracion_turnos}
        )

        return {"exito": True, "eventos": eventos}

    def _hab_sabotaje(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)
        if not obj:
            eventos.append("Objetivo inválido.")
            return {"exito": False, "eventos": eventos}

        # Verificar Invisibilidad/Anticipación
        if not self._puede_ser_afectado(obj, habilidad):
            # _puede_ser_afectado ya añade el evento
            return {"exito": False, "eventos": self.eventos_turno}

        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(f"🛡️ {obj.get_nombre()} bloqueó el Sabotaje con su escudo.")
            return {"exito": False, "eventos": eventos}

        if self._verificar_efecto_activo(obj, "barrera"):
            eventos.append(f"🔮 {obj.get_nombre()} refleja el Sabotaje.")
            self._remover_efecto(obj, "barrera")  # Barrera se consume

            # Aplicar efecto al ATACANTE
            rondas_pausa = 2 if "sabotaje_persistente" in jugador.perks_activos else 1
            turnos_pausa_total = rondas_pausa

            # Verificar si el ATACANTE está protegido
            if self._verificar_efecto_activo(jugador, "escudo"):
                self._reducir_efectos_temporales(
                    jugador, tipo_efecto="escudo", reducir_todo=False
                )
                eventos.append(
                    f"🛡️ ¡Pero {jugador.get_nombre()} bloqueó el efecto reflejado con Escudo!"
                )
            elif self._verificar_efecto_activo(jugador, "invisible"):
                eventos.append(
                    f"👻 ¡Pero {jugador.get_nombre()} evitó el efecto reflejado (Invisible)!"
                )
            else:
                # Aplicar efecto al atacante
                jugador.efectos_activos.append(
                    {"tipo": "pausa", "turnos": turnos_pausa_total}
                )
                eventos.append(
                    f"⚔️ ¡{jugador.get_nombre()} se auto-saboteó y perderá {rondas_pausa} turno(s)!"
                )

            return {
                "exito": True,
                "eventos": eventos,
                "reflejo_exitoso": True,
                "jugador_reflejo": obj.get_nombre(),
            }

        # Verificar Escudo
        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(f"🛡️ {obj.get_nombre()} bloqueó el Sabotaje con su escudo.")
            return {"exito": False, "eventos": eventos}

        # Aplicar efecto
        rondas_pausa = 2 if "sabotaje_persistente" in jugador.perks_activos else 1
        turnos_pausa_total = rondas_pausa
        obj.efectos_activos.append({"tipo": "pausa", "turnos": turnos_pausa_total})
        eventos.append(
            f"⚔️ {obj.get_nombre()} perderá su{'s próximos' if rondas_pausa > 1 else ' próximo'} {rondas_pausa} turno{'s' if rondas_pausa > 1 else ''}!"
        )
        return {"exito": True, "eventos": eventos}

    def _hab_bomba_energetica(self, jugador, habilidad, objetivo):
        eventos = []
        pos_j = jugador.get_posicion()
        rango_bomba = 5 if "bomba_fragmentacion" in jugador.perks_activos else 3
        dano_bomba = DANO_BOMBA  # Daño base
        afectados, protegidos = [], []
        reflejo_ocurrido = False
        jugadores_reflejo = []

        for j in self.jugadores:
            # Iterar sobre cada jugador 'j' que NO es el lanzador
            if (
                j != jugador
                and j.esta_activo()
                and abs(j.get_posicion() - pos_j) <= rango_bomba
            ):

                # Verificar si 'j' puede ser afectado
                if self._puede_ser_afectado(j, habilidad):
                    # Comprobar Barrera
                    if self._verificar_efecto_activo(j, "barrera"):
                        eventos.append(
                            f"🔮 {j.get_nombre()} refleja el daño de la Bomba."
                        )
                        self._remover_efecto(j, "barrera")  # Barrera se consume
                        reflejo_ocurrido = True
                        jugadores_reflejo.append(j.get_nombre())

                        if self._verificar_efecto_activo(jugador, "escudo"):
                            self._reducir_efectos_temporales(
                                jugador, tipo_efecto="escudo", reducir_todo=False
                            )
                            eventos.append(
                                f"🛡️ {jugador.get_nombre()} bloqueó el daño reflejado con Escudo."
                            )
                        elif self._verificar_efecto_activo(jugador, "invisible"):
                            eventos.append(
                                f"👻 {jugador.get_nombre()} evitó el daño reflejado (Invisible)."
                            )
                        else:
                            # Si el atacante no tiene defensas, aplicar daño reflejado
                            energia_cambio_reflejo = jugador.procesar_energia(
                                -dano_bomba
                            )
                            eventos.append(
                                f"💥 ¡Recibes {energia_cambio_reflejo} de daño reflejado!"
                            )

                            # Comprobar muerte/último aliento del ATACANTE
                            jugador_afectado = jugador
                            if not jugador_afectado.esta_activo():
                                mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por reflejo de Bomba)!"
                                if mensaje_elim not in self.eventos_turno:
                                    self.eventos_turno.append(mensaje_elim)
                            elif getattr(
                                jugador_afectado, "_ultimo_aliento_usado", False
                            ) and not getattr(
                                jugador_afectado, "_ultimo_aliento_notificado", False
                            ):
                                self.eventos_turno.append(
                                    f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                                )
                                jugador_afectado._ultimo_aliento_notificado = True
                        continue  # Pasar al siguiente jugador

                    # Comprobar Escudo (bloquea el daño)
                    elif self._verificar_efecto_activo(j, "escudo"):
                        protegidos.append(j.get_nombre())
                        self._reducir_efectos_temporales(
                            j, tipo_efecto="escudo", reducir_todo=False
                        )
                        eventos.append(f"🛡️ {j.get_nombre()} bloqueó la Bomba.")
                        continue  # Pasar al siguiente jugador

                    # Si no está protegido, aplicar daño
                    else:
                        energia_cambio_directo = j.procesar_energia(-dano_bomba)
                        self._procesar_recompensa_caza(atacante=jugador, objetivo=j)
                        afectados.append(
                            j.get_nombre()
                        )  # Añadir a afectados ANTES de verificar eliminación

                        jugador_afectado = j
                        if not jugador_afectado.esta_activo():
                            mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por Bomba)!"
                            if mensaje_elim not in self.eventos_turno:
                                self.eventos_turno.append(mensaje_elim)
                        elif getattr(
                            jugador_afectado, "_ultimo_aliento_usado", False
                        ) and not getattr(
                            jugador_afectado, "_ultimo_aliento_notificado", False
                        ):
                            self.eventos_turno.append(
                                f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                            )
                            jugador_afectado._ultimo_aliento_notificado = True

                        # Lógica de empuje (Bomba Fragmentación) - Solo si el objetivo aún está activo
                        if (
                            "bomba_fragmentacion" in jugador.perks_activos
                            and jugador_afectado.esta_activo()
                        ):
                            empuje = 1
                            if "desvio_cinetico" in j.perks_activos:
                                empuje = 0  # Anula empuje

                            if empuje > 0:
                                direccion = 1 if j.get_posicion() > pos_j else -1
                                pos_nueva_empujon = max(
                                    1,
                                    min(
                                        j.get_posicion() + (direccion * empuje),
                                        self.posicion_meta,
                                    ),
                                )
                                if pos_nueva_empujon != j.get_posicion():
                                    j.teletransportar_a(pos_nueva_empujon)
                                    eventos.append(
                                        f"💨 {j.get_nombre()} es empujado a {pos_nueva_empujon}."
                                    )
                                    # Procesar efectos/colisión en la nueva casilla
                                    self._procesar_efectos_posicion(
                                        j, pos_nueva_empujon
                                    )
                                    self._verificar_colision(j, pos_nueva_empujon)
                else:
                    # Si _puede_ser_afectado devolvió False
                    protegidos.append(j.get_nombre())

        if afectados:
            eventos.append(
                f"💥 Afectados por Bomba: {', '.join(afectados)} (-{dano_bomba} E)"
            )
        if protegidos:
            eventos.append(f"🛡️/👻 Protegidos/Esquivaron Bomba: {', '.join(protegidos)}")

        return {
            "exito": True,
            "eventos": eventos,
            "afectados_count": len(afectados),
            "reflejo_exitoso": reflejo_ocurrido,
            "jugadores_reflejo": jugadores_reflejo,
        }

    def _hab_robo(self, jugador, habilidad, objetivo):
        eventos = []
        otros = [j for j in self.jugadores if j != jugador and j.esta_activo()]
        if not otros:
            eventos.append("No hay otros jugadores activos para robar.")
            return {"exito": False, "eventos": eventos}

        # Roba al más rico
        obj = max(otros, key=lambda x: x.get_puntaje())

        # Verificar si el objetivo puede ser afectado
        if not self._puede_ser_afectado(obj, habilidad):
            return {"exito": False, "eventos": self.eventos_turno}

        # Calcular cantidad a robar
        cantidad_base = randint(50, 150)
        cantidad_robo = (
            cantidad_base + 30
            if "robo_oportunista" in jugador.perks_activos
            else cantidad_base
        )
        energia_a_robar = min(
            cantidad_robo, obj.get_puntaje()
        )  # No robar más de lo que tiene

        if energia_a_robar <= 0:
            eventos.append(f"{obj.get_nombre()} no tiene energía para robar.")
            return {"exito": False, "eventos": eventos}

        if self._verificar_efecto_activo(obj, "escudo"):
            eventos.append(f"🛡️ {obj.get_nombre()} bloqueó el Robo (Escudo consumido).")
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            return {"exito": False, "eventos": eventos}  # Robo fallido por escudo

        # Comprobar Barrera del objetivo
        if self._verificar_efecto_activo(obj, "barrera"):
            eventos.append(f"🔮 {obj.get_nombre()} refleja el Robo.")
            self._remover_efecto(obj, "barrera")  # Barrera se consume

            # Comprobar defensas del ATACANTE
            if self._verificar_efecto_activo(jugador, "escudo"):
                self._reducir_efectos_temporales(
                    jugador, tipo_efecto="escudo", reducir_todo=False
                )
                eventos.append(
                    f"🛡️ {jugador.get_nombre()} bloqueó el daño reflejado con Escudo."
                )
            elif self._verificar_efecto_activo(jugador, "invisible"):
                eventos.append(
                    f"👻 {jugador.get_nombre()} evitó el daño reflejado (Invisible)."
                )
            else:
                # Aplicar daño reflejado
                energia_cambio_reflejo = jugador.procesar_energia(-energia_a_robar)
                eventos.append(
                    f"💥 ¡Recibes {energia_cambio_reflejo} de daño reflejado!"
                )

                # Comprobar muerte/último aliento del ATACANTE
                jugador_afectado = jugador
                if not jugador_afectado.esta_activo():
                    mensaje_elim = f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por reflejo de Robo)!"
                    if mensaje_elim not in self.eventos_turno:
                        self.eventos_turno.append(mensaje_elim)
                elif getattr(
                    jugador_afectado, "_ultimo_aliento_usado", False
                ) and not getattr(
                    jugador_afectado, "_ultimo_aliento_notificado", False
                ):
                    self.eventos_turno.append(
                        f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                    )
                    jugador_afectado._ultimo_aliento_notificado = True

            return {
                "exito": True,
                "eventos": eventos,
                "reflejo_exitoso": True,
                "jugador_reflejo": obj.get_nombre(),
            }

        # Si no está protegido, realizar el robo
        else:
            # Quitar energía al objetivo
            obj.procesar_energia(-energia_a_robar)

            # Dar energía al atacante
            energia_cambio_jugador = jugador.procesar_energia(energia_a_robar)

            self._procesar_recompensa_caza(atacante=jugador, objetivo=obj)

            if energia_cambio_jugador > 0:
                eventos.append(
                    f"🎭 Robas {energia_cambio_jugador} energía a {obj.get_nombre()}."
                )
            elif energia_a_robar > 0:  # Si intentó ganar pero cambio_real fue 0
                eventos.append(
                    f"🚫 {jugador.get_nombre()} no pudo recibir la energía robada por Bloqueo."
                )

            # Comprobar muerte/último aliento del OBJETIVO
            jugador_afectado = obj
            if not jugador_afectado.esta_activo():
                mensaje_elim = (
                    f"💀 ¡{jugador_afectado.get_nombre()} ha sido eliminado (por Robo)!"
                )
                if mensaje_elim not in self.eventos_turno:
                    self.eventos_turno.append(mensaje_elim)
            elif getattr(
                jugador_afectado, "_ultimo_aliento_usado", False
            ) and not getattr(jugador_afectado, "_ultimo_aliento_notificado", False):
                self.eventos_turno.append(
                    f"❤️‍🩹 ¡Último Aliento salvó a {jugador_afectado.get_nombre()}! Sobrevive con 50 E y Escudo (3 Turnos)."
                )
                jugador_afectado._ultimo_aliento_notificado = True

            return {"exito": True, "eventos": eventos}

    def _hab_tsunami(self, jugador, habilidad, objetivo):
        eventos = []
        # El perk 'maremoto' pertenece al LANZADOR y define el empuje base
        empuje_base = 5 if "maremoto" in jugador.perks_activos else 3
        afectados = []

        movimientos_planificados = []  # Lista para guardar los movimientos

        for j in self.jugadores:
            # Solo afectar a jugadores activos
            if j.esta_activo():

                pos_inicial_j = j.get_posicion()  # Guardar pos inicial

                empuje_final_jugador = empuje_base

                # Comprobar si el OBJETIVO tiene el perk "Desvío Cinético"
                if "desvio_cinetico" in j.perks_activos:
                    reduccion = empuje_final_jugador // 2
                    empuje_final_jugador -= reduccion
                    eventos.append(
                        f"🏃‍♂️ {j.get_nombre()} desvía parte del Tsunami (Empuje reducido a {empuje_final_jugador})."
                    )

                # Aplicar el empuje final calculado para este jugador 'j'
                nueva = max(1, j.get_posicion() - empuje_final_jugador)

                if nueva != j.get_posicion():
                    j.teletransportar_a(nueva)
                    afectados.append(f"{j.get_nombre()} a {nueva}")

                    # Añadir a la lista de movimientos para la animación
                    movimientos_planificados.append(
                        {
                            "jugador": j.get_nombre(),
                            "pos_inicial": pos_inicial_j,
                            "pos_final": nueva,
                            "meta_alcanzada": False,  # Tsunami no puede llevar a la meta
                            "dado": empuje_final_jugador,
                        }
                    )

                    # Procesar efectos/colisión en la nueva casilla SIEMPRE después del movimiento
                    self._procesar_efectos_posicion(j, nueva)
                    self._verificar_colision(j, nueva)

        if afectados:
            eventos.append(
                f"🌊 Tsunami empuja (máx {empuje_base} casillas): {', '.join(afectados)}"
            )
        else:
            eventos.append("🌊 Tsunami no afectó a nadie.")

        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento_multiple": True,
            "movimientos": movimientos_planificados,
        }

    def _hab_fuga_de_energia(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)
        if not obj:
            eventos.append("Objetivo inválido.")
            return {"exito": False, "eventos": eventos}

        # Verificar si el objetivo puede ser afectado (Invisibilidad, etc.)
        if not self._puede_ser_afectado(obj, habilidad):
            return {"exito": False, "eventos": self.eventos_turno}

        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(
                f"🛡️ {obj.get_nombre()} bloqueó la Fuga de Energía con su escudo."
            )
            return {"exito": False, "eventos": eventos}

        # Verificar Barrera
        if self._verificar_efecto_activo(obj, "barrera"):
            eventos.append(f"🔮 {obj.get_nombre()} refleja la Fuga de Energía.")
            self._remover_efecto(obj, "barrera")  # Barrera se consume

            # Aplicar efecto al ATACANTE
            duracion_dot = DURACION_FUGA  # Turnos del jugador
            dano_dot = DANO_FUGA_DOT

            # Verificar si el ATACANTE está protegido
            if self._verificar_efecto_activo(jugador, "escudo"):
                self._reducir_efectos_temporales(
                    jugador, tipo_efecto="escudo", reducir_todo=False
                )
                eventos.append(
                    f"🛡️ ¡Pero {jugador.get_nombre()} bloqueó el efecto reflejado con Escudo!"
                )
            elif self._verificar_efecto_activo(jugador, "invisible"):
                eventos.append(
                    f"👻 ¡Pero {jugador.get_nombre()} evitó el efecto reflejado (Invisible)!"
                )
            else:
                jugador.efectos_activos.append(
                    {"tipo": "fuga_energia", "turnos": duracion_dot, "dano": dano_dot}
                )
                eventos.append(
                    f"🩸 ¡{jugador.get_nombre()} se auto-infligió Fuga de Energía!"
                )

            return {
                "exito": True,
                "eventos": eventos,
                "reflejo_exitoso": True,
                "jugador_reflejo": obj.get_nombre(),
            }

        # Verificar Escudo
        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(
                f"🛡️ {obj.get_nombre()} bloqueó la Fuga de Energía con su escudo."
            )
            return {"exito": False, "eventos": eventos}

        # Aplicar efecto
        duracion_dot = 3
        dano_dot = 25
        obj.efectos_activos.append(
            {"tipo": "fuga_energia", "turnos": duracion_dot, "dano": dano_dot}
        )
        self._procesar_recompensa_caza(atacante=jugador, objetivo=obj)
        eventos.append(
            f"🩸 {obj.get_nombre()} sufre una Fuga de Energía. Perderá {dano_dot} E durante {duracion_dot} turnos."
        )
        return {"exito": True, "eventos": eventos}

    def _hab_escudo_total(self, jugador, habilidad, objetivo):
        eventos = []
        rondas_duracion = DURACION_ESCUDO_RONDAS  # Duración base

        if "escudo_duradero" in jugador.perks_activos:
            rondas_duracion += 1
            eventos.append("🛡️ Escudo Duradero: ¡El escudo durará 1 ronda adicional!")

        turnos_duracion = rondas_duracion * len(self.jugadores)
        jugador.efectos_activos.append({"tipo": "escudo", "turnos": turnos_duracion})
        eventos.append(
            f"🛡️ ¡Protección activada por {rondas_duracion} rondas ({turnos_duracion} turnos)!"
        )
        return {"exito": True, "eventos": eventos}

    def _hab_curacion(self, jugador, habilidad, objetivo):
        eventos = []
        energia_intentada = VALOR_CURACION
        energia_antes = jugador.get_puntaje()
        energia_ganada_real = jugador.procesar_energia(energia_intentada)
        if energia_ganada_real > 0:
            eventos.append(f"🏥 +{energia_ganada_real} energía")
        elif energia_intentada > 0:
            eventos.append(f"🚫 Curación bloqueada para {jugador.get_nombre()}.")
        return {"exito": True, "eventos": eventos, "energia_antes": energia_antes}

    def _hab_invisibilidad(self, jugador, habilidad, objetivo):
        eventos = []
        jugador.efectos_activos.append({"tipo": "invisible", "turnos": 2})
        eventos.append("👻 Invisible por 2 turnos (Evita ser objetivo de habilidades).")
        return {"exito": True, "eventos": eventos}

    def _hab_barrera(self, jugador, habilidad, objetivo):
        eventos = []
        jugador.efectos_activos.append({"tipo": "barrera", "turnos": 2})
        eventos.append("🔮 Barrera activada (Refleja la próxima habilidad negativa).")
        return {"exito": True, "eventos": eventos}

    def _hab_cohete(self, jugador, habilidad, objetivo):
        eventos = []
        avance = randint(3, 7)
        pos_inicial = jugador.get_posicion()  # Guardar pos inicial

        nueva = min(pos_inicial + avance, self.posicion_meta)
        jugador.teletransportar_a(nueva)

        eventos.append(f"🚀 Cohete: Avanzas {avance} casillas a la posición {nueva}.")

        meta_alcanzada = False
        if nueva >= self.posicion_meta:
            self.fin_juego = True
            meta_alcanzada = True
            eventos.append(f"🏆 ¡{jugador.get_nombre()} llegó a la meta con Cohete!")

        # Devolver datos de movimiento
        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento": True,
            "resultado_movimiento": {
                "dado": avance,
                "pos_inicial": pos_inicial,
                "pos_final": nueva,
                "meta_alcanzada": meta_alcanzada,
            },
        }

    def _hab_intercambio_forzado(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)

        if not obj or not obj.esta_activo():
            eventos.append("Objetivo inválido o no activo.")
            return {"exito": False, "eventos": eventos}
        if obj == jugador:
            eventos.append("No puedes intercambiar contigo mismo.")
            return {"exito": False, "eventos": eventos}
        if not self._puede_ser_afectado(obj, habilidad):
            eventos.append(f"{obj.get_nombre()} está protegido.")
            return {"exito": False, "eventos": eventos}

        pos_j, pos_o = jugador.get_posicion(), obj.get_posicion()

        # Guardamos los datos del movimiento del *otro* jugador
        movimiento_objetivo = {
            "jugador": obj.get_nombre(),
            "pos_inicial": pos_o,
            "pos_final": pos_j,
            "meta_alcanzada": pos_j >= self.posicion_meta,
        }

        # Realizar el movimiento
        jugador.teletransportar_a(pos_o)
        obj.teletransportar_a(pos_j)
        eventos.append(f"🔄 Intercambias posición con {obj.get_nombre()}.")

        if movimiento_objetivo["meta_alcanzada"]:
            self.fin_juego = True
            eventos.append(f"🏆 ¡{obj.get_nombre()} llegó a la meta con Intercambio!")

        meta_alcanzada_jugador = pos_o >= self.posicion_meta
        if meta_alcanzada_jugador:
            self.fin_juego = True
            eventos.append(
                f"🏆 ¡{jugador.get_nombre()} llegó a la meta con Intercambio!"
            )

        # Devolver datos de movimiento
        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento_doble": True,
            "resultado_movimiento_jugador": {
                "dado": 0,
                "pos_inicial": pos_j,
                "pos_final": pos_o,
                "meta_alcanzada": meta_alcanzada_jugador,
            },
            "resultado_movimiento_objetivo": movimiento_objetivo,
        }

    def _hab_retroceso(self, jugador, habilidad, objetivo):
        eventos = []
        obj = self._encontrar_jugador(objetivo)
        if not obj or not obj.esta_activo():
            eventos.append("Objetivo inválido o no activo.")
            return {"exito": False, "eventos": eventos}

        if not self._puede_ser_afectado(obj, habilidad):
            return {"exito": False, "eventos": self.eventos_turno}

        empuje_base = 7 if "retroceso_brutal" in jugador.perks_activos else 5
        empuje_final = empuje_base

        if "desvio_cinetico" in obj.perks_activos:
            reduccion = empuje_final // 2
            empuje_final -= reduccion
            eventos.append(
                f"🏃‍♂️ {obj.get_nombre()} desvía parte del Retroceso (Empuje reducido a {empuje_final})."
            )

        pos_inicial_obj = obj.get_posicion()
        nueva = max(1, pos_inicial_obj - empuje_final)

        if nueva != pos_inicial_obj:
            obj.teletransportar_a(nueva)
            eventos.append(
                f"⏪ {obj.get_nombre()} retrocede {empuje_final} casillas a {nueva}."
            )
        else:
            eventos.append(f"⏪ {obj.get_nombre()} ya está en la casilla 1.")

        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento_otro": True,
            "resultado_movimiento": {
                "jugador_movido": obj.get_nombre(),
                "dado": empuje_final,
                "pos_inicial": pos_inicial_obj,
                "pos_final": nueva,
                "meta_alcanzada": False,
            },
        }

    def _hab_rebote_controlado(self, jugador, habilidad, objetivo):
        eventos = []
        pos_inicial = jugador.get_posicion()

        pos_intermedia = max(1, pos_inicial - 2)
        jugador.teletransportar_a(pos_intermedia)
        eventos.append(f"↩️ Rebote: Retrocedes 2 casillas a {pos_intermedia}.")

        pos_final = min(jugador.get_posicion() + 9, self.posicion_meta)
        jugador.teletransportar_a(pos_final)
        eventos.append(f"⬆️ Controlado: Avanzas 9 casillas a {pos_final}.")

        meta_alcanzada = False
        if pos_final >= self.posicion_meta:
            self.fin_juego = True
            meta_alcanzada = True
            eventos.append(f"🏆 ¡Llegaste a la meta con Rebote Controlado!")

        # Devolver la 'pos_inicial' correcta para la animación
        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento": True,
            "resultado_movimiento": {
                "dado": 9,
                "pos_inicial": pos_inicial,
                "pos_final": pos_final,
                "meta_alcanzada": meta_alcanzada,
            },
        }

    def _hab_dado_perfecto(self, jugador, habilidad, objetivo):
        eventos = []
        try:
            valor = int(objetivo)
            if not (1 <= valor <= 6):
                raise ValueError
        except (ValueError, TypeError):
            eventos.append("Valor inválido para Dado Perfecto (debe ser 1-6).")
            return {"exito": False, "eventos": eventos}

        # Almacena el valor para que ejecutar_turno_dado lo use
        jugador.dado_forzado = valor
        jugador.dado_perfecto_usado += 1
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

        # Crear la nueva casilla
        nueva_casilla_data = {
            "nombre": "Mina de Energía",
            "tipo": "trampa",
            "simbolo": "💣",
            "valor": -50,
            "colocada_por": jugador.get_nombre(),  # Guardar quién la puso
        }

        # Colocar la Mina en el juego
        self.casillas_especiales[pos_actual] = nueva_casilla_data
        eventos.append(f"💣 Mina Colocada en {pos_actual} (-50 E).")

        # Devolver el "delta" del tablero
        return {
            "exito": True,
            "eventos": eventos,
            "celda_actualizada": {
                pos_actual: nueva_casilla_data
            },  # Informa qué celda cambió
        }

    def _hab_doble_turno(self, jugador, habilidad, objetivo):
        eventos = []
        duracion_turnos = 1
        jugador.efectos_activos.append(
            {"tipo": "doble_dado", "turnos": duracion_turnos}
        )
        eventos.append(f"🔄 Lanzarás dos dados este turno.")
        return {"exito": True, "eventos": eventos}

    def _hab_caos(self, jugador, habilidad, objetivo):
        eventos = ["🎪 Caos: ¡Todos los jugadores se mueven aleatoriamente!"]
        movimientos_planificados = []

        # Comprobar si se cumple la condición del logro
        caos_cerca_meta = False
        POSICION_MINIMA_LOGRO = 65  # Definir "cerca de la meta"
        try:
            jugadores_activos = [j for j in self.jugadores if j.esta_activo()]
            if jugadores_activos:  # Asegurarse que haya jugadores
                # Comprobar si TODOS los jugadores activos están en o más allá de la posición 65
                todos_cerca_meta = all(
                    j.get_posicion() >= POSICION_MINIMA_LOGRO for j in jugadores_activos
                )
                if todos_cerca_meta:
                    caos_cerca_meta = True
                    logger.info("LOGRO DETECTADO (Potencial): 'el_caotico' se cumple.")
        except Exception as e:
            logger.error(f"Error al verificar logro 'el_caotico': {e}", exc_info=True)

        for j in self.jugadores:
            if j.esta_activo():

                mov_base = randint(1, 6)
                mov_final = mov_base

                # Chequear Perk del LANZADOR
                if j == jugador and "maestro_del_azar" in j.perks_activos:
                    mov_final *= 2  # Duplica el movimiento
                    eventos.append(
                        f"✨ ¡Maestro del Azar! {j.get_nombre()} duplica su movimiento a {mov_final}."
                    )

                # Chequear Perk del OBJETIVO
                elif j != jugador and "desvio_cinetico" in j.perks_activos:
                    reduccion = mov_final // 2
                    mov_final -= reduccion
                    eventos.append(
                        f"🏃‍♂️ {j.get_nombre()} desvía parte del Caos (Movimiento reducido a {mov_final})."
                    )

                # Aplicar el movimiento final
                pos_actual = j.get_posicion()
                nueva_pos_calc = min(pos_actual + mov_final, self.posicion_meta)

                movimientos_planificados.append(
                    {
                        "jugador": j.get_nombre(),
                        "pos_inicial": pos_actual,
                        "pos_final": nueva_pos_calc,
                        "meta_alcanzada": nueva_pos_calc >= self.posicion_meta,
                        "dado": mov_final,
                    }
                )

                if nueva_pos_calc != pos_actual:
                    j.teletransportar_a(nueva_pos_calc)
                    eventos.append(
                        f"🌀 {j.get_nombre()} avanza {mov_final} a {nueva_pos_calc}."
                    )
                    # Procesar efectos en la nueva casilla
                    if nueva_pos_calc < self.posicion_meta:
                        self._procesar_efectos_posicion(j, nueva_pos_calc)
                        self._verificar_colision(j, nueva_pos_calc)
                else:
                    eventos.append(
                        f"🌀 {j.get_nombre()} intentó moverse {mov_final} pero no avanzó."
                    )

        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento_multiple": True,
            "movimientos": movimientos_planificados,
            "caos_cerca_meta": caos_cerca_meta,
        }

    def _hab_hilos_espectrales(self, jugador, habilidad, objetivo):
        eventos = []
        if not objetivo:
            return {"exito": False, "eventos": ["Debes elegir un objetivo."]}

        obj = self._encontrar_jugador(objetivo)
        if not obj or not obj.esta_activo():
            return {"exito": False, "eventos": [f"Objetivo '{objetivo}' no válido."]}

        if obj == jugador:
            return {"exito": False, "eventos": ["No puedes vincularte a ti mismo."]}

        # Chequeo de Rango
        RANGO_MAX = 10
        pos_j = jugador.get_posicion()
        pos_o = obj.get_posicion()
        if abs(pos_j - pos_o) > RANGO_MAX:
            return {
                "exito": False,
                "eventos": [
                    f"El objetivo está fuera de rango (Máx: {RANGO_MAX} casillas)."
                ],
            }

        # Chequeo de Protecciones (Invisibilidad, Escudo)
        if not self._puede_ser_afectado(obj, habilidad):
            return {"exito": False, "eventos": self.eventos_turno}

        # Chequeo de Escudo (Bloquea)
        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(
                f"🛡️ {obj.get_nombre()} bloqueó los Hilos Espectrales con Escudo."
            )
            return {"exito": False, "eventos": eventos}

        # Chequeo de Barrera (Disipa, no refleja)
        if self._verificar_efecto_activo(obj, "barrera"):
            self._remover_efecto(obj, "barrera")  # Barrera se consume
            eventos.append(
                f"🔮 {obj.get_nombre()} disipó los Hilos Espectrales con Barrera."
            )
            return {"exito": False, "eventos": eventos}

        # Aplicar el Vínculo
        self._remover_efecto(jugador, "vinculo")

        DURACION_VINCULO = 4
        jugador.efectos_activos.append(
            {
                "tipo": "vinculo",
                "objetivo": obj.get_nombre(),
                "turnos": DURACION_VINCULO,
            }
        )

        eventos.append(
            f"🔗 {jugador.get_nombre()} se ha vinculado a {obj.get_nombre()} por {DURACION_VINCULO} turnos."
        )
        return {"exito": True, "eventos": eventos}

    def _hab_tiron_de_cadenas(self, jugador, habilidad, objetivo):
        eventos = []

        # Encontrar el vínculo activo del Titiritero
        efecto_vinculo = self._obtener_efecto_activo(jugador, "vinculo")
        if not efecto_vinculo:
            return {"exito": False, "eventos": ["No tienes a nadie vinculado."]}

        nombre_objetivo = efecto_vinculo.get("objetivo")
        obj = self._encontrar_jugador(nombre_objetivo)

        if not obj or not obj.esta_activo():
            return {
                "exito": False,
                "eventos": [
                    f"Tu objetivo vinculado ({nombre_objetivo}) no está disponible."
                ],
            }

        # Chequeo de Protecciones (Invisibilidad, etc.)
        if not self._puede_ser_afectado(obj, habilidad):
            # _puede_ser_afectado ya añade el evento de log
            return {"exito": False, "eventos": self.eventos_turno}

        # Chequeo de Escudo (Bloquea)
        if self._verificar_efecto_activo(obj, "escudo"):
            self._reducir_efectos_temporales(
                obj, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(f"🛡️ {obj.get_nombre()} bloqueó el Tirón con Escudo.")
            return {"exito": False, "eventos": eventos}

        # Chequeo de Barrera (Disipa, no refleja)
        if self._verificar_efecto_activo(obj, "barrera"):
            self._remover_efecto(obj, "barrera")
            eventos.append(f"🔮 {obj.get_nombre()} usó Barrera para cortar el Tirón.")
            return {"exito": False, "eventos": eventos}

        # Calcular movimiento
        DISTANCIA_TIRON = 5

        # Chequear perk de Desvío Cinético del OBJETIVO
        if "desvio_cinetico" in obj.perks_activos:
            reduccion = DISTANCIA_TIRON // 2  # Se reduce a 1
            DISTANCIA_TIRON -= reduccion
            eventos.append(
                f"🏃‍♂️ {obj.get_nombre()} desvía parte del Tirón (Movimiento reducido a {DISTANCIA_TIRON})."
            )

        pos_j = jugador.get_posicion()
        pos_o = obj.get_posicion()
        pos_inicial_obj = pos_o  # Guardar para la animación

        nueva_pos_obj = pos_o

        if pos_o > pos_j:
            # Objetivo está delante, tirar hacia atrás
            nueva_pos_obj = max(1, pos_o - DISTANCIA_TIRON)
        elif pos_o < pos_j:
            # Objetivo está detrás, tirar hacia adelante
            nueva_pos_obj = min(self.posicion_meta, pos_o + DISTANCIA_TIRON)

        if nueva_pos_obj == pos_inicial_obj:
            eventos.append(f"⛓️ {obj.get_nombre()} ya está pegado a ti.")
            return {"exito": False, "eventos": eventos}

        # Mover al objetivo
        obj.teletransportar_a(nueva_pos_obj)
        eventos.append(
            f"⛓️ ¡{jugador.get_nombre()} tira de {obj.get_nombre()}! Va de {pos_inicial_obj} a {nueva_pos_obj}."
        )

        # Devolver datos de movimiento
        return {
            "exito": True,
            "eventos": eventos,
            "es_movimiento_otro": True,  # Indica que otro jugador se movió
            "resultado_movimiento": {
                "jugador_movido": obj.get_nombre(),
                "dado": DISTANCIA_TIRON,
                "pos_inicial": pos_inicial_obj,
                "pos_final": nueva_pos_obj,
                "meta_alcanzada": False,
            },
        }

    def _hab_traspaso_de_dolor(self, jugador, habilidad, objetivo):
        eventos = []

        # Encontrar el vínculo activo
        efecto_vinculo = self._obtener_efecto_activo(jugador, "vinculo")
        if not efecto_vinculo:
            return {"exito": False, "eventos": ["No tienes a nadie vinculado."]}

        nombre_objetivo = efecto_vinculo.get("objetivo")
        obj = self._encontrar_jugador(nombre_objetivo)

        if not obj or not obj.esta_activo():
            return {
                "exito": False,
                "eventos": [
                    f"Tu objetivo vinculado ({nombre_objetivo}) no está disponible."
                ],
            }

        # Aplicar el efecto de Traspaso al Titiritero
        DURACION_TRASPASO = 3

        # Quitar cualquier Traspaso anterior para refrescar la duración
        self._remover_efecto(jugador, "traspaso_dolor")

        jugador.efectos_activos.append(
            {
                "tipo": "traspaso_dolor",
                "objetivo": obj.get_nombre(),
                "turnos": DURACION_TRASPASO,
            }
        )

        eventos.append(
            f"💔 ¡Traspaso de Dolor activado! El 50% del próximo daño que recibas será redirigido a {obj.get_nombre()}."
        )

        return {"exito": True, "eventos": eventos}

    def _hab_control_total(self, jugador, habilidad, objetivo):
        eventos = []

        try:
            valor_dado = int(objetivo)
            if not (1 <= valor_dado <= 6):
                raise ValueError
        except (ValueError, TypeError):
            eventos.append(
                "Valor inválido para Control Total. Debes elegir un número del 1 al 6."
            )
            return {"exito": False, "eventos": eventos}

        # Encontrar el Vínculo
        efecto_vinculo = self._obtener_efecto_activo(jugador, "vinculo")
        if not efecto_vinculo:
            return {"exito": False, "eventos": ["No tienes a nadie vinculado."]}

        nombre_objetivo_vinculado = efecto_vinculo.get("objetivo")
        obj_vinculado = self._encontrar_jugador(nombre_objetivo_vinculado)

        if not obj_vinculado or not obj_vinculado.esta_activo():
            return {
                "exito": False,
                "eventos": [
                    f"Tu objetivo vinculado ({nombre_objetivo_vinculado}) no está disponible."
                ],
            }

        # Chequear protecciones del OBJETIVO VINCULADO
        if not self._puede_ser_afectado(obj_vinculado, habilidad):
            return {"exito": False, "eventos": self.eventos_turno}

        if self._verificar_efecto_activo(obj_vinculado, "escudo"):
            self._reducir_efectos_temporales(
                obj_vinculado, tipo_efecto="escudo", reducir_todo=False
            )
            eventos.append(
                f"🛡️ {obj_vinculado.get_nombre()} bloqueó el Control Total con Escudo."
            )
            return {"exito": False, "eventos": eventos}

        if self._verificar_efecto_activo(obj_vinculado, "barrera"):
            self._remover_efecto(obj_vinculado, "barrera")
            eventos.append(
                f"🔮 {obj_vinculado.get_nombre()} usó Barrera para disipar el Control Total."
            )
            return {"exito": False, "eventos": eventos}

        DURACION_EFECTO = 2

        # Aplicar el movimiento forzado
        self._remover_efecto(obj_vinculado, "movimiento_forzado")  # Limpiar anterior
        obj_vinculado.efectos_activos.append(
            {
                "tipo": "movimiento_forzado",
                "controlador": jugador.get_nombre(),
                "dado_forzado": valor_dado,
                "turnos": DURACION_EFECTO,
            }
        )

        # Aplicar la pausa
        self._remover_efecto(obj_vinculado, "pausa")
        obj_vinculado.efectos_activos.append(
            {"tipo": "pausa", "turnos": DURACION_EFECTO}
        )

        eventos.append(
            f"🎮 ¡Control Total aplicado! {obj_vinculado.get_nombre()} será forzado a moverse {valor_dado} casillas y perderá su turno."
        )
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
            return None  # No hay jugadores, no hay ganador
        max_casillas = 0
        for j in self.jugadores:
            if j.esta_activo():
                # Calcula el puntaje base solo si está activo
                j._puntaje_base_final = self._calcular_puntaje_final_avanzado(j)

                # El bonus de explorador solo cuenta para jugadores activos
                count = len(getattr(j, "tipos_casillas_visitadas", set()))
                if count > max_casillas:
                    max_casillas = count
            else:
                j._puntaje_base_final = 0

        BONUS_CASILLA = BONUS_EXPLORADOR
        ganador_final = None
        max_score = -float("inf")  # Empezar con el score más bajo posible

        for j in self.jugadores:
            # Obtener el puntaje base calculado en el loop anterior
            puntaje_final = getattr(j, "_puntaje_base_final", 0)

            if (
                j.esta_activo()
                and max_casillas > 0
                and len(getattr(j, "tipos_casillas_visitadas", set())) == max_casillas
            ):
                puntaje_final += BONUS_CASILLA
                # Solo añadir el evento si el juego no ha terminado aún
                if not self.fin_juego:
                    self.eventos_turno.append(
                        f"🏆 ¡BONUS Explorador! {j.get_nombre()} gana +{BONUS_CASILLA} puntos."
                    )

            # Guardar el puntaje final CON bonus en el jugador
            j._puntaje_final_con_bonus = puntaje_final

            # Comprobar si este jugador (activo) es el nuevo ganador
            if j.esta_activo():
                if puntaje_final >= max_score:
                    max_score = puntaje_final
                    ganador_final = j

        # Asegurarse de marcar el juego como terminado si aún no lo estaba
        self.fin_juego = True

        # Si por alguna razón ningún jugador activo califica
        return ganador_final

    def _calcular_puntaje_final_avanzado(self, jugador):
        puntaje_energia = jugador.get_puntaje() * 1
        puntaje_posicion = jugador.get_posicion() * 1

        # Bono por llegar a la meta
        puntaje_meta = (
            100 if jugador.get_posicion() >= 75 and jugador.get_puntaje() > 0 else 0
        )

        # Colisiones Causadas
        colisiones_causadas = getattr(jugador, "colisiones_causadas", 0)
        puntaje_colisiones = colisiones_causadas * 15

        # Puntos de Mando (PM) Sobrantes
        pm_sobrantes = getattr(jugador, "pm", 0)
        puntaje_pm = pm_sobrantes * 5

        # Perks Activos
        perks_activos = getattr(jugador, "perks_activos", [])
        puntaje_perks = len(perks_activos) * 20

        puntaje_parcial = (
            puntaje_energia
            + puntaje_posicion
            + puntaje_meta
            + puntaje_colisiones
            + puntaje_pm
            + puntaje_perks
        )

        jugador._puntaje_base_final = puntaje_parcial

        return puntaje_parcial

    def obtener_estadisticas_finales(self):
        estadisticas = []
        ganador_obj = None

        if self.ha_terminado():
            ganador_obj = self.determinar_ganador()

            for jugador in self.jugadores:
                # Obtener el puntaje final calculado
                puntaje = getattr(jugador, "_puntaje_final_con_bonus", 0)

                estadisticas.append(
                    {
                        "nombre": jugador.get_nombre(),
                        # Asegúrate de usar el puntaje final con bonus
                        "_puntaje_final_con_bonus": puntaje,
                        # Añade otros campos que el cliente necesite para mostrar
                        "posicion": jugador.get_posicion(),
                        "energia_final": jugador.get_puntaje(),
                    }
                )

        # Devolver un diccionario que contenga el nombre del ganador y la lista de stats
        return {
            "ganador": ganador_obj.get_nombre() if ganador_obj else None,
            "lista_final": estadisticas,
        }

    # ===================================================================
    # --- 7. FUNCIONES DE UTILIDAD (Helpers) ---
    # ===================================================================

    def obtener_jugador_actual(self):
        if (
            self.fin_juego
            or not self.jugadores
            or self.turno_actual >= len(self.jugadores)
        ):
            return None
        jugador_en_turno = self.jugadores[self.turno_actual]
        return jugador_en_turno

    def obtener_turno_actual(self):
        if (
            self.fin_juego
            or not self.jugadores
            or self.turno_actual >= len(self.jugadores)
        ):
            logger.debug(
                f"OBTENER TURNO: Devolviendo None (fin_juego={self.fin_juego}, num_jugadores={len(self.jugadores)})"
            )
            return None

        # Asegurarse que el jugador en turno_actual existe y está activo
        jugador_en_turno = self.jugadores[self.turno_actual]
        if not jugador_en_turno.esta_activo():
            logger.debug(
                f"OBTENER TURNO: Jugador {jugador_en_turno.get_nombre()} inactivo."
            )
            return None

        nombre_turno = jugador_en_turno.get_nombre()
        # logger.debug(f"OBTENER TURNO: {nombre_turno} ({self.turno_actual})") # Descomentar si necesitas mucho detalle
        return nombre_turno

    def obtener_estado_jugadores(self):
        return [jugador.to_dict() for jugador in self.jugadores]

    def obtener_estado_tablero(self):
        tablero = {}

        # Agregar jugadores al tablero
        for jugador in self.jugadores:
            pos = jugador.get_posicion()
            if pos not in tablero:
                tablero[pos] = {
                    "jugadores": [],
                    "casilla_especial": None,
                    "energia": None,
                }

            tablero[pos]["jugadores"].append(
                {
                    "nombre": jugador.get_nombre(),
                    "energia": jugador.get_puntaje(),
                    "activo": jugador.esta_activo(),
                    "avatar_emoji": jugador.avatar_emoji,
                }
            )

        # Agregar casillas especiales
        for pos, datos in self.casillas_especiales.items():
            if pos not in tablero:
                tablero[pos] = {
                    "jugadores": [],
                    "casilla_especial": None,
                    "energia": None,
                }
            tablero[pos]["casilla_especial"] = datos

        # Agregar packs de energía
        for pack in self.energia_packs:
            pos = pack["posicion"]
            if pack["valor"] != 0:
                if pos not in tablero:
                    tablero[pos] = {
                        "jugadores": [],
                        "casilla_especial": None,
                        "energia": None,
                    }
                tablero[pos]["energia"] = pack["valor"]

        return tablero

    def marcar_jugador_inactivo(self, nombre_jugador):
        jugador = self._encontrar_jugador(nombre_jugador)
        if jugador and jugador.esta_activo():
            jugador.set_activo(False)
            jugador.efectos_activos = []  # Limpiar efectos
            self.eventos_turno.append(
                f"🔌 {nombre_jugador} se ha desconectado y queda inactivo."
            )
            logger.info(f"JUGADOR INACTIVO: {nombre_jugador}")
            return True
        return False

    def _encontrar_jugador(self, nombre):
        for jugador in self.jugadores:
            if jugador.get_nombre() == nombre:
                return jugador
        return None

    def _verificar_efecto_activo(self, jugador, tipo_efecto):
        return any(efecto["tipo"] == tipo_efecto for efecto in jugador.efectos_activos)

    def _obtener_efecto_activo(self, jugador, tipo_efecto):
        for efecto in jugador.efectos_activos:
            if efecto.get("tipo") == tipo_efecto:
                return efecto
        return None

    def _reducir_efectos_temporales(self, jugador, tipo_efecto=None, reducir_todo=True):
        nuevos_efectos = []
        efectos_a_ignorar = []

        for efecto in jugador.efectos_activos:
            tipo = efecto.get("tipo")

            # Mantener efectos defensivos sin reducir
            if tipo in efectos_a_ignorar:
                nuevos_efectos.append(efecto)
                continue

            # Reducir si es el efecto específico O si se deben reducir todos
            reducir_este = False
            if tipo_efecto and tipo == tipo_efecto:  # Si buscamos uno específico
                reducir_este = True
            elif reducir_todo and tipo not in efectos_a_ignorar:  # Si reducimos todos
                reducir_este = True

            if reducir_este:
                efecto["turnos"] -= 1

            # Mantener el efecto solo si aún tiene turnos
            if efecto.get("turnos", 0) > 0:
                nuevos_efectos.append(efecto)

        jugador.efectos_activos = nuevos_efectos

    def _puede_ser_afectado(self, objetivo, habilidad_usada=None):
        if (
            habilidad_usada
            and habilidad_usada.tipo == "ofensiva"
            and "anticipacion" in objetivo.perks_activos
        ):
            if random.random() < 0.20:
                self.eventos_turno.append(
                    f"🛡️ ¡{objetivo.get_nombre()} esquivó {habilidad_usada.nombre} (Anticipación)!"
                )

                # Disparar el logro "Fantasma"
                if self.achievement_system:
                    try:
                        threading.Thread(
                            target=self.achievement_system.check_achievement,
                            args=(
                                objetivo.get_nombre(),
                                "game_event",
                                {"event_name": "fantasma"},
                            ),
                        ).start()
                    except Exception as e:
                        logger.error(
                            f"ERROR al verificar logro 'fantasma' (Anticipación): {e}",
                            exc_info=True,
                        )

                return False  # No puede ser afectado

        # Comprobar Invisibilidad
        if self._verificar_efecto_activo(objetivo, "invisible"):
            self.eventos_turno.append(
                f"👻 {objetivo.get_nombre()} está protegido por Invisibilidad."
            )

            # Disparar el logro "Fantasma"
            if self.achievement_system:
                try:
                    threading.Thread(
                        target=self.achievement_system.check_achievement,
                        args=(
                            objetivo.get_nombre(),
                            "game_event",
                            {"event_name": "fantasma"},
                        ),
                    ).start()
                except Exception as e:
                    logger.error(
                        f"ERROR al verificar logro 'fantasma' (Invisibilidad): {e}",
                        exc_info=True,
                    )

            return False  # No puede ser afectado

        # Comprobar Escudo Total
        if self._verificar_efecto_activo(objetivo, "escudo"):
            self.eventos_turno.append(
                f"🛡️ {objetivo.get_nombre()} está protegido por Escudo."
            )

            return False  # No puede ser afectado

        return True

    def _remover_efecto(self, jugador, tipo_efecto):
        jugador.efectos_activos = [
            e for e in jugador.efectos_activos if e.get("tipo") != tipo_efecto
        ]

    def _procesar_recompensa_caza(self, atacante, objetivo):
        if not atacante or not objetivo or atacante == objetivo:
            return  # Sin recompensa

        if getattr(objetivo, "es_caza", False) and not getattr(
            atacante, "recompensa_reclamada", False
        ):
            RECOMPENSA_ENERGIA = RECOMPENSA_CAZA_ENERGIA
            RECOMPENSA_PM = RECOMPENSA_CAZA_PM

            # Dar recompensa al atacante
            atacante._JugadorWeb__puntaje += RECOMPENSA_ENERGIA
            cambio_real = RECOMPENSA_ENERGIA
            atacante.ganar_pm(RECOMPENSA_PM, fuente="cazarrecompensas")

            # MARCAR AL ATACANTE
            atacante.recompensa_reclamada = True

            self.eventos_turno.append(
                f"🎯 ¡{atacante.get_nombre()} reclamó la recompensa por {objetivo.get_nombre()}! (+{cambio_real}E, +{RECOMPENSA_PM} PM)"
            )

            # Desactivar la marca
            objetivo.es_caza = False
