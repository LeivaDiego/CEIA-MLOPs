# Modulo para manejar la conexión a la base de datos PostgreSQL y la inserción de datos desde un CSV

# --- Librerías ---
# Manejo de rutas y configuración
#   de ruta de modulo
import sys
import os
sys.path.append('/opt/airflow/scripts')
# Conexión a PostgreSQL
import psycopg2 
# Manejo de datos
import pandas as pd
# Manejo de fechas
from datetime import datetime


# --- Configuración del logger ---
# Se importa el logger desde el módulo de utilidades de logging
from log_utils import get_logger
logger = get_logger(__name__)


# --- Funciones ---

def get_postgres_connection():
    """
    Establece una conexión a la base de datos PostgreSQL.
    
    Args:
        None
    
    Returns:
        conn: psycopg2 connection object
    """
    try:
        # Crear la conexión a la base de datos PostgreSQL
        db_conn = psycopg2.connect(
            host="postgres",    # nombre del servicio en docker-compose
            database="airflow", # nombre de la base de datos
            user="airflow",     # nombre de usuario
            password="airflow", # contraseña
            port=5432           # puerto por defecto de PostgreSQL
        )

        # Retornar la conexión
        return db_conn
    
    except Exception as e:
        # Si ocurre un error, se imprime el error y se lanza una excepción
        logger.critical(f"Error al conectar a PostgreSQL: {e}")
        raise


def create_validation_log_table():
    """
    Crea la tabla validation_log en la base de datos PostgreSQL si no existe. 

    Args:
        None

    Returns:
        None
    """
    # Definición de la consulta SQL para crear la tabla
    # Si la tabla ya existe, no se crea de nuevo
    create_table_query = """
    CREATE TABLE IF NOT EXISTS validation_log (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP,
        country VARCHAR(100),
        date DATE,
        reason TEXT
    );
    """
    try:
        # Obtener la conexión a la base de datos
        conn = get_postgres_connection()
        # Crear un cursor para ejecutar la consulta
        cursor = conn.cursor()
        # Ejecutar la consulta para crear la tabla
        cursor.execute(create_table_query)
        # Confirmar los cambios en la base de datos
        conn.commit()
        # Mensaje de confirmación
        logger.info("Tabla 'weather_data' verificada o creada correctamente.")
    
    except Exception as e:
        # Si ocurre un error, se imprime el error y se lanza una excepción
        logger.error(f"Error al crear la tabla 'validation_log': {e}")
        raise
    
    finally:
        # Cerrar el cursor y la conexión a la base de datos
        cursor.close()
        conn.close()


def create_model_metrics_table():
    """
    Crea la tabla model_metrics en la base de datos PostgreSQL si no existe. 

    Args:
        None

    Returns:
        None
    """
    # Definición de la consulta SQL para crear la tabla
    # Si la tabla ya existe, no se crea de nuevo
    # Tabla de métricas de modelos
    create_table_query = """
    CREATE TABLE IF NOT EXISTS model_metrics (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP,
        model_version VARCHAR(100),
        model_path TEXT,
        accuracy FLOAT,
        precision FLOAT,
        recall FLOAT,
        f1_score FLOAT,
        is_valid BOOLEAN DEFAULT TRUE
    );
    """
    try:
        # Obtener la conexión a la base de datos
        conn = get_postgres_connection()
        # Crear un cursor para ejecutar la consulta
        cursor = conn.cursor()
        # Ejecutar la consulta para crear la tabla
        cursor.execute(create_table_query)
        # Confirmar los cambios en la base de datos
        conn.commit()
        # Mensaje de confirmación
        logger.info("Tabla 'model_metrics' verificada o creada exitosamente.")

    except Exception as e:
        # Si ocurre un error, se imprime el error y se lanza una excepción
        logger.error(f"Error al crear la tabla 'model_metrics': {e}")
        raise
    finally:
        # Cerrar el cursor y la conexión a la base de datos
        cursor.close()
        conn.close()


