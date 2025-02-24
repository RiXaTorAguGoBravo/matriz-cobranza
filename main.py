import pandas as pd
from sqlalchemy import create_engine

# Datos de conexión
DATABASE_TYPE = 'postgresql'
USER = 'ricardo.torres'
PASSWORD = r'UW`bv&&rg>2!kwo\eOaD' # Usamos raw string para evitar errores de escape
HOST = '34.123.217.240'
PORT = '5432'
DATABASE = 'credito'

# Crear la conexión con SQLAlchemy
engine = create_engine(f"{DATABASE_TYPE}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")

# Escribir la consulta
query = "SELECT * FROM CREDITS LIMIT 5;"

# Leer la tabla en un DataFrame
try:
    df = pd.read_sql_query(query, con=engine)
    print(df)  # Mostrar los datos
except Exception as e:
    print(f"Error al ejecutar la consulta: {e}")
