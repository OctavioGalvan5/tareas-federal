from app import app
from extensions import db
from models import User

def create_admin():
    with app.app_context():
        # Check if admin exists
        if User.query.filter_by(username='admin').first():
            print("El usuario 'admin' ya existe.")
            return

        print("Creando usuario administrador...")
        username = input("Ingrese nombre de usuario (default: admin): ") or 'admin'
        password = input("Ingrese contraseña: ")
        full_name = input("Ingrese nombre completo: ")
        
        admin = User(
            username=username,
            full_name=full_name,
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        print(f"Usuario administrador '{username}' creado exitosamente.")

if __name__ == '__main__':
    create_admin()