def create_weather_table():
    """
    Crea la tabla weather_data en la base de datos PostgreSQL si no existe. 

    Args:
        None

    Returns:
        None
    """
    # Definición de la consulta SQL para crear la tabla
    # Si la tabla ya existe, no se crea de nuevo
    create_table_query = """
    CREATE TABLE IF NOT EXISTS weather_data (
        id SERIAL PRIMARY KEY,
        country VARCHAR(100),
        date DATE UNIQUE,
        avg_temp_c FLOAT,
        max_temp_c FLOAT,
        min_temp_c FLOAT,
        humidity INTEGER,
        wind_kph FLOAT,
        condition VARCHAR(100),
        chance_of_rain INTEGER,
        will_it_rain INTEGER,
        totalprecip_mm FLOAT,
        uv FLOAT
    );
    """
    try:
        # Obtener la conexión a la base de datos
        conn = get_postgres_connection()
        # Crear un cursor para ejecutar la consulta
        cursor = conn.cursor()
        # Ejecutar la consulta para crear la tabla
        cursor.execute(create_table_query)
        # Confirmar los cambios en la base de datos
        conn.commit()
        # Mensaje de confirmación
        logger.info("Tabla 'weather_data' verificada o creada exitosamente.")
    except Exception as e:
        # Si ocurre un error, se imprime el error y se lanza una excepción
        logger.error(f"Error al crear la tabla 'weather_data': {e}")
        raise
    finally:
        # Cerrar el cursor y la conexión a la base de datos
        cursor.close()
        conn.close()


def validate_row(row):
    """
    Valida una fila del DataFrame para asegurarse de que contiene datos válidos.
    Si la fila no es válida, se omite al insertar en la base de datos.

    Args:
        row (pd.Series): Fila del DataFrame a validar.

    Returns:
        str: Mensaje de error si la fila no es válida.

    Raises:
        Exception: Si ocurre un error durante la validación.
    """
    try:
        if row is None:
            return "Row is None"
        # Validacion de los datos de la fila
        #   Verifica si los campos obligatorios están presentes y no son nulos
        #   y si los valores son del tipo correcto
        
        # Si el país es nulo o vacío, se omite la fila
        if pd.isna(row['country']) or str(row['country']).strip() == "":
            return "Country is null or empty"
        
        # Si la fecha es nula o no es una fecha válida, se omite la fila
        if pd.isna(row['date']) or not pd.to_datetime(row['date'], errors='coerce'):
            return "Date is null or invalid"
        
        # Si los valores de temperatura, humedad, viento, etc. son nulos se omite la fila
        if any(pd.isna(row[col]) for col in [
            'avg_temp_c', 'max_temp_c', 'min_temp_c', 'humidity', 
            'wind_kph', 'condition', 'chance_of_rain', 'will_it_rain', 
            'totalprecip_mm', 'uv']):
            return "One or more required fields are null"
        
        # Si los valores de humedad, probabilidad de lluvia, etc. están fuera de rango, se omite la fila
        if not (0 <= row['humidity'] <= 100):
            return "Humidity is out of range (0-100)"
        if not (0 <= row['chance_of_rain'] <= 100):
            return "Chance of rain is out of range (0-100)"
        
        # Si la probabilidad de lluvia no es 0 o 1 (booleano), se omite la fila
        if not (row['will_it_rain'] in [0, 1]):
            return "Will it rain is not a boolean value"
        
        # Si la velocidad del viento es negativa, se omite la fila
        if row['wind_kph'] < 0:
            return "Wind speed is negative"
        
        # Si la temperatura promedio, máxima o mínima están fuera de rango, se omite la fila
        #   Las temperaturas están en grados Celsius y se validan entre -100 y 100
        if row['avg_temp_c'] < -100 or row['avg_temp_c'] > 100:
            return "Average temperature is out of range (-100 to 100)"
        if row['max_temp_c'] < -100 or row['max_temp_c'] > 100:
            return "Maximum temperature is out of range (-100 to 100)"
        if row['min_temp_c'] < -100 or row['min_temp_c'] > 100:
            return "Minimum temperature is out of range (-100 to 100)"
        
        # Si la precipitación total es negativa, se omite la fila
        if row['totalprecip_mm'] < 0:
            return "Total precipitation is negative"
        
        # Si el índice UV es negativo o mayor a 11, se omite la fila
        #   El índice UV generalmente varía entre 0 y 10, aunque puede ser mayor en condiciones extremas
        #   pero se considera que un índice UV de 11 es poco común pues es extremadamente alto.
        if not (0 <= row['uv'] <= 11):
            return "UV index is out of range (0-11)"
        
        # Si todos los chequeos pasan, la fila es válida
        #   Se puede agregar más validaciones según sea necesario
        return None
        
    except Exception as e:
        logger.error(f"Fallo en la validación de la fila: {e}")
        return f"Unexpected error at validation: {e}"  # Si algo falla, se descarta la fila


