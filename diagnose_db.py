from app import app
from extensions import db
from models import User
import sys

def diagnose():
    print("=" * 60)
    print("DIAGNÓSTICO DE BASE DE DATOS")
    print("=" * 60)
    
    with app.app_context():
        # Test 1: Check database connection
        print("\n1. Verificando conexión a la base de datos...")
        try:
            db.engine.connect()
            print("   ✓ Conexión exitosa a la base de datos")
            print(f"   Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
        except Exception as e:
            print(f"   ✗ Error de conexión: {str(e)}")
            return
        
        # Test 2: Check if User table exists
        print("\n2. Verificando si la tabla 'user' existe...")
        try:
            User.query.first()
            print("   ✓ Tabla 'user' existe")
        except Exception as e:
            print(f"   ✗ Error al acceder a la tabla 'user': {str(e)}")
            return
        
        # Test 3: Count users
        print("\n3. Contando usuarios en la base de datos...")
        try:
            user_count = User.query.count()
            print(f"   Total de usuarios: {user_count}")
            
            if user_count == 0:
                print("\n   ⚠️  NO HAY USUARIOS EN LA BASE DE DATOS")
                print("   Necesitas crear un usuario administrador primero.")
                print("   Ejecuta: python create_admin.py")
            else:
                print("\n4. Listando usuarios existentes:")
                users = User.query.all()
                for user in users:
                    print(f"   - Username: {user.username}")
                    print(f"     Nombre: {user.full_name}")
                    print(f"     Email: {user.email}")
                    print(f"     Admin: {user.is_admin}")
                    print(f"     Password hash existe: {bool(user.password_hash)}")
                    print()
                
                # Test 4: Test password verification
                print("5. Probando verificación de contraseña...")
                test_username = input("\n   Ingresa el username que intentaste usar: ")
                test_password = input("   Ingresa la contraseña que intentaste usar: ")
                
                user = User.query.filter_by(username=test_username).first()
                if user:
                    print(f"\n   Usuario '{test_username}' encontrado en la base de datos")
                    if user.check_password(test_password):
                        print("   ✓ La contraseña es CORRECTA")
                        print("   El login debería funcionar. Verifica que estés ingresando")
                        print("   exactamente el mismo usuario y contraseña en el formulario.")
                    else:
                        print("   ✗ La contraseña es INCORRECTA")
                        print("   Necesitas resetear la contraseña o crear un nuevo usuario.")
                else:
                    print(f"\n   ✗ Usuario '{test_username}' NO encontrado en la base de datos")
                    print(f"   Usuarios disponibles: {[u.username for u in users]}")
                    
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    diagnose()
