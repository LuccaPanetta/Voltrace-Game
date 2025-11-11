# backfill.py
from app import app, db
from models import User
from sqlalchemy import func, select, text

def run_backfill():
    with app.app_context():
        print("Iniciando backfill de friends_count...")

        # Usar 'text' para la subconsulta SQL es más robusto
        # Esto cuenta cuántos amigos (friend_id) tiene cada (user_id)
        subq = text(
            'SELECT user_id, COUNT(friend_id) AS count '
            'FROM friendship '
            'GROUP BY user_id'
        )

        # Mapear los resultados (user_id -> count)
        try:
            result = db.session.execute(subq)
            counts = {row[0]: row[1] for row in result}
        except Exception as e:
            print(f"ERROR al ejecutar la subconsulta: {e}")
            print("Asegúrate de que la tabla 'friendship' exista.")
            return

        # Actualizar usuarios en un bucle
        users_to_update = User.query.filter(User.id.in_(counts.keys())).all()

        if not users_to_update:
            print("No se encontraron usuarios para actualizar (o la tabla 'friendship' está vacía).")
            return

        updated_count = 0
        try:
            for user in users_to_update:
                if user.id in counts:
                    user.friends_count = counts[user.id]
                    updated_count += 1

            db.session.commit()
            print(f"¡Éxito! {updated_count} usuarios fueron actualizados.")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR durante la actualización de usuarios: {e}")

if __name__ == "__main__":
    run_backfill()