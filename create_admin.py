from app import app
from extensions import db
from models import User

def create_admin():
    with app.app_context():
        print("Creando usuario administrador...")
        username = input("Ingrese nombre de usuario (default: admin): ") or 'admin'
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            print(f"El usuario '{username}' ya existe.")
            return
        
        email = input("Ingrese email: ")
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            print(f"El email '{email}' ya está en uso.")
            return
        
        password = input("Ingrese contraseña: ")
        full_name = input("Ingrese nombre completo: ")
        
        admin = User(
            username=username,
            full_name=full_name,
            email=email,
            is_admin=True
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        print(f"Usuario administrador '{username}' creado exitosamente.")

if __name__ == '__main__':
    create_admin()
