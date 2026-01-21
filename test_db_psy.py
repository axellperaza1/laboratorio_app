import psycopg2

try:
    conexion = psycopg2.connect(
            host="localhost",
            database="laboratorio_clinico_ong",
            user="postgres",
            password="Aapf*18*",
            port="5432"
        )
    print("si")
    conexion.close()

except Exception as e:
    print("no")
    print(e)