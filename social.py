# ===================================================================
# SISTEMA SOCIAL - VOLTRACE (social.py)
# ===================================================================
#
# Este archivo define la clase 'SocialSystem'.
# Maneja toda la lógica de interacción social entre jugadores,
# interactuando directamente con los modelos de la DB (User, PrivateMessage).
#
# Responsabilidades:
# - Gestión de Amigos: Enviar, aceptar, rechazar y eliminar solicitudes.
# - Búsqueda de Usuarios: Encontrar nuevos jugadores.
# - Chat Privado: Enviar, recibir y cargar historial de conversaciones.
# - Presencia: Manejar el estado (online, offline, in_game) de los
#   usuarios conectados.
# - Invitaciones: Lógica para enviar y recibir invitaciones a salas
#   entre amigos.
#
# ===================================================================

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from models import db, User, Achievement, UserAchievement, PrivateMessage
from sqlalchemy import func, case

class SocialSystem:

    def __init__(self):
        self.presence_data = {}

    def send_friend_request(self, sender_username: str, target_username: str) -> Dict:
        # Obtener los objetos User
        sender = User.query.filter_by(username=sender_username).first()
        target = User.query.filter_by(username=target_username).first()

        if not sender or not target:
            return {'success': False, 'message': 'Usuario remitente o destinatario no encontrado.'}

        if sender.id == target.id:
            return {'success': False, 'message': 'No puedes enviarte una solicitud a ti mismo.'}

        if sender.is_friend(target):
            return {'success': False, 'message': f'Ya eres amigo de {target_username}.'}

        if sender.has_sent_request_to(target):
            return {'success': False, 'message': f'Ya enviaste una solicitud a {target_username}.'}

        if target.has_sent_request_to(sender):
            return {'success': False, 'message': f'{target_username} ya te envió una solicitud. Revísala en la pestaña "Solicitudes".'}

        try:
            # Intentar crear la solicitud en la DB
            if sender.send_friend_request(target):
                db.session.commit()
                return {'success': True, 'message': f'Solicitud enviada a {target_username}.'}
            else:
                # Esto solo debería pasar si alguna verificación falló inesperadamente
                return {'success': False, 'message': 'No se pudo enviar la solicitud (error de lógica).'}

        except Exception as e:
            db.session.rollback()
            print(f"Error DB al enviar solicitud: {e}")
            return {'success': False, 'message': 'Error del servidor al procesar la solicitud.'}

    def accept_friend_request(self, username: str, friend_username: str) -> Dict:
        # Obtener los objetos User
        user = User.query.filter_by(username=username).first()        # El receptor 
        sender = User.query.filter_by(username=friend_username).first() # El emisor 

        if not user or not sender:
            return {'success': False, 'message': 'Usuarios no encontrados.'}

        if not user.has_received_request_from(sender):
            return {'success': False, 'message': 'No hay una solicitud pendiente de este usuario.'}
        
        try:
            # Lógica para aceptar: borra la solicitud y crea la amistad
            if user.accept_friend_request(sender):
                db.session.commit()
                
                # Notificación interna
                self.update_user_presence(friend_username, 'online', {'new_friend': username})
                
                return {'success': True, 'message': f'Ahora eres amigo de {friend_username}.'}
            else:
                return {'success': False, 'message': 'Error de lógica al aceptar.'}

        except Exception as e:
            db.session.rollback()
            print(f"Error DB al aceptar solicitud: {e}")
            return {'success': False, 'message': 'Error interno del servidor (DB).'}

    def reject_friend_request(self, username: str, friend_username: str) -> Dict:
        # Obtener los objetos User
        user = User.query.filter_by(username=username).first()        # El receptor 
        sender = User.query.filter_by(username=friend_username).first() # El emisor 

        if not user or not sender:
            return {'success': False, 'message': 'Usuarios no encontrados.'}

        # Verificar que la solicitud existe (el receptor debe tenerla recibida)
        if not user.has_received_request_from(sender):
            return {'success': False, 'message': 'No hay una solicitud pendiente de este usuario.'}
        
        try:
            # Lógica para rechazar
            if user.reject_friend_request(sender):
                db.session.commit()
                return {'success': True, 'message': f'Solicitud de {friend_username} rechazada.'}
            else:
                # Esto puede pasar si la solicitud ya no existe
                return {'success': False, 'message': 'Error de lógica al rechazar.'}

        except Exception as e:
            db.session.rollback()
            print(f"Error DB al rechazar solicitud: {e}")
            return {'success': False, 'message': 'Error interno del servidor (DB).'}

    def remove_friend(self, username, friend_to_remove):
        # Obtener los objetos User
        user = User.query.filter_by(username=username).first()
        friend = User.query.filter_by(username=friend_to_remove).first()

        if not user or not friend:
            return {'success': False, 'message': 'Usuario no encontrado.'}

        if not user.is_friend(friend):
            return {'success': False, 'message': f'{friend_to_remove} no es tu amigo.'}

        try:
            # Lógica para remover la amistad (definida en models.py)
            if user.remove_friend(friend):
                db.session.commit()
                
                self.update_user_presence(friend_to_remove, 'online', {'friend_removed': username})
                
                return {'success': True, 'message': f'{friend_to_remove} fue eliminado de tus amigos.'}
            else:
                return {'success': False, 'message': 'Error de lógica al eliminar.'}

        except Exception as e:
            db.session.rollback()
            print(f"Error DB al remover amistad: {e}")
            return {'success': False, 'message': 'Error interno del servidor (DB).'}

    def search_users(self, query: str, current_user: str, limit: int = 10) -> List[Dict]:
        user_searching = User.query.filter_by(username=current_user).first()
        if not user_searching:
            return {'error': 'Usuario de búsqueda no válido'}

        # Buscar en la Base de Datos: Filtra por username que contiene la query
        results = User.query.filter(
            User.username.ilike(f'%{query}%'),
            User.username != current_user      
        ).limit(10).all()

        output = []
        
        # Procesar los resultados y determinar la relación
        for target_user in results:
            relation = 'none' # Asume que no hay relación

            if user_searching.is_friend(target_user):
                relation = 'friend'
            elif user_searching.has_sent_request_to(target_user):
                relation = 'pending_sent'
            elif user_searching.has_received_request_from(target_user):
                relation = 'pending_received'
                
            output.append({
                'username': target_user.username,
                'level': target_user.level, 
                'relation': relation
            })
            
        return output

    def get_friends_list(self, username: str) -> Dict:
        # Obtener el usuario principal 
        main_user = User.query.filter_by(username=username).first()
        if not main_user:
            return {'error': 'Usuario no encontrado'}

        # Preparar la lista de amigos
        friends_list = []
        
        # Accede a la relación friends
        for friend_user in main_user.friends:
            
            # Obtener el estado de presencia 
            status = self._get_user_status(friend_user.username)
            
            friends_list.append({
                'username': friend_user.username,
                'level': friend_user.level, # Stats directas del modelo User
                'status': status
            })

        # Obtener solicitudes pendientes que el USUARIO RECIBIÓ
        pending_received = [
            sender_user.username for sender_user in main_user.received_requests
        ]
        
        # Obtener solicitudes pendientes que el USUARIO ENVIÓ
        pending_sent = [
            receiver_user.username for receiver_user in main_user.sent_requests
        ]

        return {
            'friends': friends_list,
            'pending_received': pending_received,
            'pending_sent': pending_sent,
        }

    def update_user_presence(self, username: str, status: str, extra_data: Dict = None):
        if username not in self.presence_data:
            self.presence_data[username] = {}

        # Actualizar estado y última vez visto
        self.presence_data[username]['status'] = status
        self.presence_data[username]['last_seen'] = datetime.now().isoformat() 

        # Guardar o limpiar extra_data (que contiene el SID)
        if extra_data:
            self.presence_data[username]['extra_data'] = extra_data
        elif status == 'offline' and 'extra_data' in self.presence_data.get(username, {}):
             # Limpiar SID si se desconecta
             del self.presence_data[username]['extra_data']

    def _get_user_status(self, username: str) -> str:
        if username not in self.presence_data:
            return "offline" # Si nunca se conectó, está offline

        presence = self.presence_data[username]
        status = presence.get("status", "offline")

        # Si el estado registrado es 'offline', devolver 'offline'
        if status == "offline":
            return "offline"

        # Si está online/in_game/in_lobby, verificar la última vez visto
        last_seen_iso = presence.get("last_seen")
        if not last_seen_iso:
            return "offline" # Si no hay timestamp, asumir offline

        try:
            last_seen = datetime.fromisoformat(last_seen_iso)
            now = datetime.now()

            # Considerar offline si han pasado más de X segundos
            if (now - last_seen).total_seconds() > 60:
                return "offline"

            # Si está dentro del umbral, devolver el estado registrado
            return status
        except ValueError:
            # Si el timestamp es inválido
            return "offline"

    def send_private_message(self, sender: str, recipient: str, message: str) -> Dict:
        # Obtener los objetos User
        sender_user = User.query.filter_by(username=sender).first()
        recipient_user = User.query.filter_by(username=recipient).first()

        if not sender_user or not recipient_user:
            return {'success': False, 'message': 'Usuario remitente o destinatario no válido.'}
        
        if sender_user.id == recipient_user.id:
            return {'success': False, 'message': 'No puedes enviarte mensajes a ti mismo.'}
    
        try:
            # Crear y guardar el objeto PrivateMessage en la DB
            new_message = PrivateMessage(
                sender_id=sender_user.id,
                recipient_id=recipient_user.id,
                message=message,
                timestamp=datetime.utcnow() # Usamos UTC para guardar en DB
            )
            db.session.add(new_message)
            db.session.commit()
            
            # Preparar los datos para el cliente (debe usar la hora local si es necesario, pero ISO es seguro)
            message_data = {
                'sender': sender,
                'recipient': recipient,
                'message': message,
                'timestamp': new_message.timestamp.isoformat() # Convertir a string para JSON
            }

            return {'success': True, 'message_data': message_data}

        except Exception as e:
            db.session.rollback()
            print(f"Error DB al enviar mensaje privado: {e}")
            return {'success': False, 'message': 'Error interno del servidor (DB).'}

    def get_conversation(self, user1_username, user2_username):
        # Obtener los IDs de los usuarios
        user1 = User.query.filter_by(username=user1_username).first()
        user2 = User.query.filter_by(username=user2_username).first()

        if not user1 or not user2:
            return [] 

        # Consultar la tabla PrivateMessage
        messages = PrivateMessage.query.filter(
            ((PrivateMessage.sender_id == user1.id) & (PrivateMessage.recipient_id == user2.id)) |
            ((PrivateMessage.sender_id == user2.id) & (PrivateMessage.recipient_id == user1.id))
        ).order_by(PrivateMessage.timestamp.asc()).limit(50).all() # Orden ascendente para mostrar más viejos primero

        # Formatear los mensajes para el cliente
        conversation_data = [
            {
                'sender': msg.sender.username,
                'recipient': msg.recipient.username,
                'message': msg.message,
                'timestamp': msg.timestamp.isoformat() # Usar ISO para consistencia
            } for msg in messages
        ]
        
        return conversation_data

    def mark_messages_as_read(self, username: str, other_user: str) -> bool:
        # Obtener los IDs de los usuarios
        user = User.query.filter_by(username=username).first()
        sender = User.query.filter_by(username=other_user).first()

        if not user or not sender: return False

        try:
            # Busca mensajes no leídos enviados por 'other_user' a 'username'
            messages_to_update = PrivateMessage.query.filter(
                PrivateMessage.recipient_id == user.id,
                PrivateMessage.sender_id == sender.id,
                PrivateMessage.read == False # Asume campo boolean 'read' en PrivateMessage
            ).all()

            if messages_to_update:
                for msg in messages_to_update:
                    msg.read = True
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Error DB al marcar mensajes como leídos: {e}")
            return False

    def get_unread_message_count(self, username: str) -> Dict[str, int]:
        unread_counts = {}

        user = User.query.filter_by(username=username).first()
        if not user: return {}

        # Consulta para contar mensajes no leídos agrupados por remitente
        unread_query = db.session.query(
            PrivateMessage.sender_id,
            func.count(PrivateMessage.id) # Contar cuántos mensajes hay por sender_id
        ).filter(
            PrivateMessage.recipient_id == user.id, # Mensajes recibidos por el usuario
            PrivateMessage.read == False          # Que no estén leídos
        ).group_by(PrivateMessage.sender_id).all() # Agrupar por remitente

        # Mapear IDs de remitentes a nombres de usuario
        sender_ids = [sender_id for sender_id, count in unread_query]
        senders = User.query.filter(User.id.in_(sender_ids)).all()
        sender_map = {s.id: s.username for s in senders}

        # Construir el diccionario final
        for sender_id, count in unread_query:
            sender_username = sender_map.get(sender_id)
            if sender_username:
                unread_counts[sender_username] = count

        return unread_counts

    def get_recent_conversations(self, username: str, limit: int = 10) -> List[Dict]:
        # Obtener el usuario actual de la DB
        user = User.query.filter_by(username=username).first()
        if not user:
            return []

        # Consulta avanzada para obtener las conversaciones recientes
        subq = db.session.query(
            # Determina el ID del 'otro' usuario en la conversación
            case(
                (PrivateMessage.sender_id == user.id, PrivateMessage.recipient_id),
                else_=PrivateMessage.sender_id
            ).label("other_user_id"),
            func.max(PrivateMessage.timestamp).label("last_timestamp")
        ).filter(
            (PrivateMessage.sender_id == user.id) | (PrivateMessage.recipient_id == user.id)
        ).group_by("other_user_id").subquery()

        # Consulta principal: une User con la subconsulta para obtener los detalles
        recent_users_q = db.session.query(
            User, subq.c.last_timestamp
        ).join(
            subq, User.id == subq.c.other_user_id
        ).order_by(
            subq.c.last_timestamp.desc() # Ordenar por el último mensaje 
        ).limit(limit)

        # Ejecutar la consulta
        recent_users_with_timestamp = recent_users_q.all()

        # Formatear la salida para el cliente
        conversations = []
        for other_user_obj, last_timestamp in recent_users_with_timestamp:
            # Obtener el último mensaje
            
            # Obtener estado de presencia del otro usuario
            other_user_status = self._get_user_status(other_user_obj.username)

            conversations.append({
                "other_user": {
                    "username": other_user_obj.username,
                    "level": other_user_obj.level,
                    "status": other_user_status
                },
                "timestamp": last_timestamp.isoformat()
            })
            
        return conversations

    def send_room_invitation(self, sender_username: str, recipient_username: str, 
                         room_id: str, room_name: str = None) -> Dict:
        # Obtener los objetos User de la DB
        sender_user = User.query.filter_by(username=sender_username).first()
        recipient_user = User.query.filter_by(username=recipient_username).first()

        if not sender_user or not recipient_user:
            return {"success": False, "message": "Usuario remitente o destinatario no válido."}

        if not sender_user.is_friend(recipient_user):
            return {"success": False, "message": "Solo puedes invitar amigos."}
            
        # Verificar que el destinatario está disponible (solo 'online' en el lobby)
        recipient_status = self._get_user_status(recipient_username)
        if recipient_status == "offline":
            return {"success": False, "message": "El usuario no está conectado."}
        if recipient_status == "in_game":
            return {"success": False, "message": "El usuario está en medio de una partida."}
        if recipient_status == "in_lobby":
            return {"success": False, "message": "El usuario ya está en una sala de espera."}
            
        # Crear invitación
        invitation_data = {
            "id": f"inv_{datetime.now().timestamp()}",
            "sender": sender_username,
            "recipient": recipient_username,
            "room_id": room_id,
            "room_name": room_name or f"Sala de {sender_username}",
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Almacenar invitación temporalmente
        if "invitations" not in self.presence_data:
            self.presence_data["invitations"] = {}
            
        if recipient_username not in self.presence_data["invitations"]:
            self.presence_data["invitations"][recipient_username] = []
            
        self.presence_data["invitations"][recipient_username].append(invitation_data)
        
        self._clean_old_invitations(recipient_username)
        
        return {
            "success": True,
            "message": f"Invitación enviada a {recipient_username}",
            "invitation_data": invitation_data
        }

    def get_pending_invitations(self, username: str) -> List[Dict]:
        if ("invitations" not in self.presence_data or 
            username not in self.presence_data["invitations"]):
            return []
            
        # Limpiar invitaciones antiguas primero
        self._clean_old_invitations(username)
        
        # Devolver solo invitaciones pendientes
        pending = [inv for inv in self.presence_data["invitations"][username] 
                  if inv["status"] == "pending"]
                  
        return pending

    def respond_to_invitation(self, username: str, invitation_id: str, response: str) -> Dict:
        if ("invitations" not in self.presence_data or 
            username not in self.presence_data["invitations"]):
            return {"success": False, "message": "No hay invitaciones"}
            
        # Buscar invitación
        invitation = None
        for inv in self.presence_data["invitations"][username]:
            if inv["id"] == invitation_id and inv["status"] == "pending":
                invitation = inv
                break
                
        if not invitation:
            return {"success": False, "message": "Invitación no encontrada o expirada"}
            
        # Actualizar estado de invitación
        invitation["status"] = "accepted" if response == "accept" else "declined"
        self._save_presence()
        
        if response == "accept":
            return {
                "success": True,
                "message": "Invitación aceptada",
                "room_id": invitation["room_id"]
            }
        else:
            return {
                "success": True,
                "message": "Invitación rechazada"
            }

    def _clean_old_invitations(self, username: str):
        if ("invitations" not in self.presence_data or 
            username not in self.presence_data["invitations"]):
            return
            
        now = datetime.now()
        valid_invitations = []
        
        for invitation in self.presence_data["invitations"][username]:
            inv_time = datetime.fromisoformat(invitation["timestamp"])
            # Mantener invitaciones de menos de 10 minutos
            if (now - inv_time).total_seconds() < 600:  # 10 minutos
                valid_invitations.append(invitation)
            else:
                # Marcar como expirada
                invitation["status"] = "expired"
                valid_invitations.append(invitation)
                
        self.presence_data["invitations"][username] = valid_invitations

    def get_social_achievements(self) -> Dict:
        return self.social_achievements