def insert_weather_forecast(record):
    """
    Inserta un solo registro de clima en la tabla weather_data de PostgreSQL.
    Valida el registro antes de la inserción. Si el registro no es válido, se omite.
    Si el registro ya existe en la base de datos, se omite la inserción.

    Args:
        record (dict): Registro de clima a insertar. Debe contener las claves:
            'country', 'date', 'avg_temp_c', 'max_temp_c', 'min_temp_c',
            'humidity', 'wind_kph', 'condition', 'chance_of_rain',
            'will_it_rain', 'totalprecip_mm', 'uv'

    Returns:
        bool: True si la inserción fue exitosa, False si se omitió el registro.
    """
    if record is None:
        logger.warning("Registro de clima es None. No se insertará.")
        return False
    
    # Leer el registro en un DataFrame de pandas
    #   Se espera que el registro sea un diccionario con los datos del clima
    df = pd.DataFrame([record])

    # Obtener la conexión a la base de datos
    #   y crear un cursor para ejecutar las consultas
    conn = get_postgres_connection()
    cursor = conn.cursor()
    
    # Iterar sobre cada fila del DataFrame 
    for index, row in df.iterrows():
        # Validar la fila antes de la inserción
        reason = validate_row(row)
        if reason is None:
            try:
                # Si la fila es válida, preparar la consulta de inserción
                #   y ejecutar la consulta
                insert_query = """
                INSERT INTO weather_data (country, date, avg_temp_c, max_temp_c, min_temp_c,
                                        humidity, wind_kph, condition, chance_of_rain,
                                        will_it_rain, totalprecip_mm, uv)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO NOTHING;
                """
                # Ejecutar la consulta de inserción con los valores de la fila
                #   Se utiliza ON CONFLICT para evitar duplicados
                cursor.execute(insert_query, (
                    row['country'],
                    row['date'],
                    row['avg_temp_c'],
                    row['max_temp_c'],
                    row['min_temp_c'],
                    row['humidity'],
                    row['wind_kph'],
                    row['condition'],
                    row['chance_of_rain'],
                    row['will_it_rain'],
                    row['totalprecip_mm'],
                    row['uv'],
                ))
            except Exception as e:
                # Si ocurre un error durante la inserción, se registra el error
                logger.error(f"Error al insertar el registro de clima: {e}")
                # Registrar el error de validación en la base de datos
                log_validation_error(row.to_dict(), str(e))
                return False
        else:
            logger.warning(f"Registro de clima {index} omitido: {reason}")
            log_validation_error(row.to_dict(), reason)
            return False # Si la fila no es válida, se omite

    # Confirmar los cambios en la base de datos
    conn.commit()

    # Cerrar el cursor y la conexión a la base de datos
    cursor.close()
    conn.close()

    # Mensaje de confirmación
    logger.info(f"Registro insertado exitosamente: {record.get('date', 'fecha_desconocida')}")

    return True # Retornar True si la inserción fue exitosa


def insert_history_data(file_path="/opt/airflow/data/weather_data.csv"):
    """
    Inserta datos de un archivo CSV en la tabla weather_data de PostgreSQL.

    Valida cada fila antes de la inserción. Si la fila no es válida, se omite.
    Si la fila ya existe en la base de datos, se omite la inserción.

    Args:
        file_path (str): Ruta del archivo CSV que contiene los datos de clima. (default: "/opt/airflow/data/weather_data.csv")

    Returns:
        None

    Raises:
        Exception: Si ocurre un error durante la inserción de datos.
    """
    logger.info(f"Iniciando carga de histórico desde: {file_path}")

    try:
        # Leer el archivo CSV en un DataFrame de pandas
        df = pd.read_csv(file_path)

        # Validar que el DataFrame no esté vacío
        if df.empty:
            logger.warning(f"Archivo CSV {file_path} está vacío. No se insertaron registros.")
            return

        # Contadores para filas insertadas y omitidas
        inserted_rows = 0
        skipped_rows = 0

        # Iterar sobre cada fila del DataFrame
        for index, row in df.iterrows():
            # Insertar el registro en la base de datos
            #   y validar la fila antes de la inserción
            if insert_weather_forecast(row.to_dict()):
                inserted_rows += 1
            else:
                skipped_rows += 1

        # Mensaje de confirmación
        logger.info(f"Carga completa desde {file_path} - Insertados: {inserted_rows}, Omitidos: {skipped_rows}")
    except FileNotFoundError:
        logger.error(f"Archivo no encontrado: {file_path}.")
        raise
    except pd.errors.ParserError as e:
        logger.error(f"Error al leer el archivo CSV: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado al insertar datos desde CSV: {e}")
        raise


