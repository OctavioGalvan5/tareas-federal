"""
Script para resetear la base de datos y prepararla para produccion.
ADVERTENCIA: Este script eliminara TODOS los datos existentes.
"""
from app import app
from extensions import db
from models import User, Task, Tag, TaskTemplate

def reset_database():
    with app.app_context():
        print("=" * 60)
        print("[!] ADVERTENCIA: RESET DE BASE DE DATOS")
        print("=" * 60)
        print("\nEste script eliminara TODOS los datos de la base de datos:")
        print("  - Usuarios")
        print("  - Tareas")
        print("  - Etiquetas (Tags)")
        print("  - Plantillas de tareas")
        print("\nEstas seguro de que deseas continuar?")
        
        confirmation = input("\nEscribe 'RESETEAR' para confirmar: ")
        
        if confirmation != 'RESETEAR':
            print("\n[X] Operacion cancelada.")
            return
        
        print("\n[...] Eliminando todas las tablas...")
        
        # Drop all tables
        db.drop_all()
        print("[OK] Tablas eliminadas.")
        
        # Recreate all tables
        print("[...] Recreando tablas vacias...")
        db.create_all()
        print("[OK] Tablas recreadas.")
        
        # Create admin user
        print("\n" + "=" * 60)
        print("CREAR USUARIO ADMINISTRADOR")
        print("=" * 60)
        
        username = input("\nNombre de usuario (default: admin): ") or 'admin'
        email = input("Email: ")
        password = input("Contrasena: ")
        full_name = input("Nombre completo: ")
        
        admin = User(
            username=username,
            full_name=full_name,
            email=email,
            is_admin=True
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("[OK] BASE DE DATOS RESETEADA EXITOSAMENTE")
        print("=" * 60)
        print(f"\nUsuario administrador creado:")
        print(f"   - Usuario: {username}")
        print(f"   - Email: {email}")
        print(f"   - Nombre: {full_name}")
        print(f"   - Admin: Si")
        print("\nLa base de datos esta lista para produccion.")

if __name__ == '__main__':
    reset_database()
