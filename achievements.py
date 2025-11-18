# ===================================================================
# SISTEMA DE LOGROS - VOLTRACE (achievements.py)
# ===================================================================
#
# Este archivo define la clase 'AchievementSystem'.
# Maneja la lógica de configuración y desbloqueo de todos los logros.
#
# Responsabilidades:
# - achievements_config: Diccionario con la definición de todos los
#   logros (nombre, XP, icono, trigger, etc.).
# - check_achievement: Función principal que recibe un evento (ej.
#   'game_finished') y determina si se debe desbloquear un logro.
# - _check_*_achievements: Funciones helper para verificar categorías
#   específicas de logros (social, persistencia, juego, etc.).
# - get_user_achievement_progress: Calcula el estado actual (progreso)
#   de todos los logros para un usuario.
#
# ===================================================================

from datetime import datetime
from models import db, User, Achievement, UserAchievement
from sqlalchemy.orm import selectinload
import logging

logger = logging.getLogger('voltrace')

class AchievementSystem:
    
    def __init__(self, db_lock):
        self.db_lock = db_lock
        self.achievements_config = {
            # Logros de Primeras Veces
            "first_win": {"name": "Primera Victoria", "description": "Gana tu primera partida", "xp_reward": 100, "icon": "🏆", "category": "primeras_veces", "trigger": "game_finished", "target_value": 1},
            "first_game": {"name": "Primer Juego", "description": "Completa tu primera partida", "xp_reward": 50, "icon": "🎮", "category": "primeras_veces", "trigger": "game_finished", "target_value": 1},
            "first_room": {"name": "Creador Novato", "description": "Crea tu primera sala", "xp_reward": 25, "icon": "🏠", "category": "primeras_veces", "trigger": "room_created", "target_value": 1},
            "first_ability": {"name": "Primer Poder", "description": "Usa tu primera habilidad", "xp_reward": 30, "icon": "⚡", "category": "primeras_veces", "trigger": "ability_used", "target_value": 1},

            # Logros de Juego
            "speed_demon": {"name": "Demonio Velocista", "description": "Gana una partida en menos de 15 movimientos", "xp_reward": 200, "icon": "🚀", "category": "gameplay", "trigger": "game_finished", "target_value": 1}, # Es ganar 1 partida así
            "survivor": {"name": "Superviviente", "description": "Gana con menos de 50 de energía", "xp_reward": 150, "icon": "🩹", "category": "gameplay", "trigger": "game_finished", "target_value": 1}, # Es ganar 1 partida así
            "energy_master": {"name": "Maestro de Energía", "description": "Termina una partida con más de 1000 de energía", "xp_reward": 125, "icon": "⚡", "category": "gameplay", "trigger": "game_finished", "target_value": 1}, # Es terminar 1 partida así
            "ability_master": {"name": "Maestro de Habilidades", "description": "Usa las 4 habilidades en una partida", "xp_reward": 175, "icon": "🎯", "category": "gameplay", "trigger": "game_finished", "target_value": 1}, # Es 1 partida así
            "comeback_king": {"name": "Rey del Comeback", "description": "Gana estando en último lugar a mitad de partida", "xp_reward": 250, "icon": "👑", "category": "gameplay", "trigger": "game_finished", "target_value": 1}, # Es 1 partida así

            # Logros Sociales
            "chat_king": {"name": "Rey del Chat", "description": "Envía 25 mensajes en una sola partida", "xp_reward": 50, "icon": "💬", "category": "social", "trigger": "game_finished", "target_value": 25}, # Requiere trackeo por partida
            "room_host": {"name": "Anfitrión Experto", "description": "Crea 10 salas", "xp_reward": 100, "icon": "🏠", "category": "social", "trigger": "room_created", "target_value": 10},
            "social_butterfly": {"name": "Mariposa Social", "description": "Agrega 5 amigos", "xp_reward": 150, "icon": "🦋", "category": "social", "trigger": "friend_added", "target_value": 5},
            "popular": {"name": "Popular", "description": "Alcanza 15 amigos", "xp_reward": 500, "icon": "⭐", "category": "social", "trigger": "friend_added", "target_value": 15},
            "chat_master": {"name": "Maestro del Chat", "description": "Envía 50 mensajes privados", "xp_reward": 200, "icon": "💬", "category": "social", "trigger": "private_message_sent", "target_value": 50},

            # Logros de Suerte
            "lucky_seven": {"name": "Siete de la Suerte", "description": "Saca 6 en el dado 3 veces seguidas", "xp_reward": 300, "icon": "🍀", "category": "luck", "trigger": "dice_rolled", "target_value": 1}, # Es 1 vez que ocurra
            "treasure_hunter": {"name": "Cazatesoros", "description": "Cae en 5 casillas de tesoro en una partida", "xp_reward": 150, "icon": "💰", "category": "luck", "trigger": "game_finished", "target_value": 5}, # Requiere trackeo por partida
            "trap_avoider": {"name": "Esquiva Trampas", "description": "Completa una partida sin caer en ninguna trampa", "xp_reward": 100, "icon": "🛡️", "category": "luck", "trigger": "game_finished", "target_value": 1}, # Es 1 partida así

            # Logros de Persistencia
            "veteran": {"name": "Veterano", "description": "Juega 50 partidas", "xp_reward": 500, "icon": "🎖️", "category": "persistence", "trigger": "game_finished", "target_value": 50},
            "champion": {"name": "Campeón", "description": "Gana 25 partidas", "xp_reward": 750, "icon": "🏆", "category": "persistence", "trigger": "game_finished", "target_value": 25},
            "dedicated": {"name": "Dedicado", "description": "Juega durante 7 días diferentes", "xp_reward": 200, "icon": "📅", "category": "persistence", "trigger": "login", "target_value": 7}, # Requiere trackeo de días
            "level_master": {"name": "Maestro de Niveles", "description": "Alcanza el nivel 10", "xp_reward": 1000, "icon": "🌟", "category": "persistence", "trigger": "level_up", "target_value": 10},

            # Logros Específicos del Juego
            "superviviente": {"name": "Superviviente", "description": "Terminar el juego sin ser eliminado", "xp_reward": 200, "icon": "💪", "category": "survival", "trigger": "game_finished", "target_value": 1},
            "meta_alcanzada": {"name": "¡Meta Alcanzada!", "description": "Llegar a la casilla 75", "xp_reward": 300, "icon": "🏁", "category": "achievement", "trigger": "game_finished", "target_value": 1},
            "explosion_perfecta": {"name": "Explosión Perfecta", "description": "Afectar a 2 o más jugadores con Bomba Energética", "xp_reward": 250, "icon": "💥", "category": "combat", "trigger": "ability_used", "target_value": 1},
            "reflejo_maestro": {"name": "Reflejo Maestro", "description": "Reflejar un ataque con Barrera", "xp_reward": 200, "icon": "🔁", "category": "defense", "trigger": "ability_used", "target_value": 1},
            "muralla_humana": {"name": "Muralla Humana", "description": "Sobrevivir a una colisión con escudo activo", "xp_reward": 175, "icon": "🛡️", "category": "defense", "trigger": "collision", "target_value": 1},
            "fantasma": {"name": "Fantasma", "description": "Evitar un ataque estando invisible", "xp_reward": 150, "icon": "👻", "category": "stealth", "trigger": "ability_defense", "target_value": 1},
            "regenerador": {"name": "Regenerador", "description": "Recuperar energía con Curación desde menos de 200 puntos", "xp_reward": 175, "icon": "💚", "category": "recovery", "trigger": "ability_used", "target_value": 1},
            "ultimo_en_pie": {"name": "Último en Pie", "description": "Ser el único jugador activo al final de la partida", "xp_reward": 500, "icon": "👑", "category": "domination", "trigger": "game_finished", "target_value": 1},
            "viajero_dimensional": {"name": "Viajero Dimensional", "description": "Activar 5 casillas especiales distintas en una misma partida", "xp_reward": 225, "icon": "🌀", "category": "exploration", "trigger": "game_finished", "target_value": 5},
            "energizado": {"name": "Energizado", "description": "Alcanzar más de 1000 puntos de energía", "xp_reward": 200, "icon": "⚡", "category": "power", "trigger": "game_finished", "target_value": 1},
            "cazador_de_packs": {"name": "Cazador de Packs", "description": "Obtener 10 o más packs de energía en una partida", "xp_reward": 225, "icon": "🎒", "category": "collection", "trigger": "game_finished", "target_value": 10},
            "inmortal": {"name": "Inmortal", "description": "Recuperarse tras llegar a 0 energía", "xp_reward": 400, "icon": "🔥", "category": "comeback", "trigger": "game_event", "target_value": 1},
            "el_caotico": {"name": "El Caótico", "description": "Usar Caos cuando todos los jugadores están cerca de la meta", "xp_reward": 300, "icon": "🎪", "category": "chaos", "trigger": "ability_used", "target_value": 1},
            "equilibrio_cosmico": {"name": "Equilibrio Cósmico", "description": "Terminar el juego con exactamente 600 puntos de energía", "xp_reward": 350, "icon": "⚖️", "category": "precision", "trigger": "game_finished", "target_value": 1},

            # Logros adicionales
            "coleccionista": {"name": "Coleccionista", "description": "Desbloquear 10 logros diferentes", "xp_reward": 500, "icon": "📚", "category": "meta", "trigger": "achievement_unlocked", "target_value": 10},
            "perfeccionista": {"name": "Perfeccionista", "description": "Ganar sin usar ninguna habilidad", "xp_reward": 300, "icon": "✨", "category": "challenge", "trigger": "game_finished", "target_value": 1},
            "estratega_supremo": {"name": "Estratega Supremo", "description": "Ganar 3 partidas consecutivas", "xp_reward": 400, "icon": "🧠", "category": "mastery", "trigger": "game_finished", "target_value": 3}, # Requiere trackeo externo
            "maratonista": {"name": "Maratonista", "description": "Completar una partida que dure más de 50 rondas", "xp_reward": 150, "icon": "🏃‍♂️", "category": "endurance", "trigger": "game_finished", "target_value": 1},
            "precision_laser": {"name": "Precisión Láser", "description": "Usar la habilidad 'Dado Perfecto' 3 veces en una sola partida", "xp_reward": 175, "icon": "🎯", "category": "precision", "trigger": "game_finished", "target_value": 3} # Requiere trackeo por partida
        }
    
    def check_achievement(self, username, event_type, event_data=None):
        with self.db_lock:
            unlocked_achievements = []
            newly_unlocked_ids = []

            # Obtener el usuario de la DB
            user = User.query.filter_by(username=username).first()
            if not user:
                logger.warning(f"ACHIEVEMENT ERROR: Usuario {username} no encontrado en la DB. No se verificaron logros.")
                return []

            # Obtener IDs de logros ya desbloqueados
            unlocked_ach_ids = [ua.achievement.internal_id for ua in user.unlocked_achievements_assoc]
            
            # Mapear las estadísticas del usuario para compatibilidad con las funciones de verificación
            user_stats = {
                'xp': user.xp,
                'level': user.level,
                'games_played': user.games_played,
                'games_won': user.games_won,
                'abilities_used': getattr(user, 'abilities_used', 0), 
                'game_messages_sent': getattr(user, 'game_messages_sent', 0),    
                'private_messages_sent': getattr(user, 'private_messages_sent', 0),
                'messages_sent': getattr(user, 'chat_messages_sent', 0),    
                'rooms_created': getattr(user, 'rooms_created', 0),
                'friends_count': user.friends.count(),
                'unique_login_days_count': getattr(user, 'unique_login_days_count', 0)
            }
            
            # Llamar a las funciones de verificación
            if event_type == 'game_finished':
                newly_unlocked_ids.extend(self._check_game_finished_achievements(username, event_data, unlocked_ach_ids, user_stats))
            
            elif event_type == 'ability_used':
                newly_unlocked_ids.extend(self._check_ability_achievements(username, event_data, unlocked_ach_ids, user_stats))
            
            elif event_type == 'room_created':
                newly_unlocked_ids.extend(self._check_room_achievements(username, unlocked_ach_ids, user_stats))
            
            elif event_type == 'dice_rolled':
                newly_unlocked_ids.extend(self._check_dice_achievements(username, event_data, unlocked_ach_ids, user_stats))
            
            elif event_type == 'special_tile':
                newly_unlocked_ids.extend(self._check_special_tile_achievements(username, event_data, unlocked_ach_ids, user_stats))

            elif event_type == 'game_event':
                newly_unlocked_ids.extend(self._check_game_event_achievements(username, event_data, unlocked_ach_ids, user_stats))

            elif event_type == 'login':
                newly_unlocked_ids.extend(self._check_login_achievements(username, event_data, unlocked_ach_ids, user_stats))

            # Añadimos los nuevos triggers sociales
            elif event_type == 'friend_added':
                newly_unlocked_ids.extend(self._check_social_achievements(username, event_type, unlocked_ach_ids, user_stats))
            
            elif event_type == 'private_message_sent':
                newly_unlocked_ids.extend(self._check_social_achievements(username, event_type, unlocked_ach_ids, user_stats))

            newly_unlocked_ids.extend(self._check_persistence_achievements(username, unlocked_ach_ids, user_stats))

            # Guardar logros desbloqueados y otorgar XP (EN LA DB)
            total_xp_gained = 0
            
            # Filtra solo los ID de logros que aún no hemos procesado para evitar doble conteo si una subfunción retorna el mismo ID
            final_unlocks = list(set(newly_unlocked_ids))
            
            # Obtener todos los objetos Achievement necesarios en una sola consulta
            achievements_to_unlock = Achievement.query.filter(Achievement.internal_id.in_(final_unlocks)).all()
            
            for achievement_obj in achievements_to_unlock:
                # Verificar UNA ÚLTIMA VEZ que el logro no esté ya en la tabla de asociación
                is_already_unlocked = UserAchievement.query.filter_by(user_id=user.id, achievement_id=achievement_obj.id).first()
                
                if not is_already_unlocked:
                    # Añadir a la tabla de asociación UserAchievement
                    ua = UserAchievement(user=user, achievement=achievement_obj)
                    db.session.add(ua)
                    
                    # Sumar XP y guardar ID para retorno
                    xp_reward = achievement_obj.xp_reward
                    total_xp_gained += xp_reward
                    unlocked_achievements.append(achievement_obj.internal_id)

            # Actualizar XP del usuario y guardar en DB
            if total_xp_gained > 0:
                user.xp += total_xp_gained
            
            # Guardar todos los cambios de una vez
            db.session.commit()
            
            return unlocked_achievements
    
    def _check_game_finished_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        event_data = event_data or {} # Asegurar que event_data no sea None
        
        # Primera partida
        if 'first_game' not in current_achievements and user_stats['games_played'] >= 1:
            unlocked.append('first_game')
        
        # Primera victoria
        if 'first_win' not in current_achievements and event_data.get('won') and user_stats['games_won'] >= 1:
            unlocked.append('first_win')
        
        # Demonio velocista
        if 'speed_demon' not in current_achievements and event_data.get('won') and event_data.get('total_rounds', 99) < 15:
            unlocked.append('speed_demon')
        
        # Superviviente original (ganar con poca energía)
        if 'survivor' not in current_achievements and event_data.get('won') and event_data.get('final_energy', 1000) < 50:
            unlocked.append('survivor')
        
        # Superviviente (terminar sin ser eliminado)
        if 'superviviente' not in current_achievements and event_data.get('never_eliminated', True):
            unlocked.append('superviviente')
        
        # Meta Alcanzada (llegar a casilla 75)
        if 'meta_alcanzada' not in current_achievements and event_data.get('reached_position', 0) >= 75:
            unlocked.append('meta_alcanzada')
        
        # Energizado / Energy Master (más de 1000 energía)
        if event_data.get('final_energy', 0) > 1000:
            if 'energizado' not in current_achievements:
                unlocked.append('energizado')
            if 'energy_master' not in current_achievements:
                unlocked.append('energy_master')
        
        # Equilibrio Cósmico (exactamente 600 energía)
        if 'equilibrio_cosmico' not in current_achievements and event_data.get('final_energy', 0) == 600:
            unlocked.append('equilibrio_cosmico')
        
        # Último en Pie (único jugador activo)
        if 'ultimo_en_pie' not in current_achievements and event_data.get('only_active_player', False):
            unlocked.append('ultimo_en_pie')
        
        # Cazador de Packs (10+ packs de energía)
        if 'cazador_de_packs' not in current_achievements and event_data.get('energy_packs_collected', 0) >= 10:
            unlocked.append('cazador_de_packs')
        
        # Viajero Dimensional (5 casillas especiales distintas)
        if 'viajero_dimensional' not in current_achievements and len(event_data.get('special_tiles_activated', set())) >= 5:
            unlocked.append('viajero_dimensional')
        
        # Perfeccionista (ganar sin usar habilidades)
        if 'perfeccionista' not in current_achievements and event_data.get('won') and event_data.get('abilities_used', 1) == 0:
            unlocked.append('perfeccionista')
        
        # Maratonista (más de 50 rondas)
        if 'maratonista' not in current_achievements and event_data.get('total_rounds', 0) > 50:
            unlocked.append('maratonista')

        # Maestro de habilidades (Usa 4 o más habilidades)
        if 'ability_master' not in current_achievements and event_data.get('abilities_used', 0) >= 4:
            unlocked.append('ability_master')
        
        # Cazatesoros (Cae en 5+ tesoros)
        if 'treasure_hunter' not in current_achievements and event_data.get('treasures_this_game', 0) >= 5:
            unlocked.append('treasure_hunter')

        # Precisión Láser (Usa Dado Perfecto 3+ veces)
        if 'precision_laser' not in current_achievements and event_data.get('precision_laser', 0) >= 3:
            unlocked.append('precision_laser')

        # Esquiva Trampas (Completa sin caer en trampas)
        if 'trap_avoider' not in current_achievements and event_data.get('completed_without_traps', False):
             unlocked.append('trap_avoider')
        
        # Estratega Supremo (3 victorias consecutivas)
        if 'estratega_supremo' not in current_achievements and event_data.get('won'):
            consecutive_wins = event_data.get('consecutive_wins', 0)
            if consecutive_wins >= 3:
                unlocked.append('estratega_supremo')
        
        if 'comeback_king' not in current_achievements and event_data.get('won'):
            ultimo_mid_game = event_data.get('ultimo_en_mid_game')
            # Comprobar que el dato exista y sea igual al usuario actual
            if ultimo_mid_game and ultimo_mid_game == username:
                unlocked.append('comeback_king')

        # Rey del Chat (25 mensajes en partida)
        if 'chat_king' not in current_achievements and event_data.get('messages_this_game', 0) >= 25:
            unlocked.append('chat_king')

        # Coleccionista (10 logros)
        current_total_achievements = len(current_achievements) + len(unlocked)
        if 'coleccionista' not in current_achievements and current_total_achievements >= 10:
            unlocked.append('coleccionista')

        return unlocked

    
    def _check_ability_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        event_data = event_data or {}
        
        # Primera habilidad
        if 'first_ability' not in current_achievements and user_stats['abilities_used'] >= 1:
            unlocked.append('first_ability')
        
        # Explosion Perfecta (Bomba Energética)
        habilidad_usada = event_data.get('habilidad', {}).get('nombre')
        if habilidad_usada == 'Bomba Energética':
            afectados_count = event_data.get('afectados_count', 0)
            if 'explosion_perfecta' not in current_achievements and afectados_count >= 2:
                unlocked.append('explosion_perfecta')
        
        # Regenerador (Curación)
        if habilidad_usada == 'Curacion':
            energia_antes = event_data.get('energia_antes', 999) 
            if 'regenerador' not in current_achievements and energia_antes < 200:
                unlocked.append('regenerador')
        
        # El Caótico (Caos)
        if habilidad_usada == 'Caos':
            if event_data.get('caos_cerca_meta') and 'el_caotico' not in current_achievements:
                unlocked.append('el_caotico')
        
        # Reflejo Maestro (Barrera)
        if event_data.get('reflejo_exitoso'):
             if 'reflejo_maestro' not in current_achievements:
                unlocked.append('reflejo_maestro')
                
        
        return unlocked
    
    def _check_room_achievements(self, username, current_achievements, user_stats):
        unlocked = []
        
        # Primera sala
        if 'first_room' not in current_achievements and user_stats['rooms_created'] >= 1:
            unlocked.append('first_room')
        
        # Anfitrión experto
        if 'room_host' not in current_achievements and user_stats['rooms_created'] >= 10:
            unlocked.append('room_host')
        
        return unlocked
    
    def _check_chat_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        event_data = event_data or {}
        # Rey del chat (25 mensajes en una partida)
        # Nota: necesitarías trackear mensajes por partida específicamente
        messages_this_game = event_data.get('messages_this_game', 0)
        if 'chat_king' not in current_achievements and messages_this_game >= 25:
            unlocked.append('chat_king')
        
        return unlocked
    
    def _check_dice_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        event_data = event_data or {}
        
        # Siete de la suerte (3 seises seguidos)
        consecutive_sixes = event_data.get('consecutive_sixes', 0)
        if 'lucky_seven' not in current_achievements and consecutive_sixes >= 3:
            unlocked.append('lucky_seven')
        
        return unlocked
    
    def _check_special_tile_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        
        # Cazatesoros
        treasures_this_game = event_data.get('treasures_this_game', 0)
        if 'treasure_hunter' not in current_achievements and treasures_this_game >= 5:
            unlocked.append('treasure_hunter')
        
        # Esquiva trampas (completar partida sin trampas)
        if 'trap_avoider' not in current_achievements and event_data.get('completed_without_traps'):
            unlocked.append('trap_avoider')
        
        return unlocked
    
    def _check_persistence_achievements(self, username, current_achievements, user_stats):
        unlocked = []
        
        # Veterano
        if 'veteran' not in current_achievements and user_stats['games_played'] >= 50:
            unlocked.append('veteran')
        
        # Campeón
        if 'champion' not in current_achievements and user_stats['games_won'] >= 25:
            unlocked.append('champion')
        
        # Maestro de niveles
        if 'level_master' not in current_achievements and user_stats['level'] >= 10:
            unlocked.append('level_master')
        
        return unlocked
    
    def _check_game_event_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        event_name = event_data.get('event_name')

        # Inmortal (Último Aliento)
        if event_name == 'inmortal' and 'inmortal' not in current_achievements:
            unlocked.append('inmortal')
        
        # Muralla Humana (Sobrevivir colisión con escudo)
        if event_name == 'muralla_humana' and 'muralla_humana' not in current_achievements:
            unlocked.append('muralla_humana')

        # Fantasma (Esquivar habilidad con invisibilidad)
        if event_name == 'fantasma' and 'fantasma' not in current_achievements:
            unlocked.append('fantasma')

        return unlocked
    
    def _check_login_achievements(self, username, event_data, current_achievements, user_stats):
        unlocked = []
        
        # 'dedicated' (Jugar 7 días diferentes)
        login_days_count = event_data.get('login_days', 0)
        if 'dedicated' not in current_achievements and login_days_count >= 7:
            unlocked.append('dedicated')

        return unlocked
    
    def get_achievement_info(self, achievement_id, current_user_stats=None, unlocked_ids_set=None):
        achievement_config = self.achievements_config.get(achievement_id)
        if not achievement_config:
            return None

        info = {
            "id": achievement_id,
            "name": achievement_config.get("name", "Logro Desconocido"),
            "desc": achievement_config.get("description", ""),
            "xp_reward": achievement_config.get("xp_reward", 0),
            "icon": achievement_config.get("icon", "⭐"),
            "category": achievement_config.get("category", "general"),
            "unlocked": False,
            "unlocked_at": None,
            "target_value": achievement_config.get("target_value", 1),
            "current_value": 0
        }

        if unlocked_ids_set and achievement_id in unlocked_ids_set:
            info["unlocked"] = True
            info["current_value"] = info["target_value"] # Si está desbloqueado, el progreso es 100%

        elif not info["unlocked"] and current_user_stats:
            if achievement_id == "veteran":
                info["current_value"] = current_user_stats.get('games_played', 0)
            elif achievement_id == "champion":
                info["current_value"] = current_user_stats.get('games_won', 0)
            elif achievement_id == "level_master":
                info["current_value"] = current_user_stats.get('level', 1)
            elif achievement_id == "chat_master":
                info["current_value"] = current_user_stats.get('chat_messages_sent', 0)
            elif achievement_id == "room_host":
                # Asume que tienes un campo 'rooms_created' en User o current_user_stats
                info["current_value"] = current_user_stats.get('rooms_created', 0)
            elif achievement_id == "coleccionista":
                 # El progreso es la cantidad de logros ya desbloqueados
                 info["current_value"] = len(unlocked_ids_set) if unlocked_ids_set else 0

            # Logros de "primera vez" (target 1)
            elif achievement_id == "first_game":
                 info["current_value"] = 1 if current_user_stats.get('games_played', 0) >= 1 else 0
            elif achievement_id == "first_win":
                 info["current_value"] = 1 if current_user_stats.get('games_won', 0) >= 1 else 0
            elif achievement_id == "first_room":
                 info["current_value"] = 1 if current_user_stats.get('rooms_created', 0) >= 1 else 0
            elif achievement_id == "first_ability":
                 info["current_value"] = 1 if current_user_stats.get('abilities_used', 0) >= 1 else 0
                 
            # Logros de partida única (target > 1, pero progreso se resetea cada partida)
            elif achievement_id in ["treasure_hunter", "viajero_dimensional", "cazador_de_packs", "precision_laser", "chat_king"]:
                 info["current_value"] = 0 # Progreso solo visible durante la partida (requiere más lógica)

            # Logros booleanos o de 1 vez que no dependen de contadores acumulativos
            else:
                 # Si es target 1 y no está desbloqueado, el progreso es 0
                 if info["target_value"] == 1:
                     info["current_value"] = 0
                 # Si tiene un target > 1 pero no mapeamos el progreso arriba, lo dejamos en 0
                 else:
                     info["current_value"] = 0

            # Asegurar que current_value no exceda target_value
            info["current_value"] = min(info["current_value"], info["target_value"])

        return info
    
    def get_all_achievements(self):
        return self.achievements_config
    
    def get_user_achievement_progress(self, username):
        user = User.query.options(
            selectinload(User.unlocked_achievements_assoc)
            .selectinload(UserAchievement.achievement)
        ).filter_by(username=username).first()
        if not user:
            return {'error': 'Usuario no encontrado'}

        unlocked_assoc = UserAchievement.query.filter_by(user_id=user.id).all()
        # Crear un mapa {achievement_id: unlocked_at} y un set de IDs
        unlocked_map = {ua.achievement.internal_id: ua.unlocked_at for ua in unlocked_assoc}
        unlocked_ids_set = set(unlocked_map.keys())

        # btener las estadísticas actuales del usuario para calcular progreso
        current_user_stats = {
            'xp': user.xp, 'level': user.level,
            'games_played': user.games_played, 'games_won': user.games_won,
            'abilities_used': getattr(user, 'abilities_used', 0),
            'game_messages_sent': getattr(user, 'game_messages_sent', 0),
            'private_messages_sent': getattr(user, 'private_messages_sent', 0),
            'rooms_created': getattr(user, 'rooms_created', 0), 
            'unlocked_achievements_count': len(unlocked_ids_set),
            'friends_count': getattr(user, 'friends_count', 0),
            'unique_login_days_count': getattr(user, 'unique_login_days_count', 0)
        }

        # Iterar sobre TODOS los logros configurados y obtener su info/progreso
        progress_list = []
        all_achievements_config = self.achievements_config # Usar la config de la clase

        for ach_id, ach_config in all_achievements_config.items():
            is_unlocked = ach_id in unlocked_ids_set
            target_value = ach_config.get('target_value', 1)
            current_value = 0 # Default

            if is_unlocked:
                current_value = target_value # Si está desbloqueado, progreso es 100%
            elif current_user_stats: # Calcular progreso solo si no está desbloqueado
                
                # Mapeo de ID de logro a stat del usuario
                stat_map = {
                    "veteran": "games_played",
                    "champion": "games_won",
                    "level_master": "level",
                    "chat_master": "private_messages_sent", 
                    "room_host": "rooms_created",
                    "coleccionista": "unlocked_achievements_count",
                    "social_butterfly": "friends_count",
                    "popular": "friends_count",
                    "dedicated": "unique_login_days_count"
                }
                
                if ach_id in stat_map:
                    current_value = current_user_stats.get(stat_map[ach_id], 0)

                # Logros de primera vez 
                elif ach_id == "first_game":
                    current_value = 1 if current_user_stats.get('games_played', 0) >= 1 else 0
                elif ach_id == "first_win":
                    current_value = 1 if current_user_stats.get('games_won', 0) >= 1 else 0
                elif ach_id == "first_room":
                    current_value = 1 if current_user_stats.get('rooms_created', 0) >= 1 else 0
                elif ach_id == "first_ability":
                    current_value = 1 if current_user_stats.get('abilities_used', 0) >= 1 else 0

                # Asegurar que current_value no exceda target_value
                current_value = min(current_value, target_value)

            # Construir datos del logro para el cliente
            achievement_data = {
                'id': ach_id,
                'name': ach_config.get('name', 'N/A'),
                'desc': ach_config.get('description', ''), 
                'xp_reward': ach_config.get('xp_reward', 0),
                'icon': ach_config.get('icon', '⭐'),
                'category': ach_config.get('category', 'general'),
                'unlocked': is_unlocked,
                'unlocked_at': unlocked_map.get(ach_id).isoformat() if is_unlocked and unlocked_map.get(ach_id) else None,
                'target_value': target_value,
                'current_value': current_value
            }
            progress_list.append(achievement_data)

        # Ordenar y devolver el resultado
        progress_list.sort(key=lambda x: (x['category'], not x['unlocked'], x['name']))

        return {
            'unlocked': len(unlocked_ids_set),
            'total': len(all_achievements_config),
            'percentage': (len(unlocked_ids_set) / len(all_achievements_config)) * 100 if len(all_achievements_config) > 0 else 0,
            'achievements': progress_list # La lista detallada
        }
    
    def _check_social_achievements(self, username, event_type, current_achievements, user_stats):
        unlocked = []
        
        if event_type == 'friend_added':
            friends_count = user_stats.get('friends_count', 0)
            # Mariposa Social (5 amigos)
            if "social_butterfly" not in current_achievements and friends_count >= 5:
                 unlocked.append("social_butterfly")
            # Popular (15 amigos)
            if "popular" not in current_achievements and friends_count >= 15:
                 unlocked.append("popular")

        elif event_type == 'private_message_sent':
            messages_sent_count = user_stats.get('private_messages_sent', 0)
            # Maestro del Chat (50 mensajes)
            if "chat_master" not in current_achievements and messages_sent_count >= 50:
                 unlocked.append("chat_master")
        
        return unlocked