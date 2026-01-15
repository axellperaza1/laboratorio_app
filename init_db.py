import os
import psycopg2

def init_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        cedula TEXT,
        telefono TEXT,
        email TEXT,
        password TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS examenes (
        id SERIAL PRIMARY KEY,
        nombre_examen TEXT NOT NULL,
        descripcion TEXT,
        precio NUMERIC(10,2) NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS examenes_deseados (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
        examen_id INTEGER REFERENCES examenes(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS resultados (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES clientes(id),
        examen_id INTEGER REFERENCES examenes(id),
        archivo_pdf TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS presupuestos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES clientes(id),
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()