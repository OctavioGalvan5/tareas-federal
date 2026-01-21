"""
MinIO/S3 Storage Utilities
Maneja la subida, descarga y eliminación de archivos en MinIO.
"""
import os
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Configuración desde variables de entorno
# Configuración desde variables de entorno
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.environ.get('MINIO_BUCKET', 'task-attachments')
MINIO_SECURE = os.environ.get('MINIO_SECURE', 'False').lower() == 'true'

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def get_s3_client():
    """
    Crea y retorna un cliente S3 configurado para MinIO.
    """
    protocol = 'https' if MINIO_SECURE else 'http'
    endpoint_url = f"{protocol}://{MINIO_ENDPOINT}"
    
    client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'  # MinIO ignora esto pero boto3 lo requiere
    )
    
    return client

def ensure_bucket_exists():
    """
    Verifica que el bucket existe, si no lo crea.
    """
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code in ['404', 'NoSuchBucket']:
            # Crear el bucket si no existe
            client.create_bucket(Bucket=MINIO_BUCKET)
            print(f"Bucket '{MINIO_BUCKET}' creado exitosamente.")
        else:
            raise

def allowed_file(filename):
    """
    Verifica si la extensión del archivo está permitida.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file(file, task_id, filename):
    """
    Sube un archivo a MinIO.
    
    Args:
        file: Objeto file-like (de request.files)
        task_id: ID de la tarea
        filename: Nombre del archivo (sanitizado)
    
    Returns:
        tuple: (success, file_key o error_message)
    """
    try:
        client = get_s3_client()
        
        # Construir la key del archivo
        file_key = f"tasks/{task_id}/{filename}"
        
        # Leer el contenido del archivo
        file_content = file.read()
        file_size = len(file_content)
        
        # Verificar tamaño
        if file_size > MAX_FILE_SIZE:
            return False, f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE / (1024*1024):.0f} MB"
        
        # Volver al inicio del archivo
        file.seek(0)
        
        # Determinar content type
        content_type = file.content_type or 'application/octet-stream'
        
        # Subir a MinIO
        client.upload_fileobj(
            file,
            MINIO_BUCKET,
            file_key,
            ExtraArgs={
                'ContentType': content_type,
                'ContentDisposition': f'attachment; filename="{filename}"'
            }
        )
        
        return True, file_key
        
    except ClientError as e:
        return False, f"Error al subir archivo: {str(e)}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def download_file(file_key):
    """
    Descarga un archivo de MinIO.
    
    Args:
        file_key: Key del archivo en MinIO
    
    Returns:
        tuple: (success, file_data o error_message)
    """
    try:
        client = get_s3_client()
        
        response = client.get_object(Bucket=MINIO_BUCKET, Key=file_key)
        file_data = response['Body'].read()
        content_type = response.get('ContentType', 'application/octet-stream')
        
        return True, {'data': file_data, 'content_type': content_type}
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            return False, "Archivo no encontrado"
        return False, f"Error al descargar archivo: {str(e)}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def delete_file(file_key):
    """
    Elimina un archivo de MinIO.
    
    Args:
        file_key: Key del archivo en MinIO
    
    Returns:
        tuple: (success, message)
    """
    try:
        client = get_s3_client()
        client.delete_object(Bucket=MINIO_BUCKET, Key=file_key)
        return True, "Archivo eliminado exitosamente"
        
    except ClientError as e:
        return False, f"Error al eliminar archivo: {str(e)}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def get_file_url(file_key, expires_in=3600):
    """
    Genera una URL pre-firmada para acceder temporalmente a un archivo.
    
    Args:
        file_key: Key del archivo en MinIO
        expires_in: Segundos hasta que expire la URL (default: 1 hora)
    
    Returns:
        str: URL pre-firmada
    """
    try:
        client = get_s3_client()
        
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': MINIO_BUCKET,
                'Key': file_key
            },
            ExpiresIn=expires_in
        )
        
        return url
        
    except Exception as e:
        return None