def log_validation_error(record, reason):
    """
    Registra un error de validación en la tabla validation_errors de PostgreSQL.

    Args:
        record (dict): Registro de clima que falló la validación.
        reason (str): Motivo del error de validación.
    """
    try:
        # Obtener la conexión a la base de datos
        conn = get_postgres_connection()
        cursor = conn.cursor()

        # Definición de la consulta SQL para insertar el error de validación
        insert_error_query = """
        INSERT INTO validation_errors (timestamp, country, date, reason)
        VALUES (%s, %s, %s, %s);
        """

        # Ejecutar la consulta de inserción con los valores del registro
        cursor.execute(insert_error_query, (
            datetime.now(),
            record.get('country', 'N/A'),
            record.get('date', None),
            reason
        ))

        # Confirmar los cambios en la base de datos
        conn.commit()

        # Mensaje de confirmación
        logger.info(f"Error de validación registrado: {record.get('date', 'sin fecha')} - Motivo: {reason}")

    except Exception as e:
        # Si ocurre un error, se imprime el error y se lanza una excepción
        logger.error(f"Fallo al registrar error de validación ({record.get('date', 'sin fecha')}): {e}")
        raise

    finally:
        # Cerrar el cursor y la conexión a la base de datos
        cursor.close()
        conn.close()


def log_model_metrics(metrics, model_path, model_version):
    """
    Registra las métricas de un modelo entrenado en la tabla model_metrics de PostgreSQL.

    Args:
        metrics (dict): Diccionario con las métricas del modelo (accuracy, f1_score, etc.)
        model_path (str): Ruta donde se guardó el modelo.
        model_version (str): Versión del modelo.

    Returns:
        None
    """
    try:
        # Validar que las métricas contengan los campos requeridos
        required_keys = ['accuracy', 'precision', 'recall', 'f1_score']

        missing_or_invalid = [k for k in required_keys if k not in metrics or metrics[k] is None]
        if missing_or_invalid:
            logger.warning(f"No se registraron métricas: campos faltantes o inválidos - {missing_or_invalid}")
            return

        if metrics is None or model_path is None or model_version is None:
            logger.warning("No se registraron métricas, ruta o versión del modelo son None.")
            return

        # Obtener la conexión a la base de datos
        conn = get_postgres_connection()
        cursor = conn.cursor()

        # Definición de la consulta SQL para insertar las métricas del modelo
        insert_metrics_query = """
        INSERT INTO model_metrics (
            timestamp, model_version, model_path,
            accuracy, precision, recall, f1_score, is_valid
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """

        # Ejecutar la consulta de inserción con los valores de las métricas
        cursor.execute(insert_metrics_query, (
            datetime.now(),
            model_version,
            model_path,
            metrics.get('accuracy'),
            metrics.get('precision'),
            metrics.get('recall'),
            metrics.get('f1_score'),
            metrics.get('is_valid', True)  # Por defecto, se considera válido
        ))

        # Confirmar los cambios en la base de datos
        conn.commit()

        # Mensaje de confirmación
        logger.info(f"Métricas del modelo registradas: {model_version} ({model_path})")

    except Exception as e:
        # Si ocurre un error, se imprime el error y se lanza una excepción
        logger.error(f"Fallo al registrar métricas del modelo ({model_version} - {model_path}): {e}")
        raise

    finally:
        # Cerrar el cursor y la conexión a la base de datos
        cursor.close()
        conn.close()