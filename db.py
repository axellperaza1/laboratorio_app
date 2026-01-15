import psycopg2

def conectar():
    try:
        conexion = psycopg2.connect(
            host = "localhost",
            user = "postgres",
            password = "Aapf*18*",

database = "laboratorio_clinico_ong"
        )
        return conexion
    except Exception as e:
        print("Error de conexion: ", e)
        return None