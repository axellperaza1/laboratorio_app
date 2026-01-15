from flask import Flask, render_template, request, redirect, url_for, session, make_response
from psycopg2.extras import DictCursor
import psycopg2
from functools import wraps
from datetime import datetime
import qrcode
import io
import base64
from werkzeug.utils import secure_filename
import os
from init_db import init_db

# Para PDF con WeasyPrint
from weasyprint import HTML

# Inicialización de base de datos en Railway
if os.getenv("RAILWAY_ENVIRONMENT"):
    init_db()

# Variable para producción
IS_PRODUCTION = os.getenv("ENV") == "production"

app = Flask(__name__)
app.secret_key = "mi_clave_secreta"

# Función para conectar a la base de datos
def conectar():
    if IS_PRODUCTION:
        # En producción usamos DATABASE_URL
        return psycopg2.connect(os.environ["DATABASE_URL"])
    else:
        # En local
        return psycopg2.connect(
            dbname="laboratorio_clinico_ong",
            user="postgres",
            password="Aapf*18*",
            host="localhost",
        )

# Sistema de seguridad básico
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "cliente_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Página principal
@app.route("/")
def index():
    return render_template("index.html")

# Página de exámenes disponibles
@app.route("/examenes")
def examenes():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM examenes")
    lista_examenes = cursor.fetchall()
    cursor.close()
    conexion.close()

    examenes = [
        {
            "id": examen[0],
            "nombre_examen": examen[1],
            "descripcion": examen[2],
            "precio": examen[3],
        }
        for examen in lista_examenes
    ]

    return render_template("examenes.html", examenes=examenes)

# Registro de exámenes en el área de personal
@app.route("/registrar_examenes", methods=["GET", "POST"])
def registrar_examenes():
    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    # obtener la lista de los pacientes
    cursor.execute("SELECT * FROM pacientes")
    pacientes = cursor.fetchall()
    # Obtener la lista de examenes
    cursor.execute("SELECT * FROM examenes")
    examenes = cursor.fetchall()

    cursor.close()
    conexion.close()

    if request.method == "POST":
        paciente_id = request.form["paciente_id"]
        examenes_id = request.form["examen_id"]
        fecha = request.form["fecha"]
        resultado = request.form["resultado"]

        if not fecha or not resultado:
            return "Fecha o resultado inválido", 400
        try:
            fecha_valida = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return "Fecha inválida", 400

        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO examenes_realizados (paciente_id, examen_id, fecha, resultado) VALUES (%s, %s, %s, %s)",
            (paciente_id, examenes_id, fecha, resultado),
        )
        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for("panel_personal"))

    return render_template(
        "registrar_examenes.html", pacientes=pacientes, examenes=examenes
    )

# Exámenes realizados de un paciente
@app.route("/examenes_realizados/<paciente_id>", methods=["GET"])
def examenes_realizados(paciente_id):
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute(
        """
        SELECT er.id, e.nombre_examen, er.fecha, er.resultado
        FROM examenes_realizados er
        JOIN examenes e ON er.examen_id = e.id
        WHERE er.paciente_id = %s
        """,
        (paciente_id,),
    )
    examenes = cursor.fetchall()

    cursor.close()
    conexion.close()

    if not examenes:
        return "Este paciente no tiene exámenes registrados."

    return render_template(
        "examenes_realizados.html", paciente_id=paciente_id, examenes=examenes
    )

# Login de clientes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        contraseña = request.form["contraseña"]

        conexion = conectar()
        cursor = conexion.cursor(cursor_factory=DictCursor)
        cursor.execute(
            "SELECT * FROM clientes WHERE email = %s AND contraseña = %s",
            (email, contraseña),
        )
        cliente = cursor.fetchone()
        cursor.close()
        conexion.close()

        if cliente:
            session["cliente_id"] = int(cliente["id"])
            session["cliente_nombre"] = cliente["nombre"]
            return redirect(url_for("dashboard", cliente_id=cliente["id"]))
        else:
            return render_template(
                "login.html", error="Correo o contraseñas incorrectos"
            )

    return render_template("login.html")

# Perfil de usuario
@app.route("/perfil")
@login_required
def perfil():
    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    cursor.execute(
        "SELECT nombre, email, telefono, cedula FROM clientes WHERE id = %s",
        (session["cliente_id"],),
    )

    cliente = cursor.fetchone()
    cursor.close()
    conexion.close()

    if not cliente:
        return "Cliente no encontrado", 404

    return render_template("perfil.html", cliente=cliente)

# Registro de cliente
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        cedula = request.form["cedula"]
        telefono = request.form["telefono"]
        contraseña = request.form["contraseña"]

        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO clientes (nombre, email, cedula, telefono, contraseña) VALUES (%s, %s, %s, %s, %s)",
            (nombre, email, cedula, telefono, contraseña),
        )
        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for("login"))

    return render_template("registro.html")

# Dashboard de cliente
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    cliente_id = session["cliente_id"]

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    if request.method == "POST":
        seleccionados = request.form.getlist("examenes")
        for examen_id in seleccionados:
            cursor.execute(
                "INSERT INTO examenes_deseados (cliente_id, examen_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (cliente_id, examen_id),
            )
        conexion.commit()

    cursor.execute(
        "SELECT id, nombre_examen, precio FROM examenes ORDER BY nombre_examen"
    )
    examenes = cursor.fetchall() or []

    cursor.execute(
        "SELECT e.id, e.nombre_examen FROM examenes_deseados ed JOIN examenes e ON ed.examen_id = e.id WHERE ed.cliente_id = %s",
        (cliente_id,),
    )
    pendientes = cursor.fetchall() or []

    cursor.execute(
        "SELECT COALESCE(SUM(e.precio), 0) AS total FROM examenes_deseados ed JOIN examenes e ON ed.examen_id = e.id WHERE ed.cliente_id = %s",
        (cliente_id,),
    )
    total = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT r.archivo_pdf, r.fecha, e.nombre_examen FROM resultados r JOIN examenes e ON e.id = r.examen_id WHERE r.cliente_id = %s",
        (cliente_id,)
    )
    realizados = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "dashboard.html",
        examenes=examenes,
        pendientes=pendientes,
        realizados=realizados,
        total=total,
    )

# PDF de presupuesto
@app.route("/presupuesto_pdf")
@login_required
def presupuesto_pdf():
    cliente_id = session["cliente_id"]

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    cursor.execute(
        "SELECT nombre, cedula, telefono FROM clientes WHERE id = %s",
        (cliente_id,)
    )
    cliente = cursor.fetchone()

    cursor.execute(
        "SELECT e.nombre_examen, e.precio FROM examenes_deseados ed JOIN examenes e ON ed.examen_id = e.id WHERE ed.cliente_id = %s",
        (cliente_id,)
    )
    examenes = cursor.fetchall()

    cursor.execute(
        "SELECT COALESCE(SUM(e.precio), 0) AS total FROM examenes_deseados ed JOIN examenes e ON ed.examen_id = e.id WHERE ed.cliente_id = %s",
        (cliente_id,)
    )
    total = cursor.fetchone()["total"]

    cursor.execute(
        "INSERT INTO presupuestos (cliente_id) VALUES (%s) RETURNING id",
        (cliente_id,)
    )
    numero_presupuesto = cursor.fetchone()["id"]
    conexion.commit()

    cursor.close()
    conexion.close()

    numero_presupuesto = f"P-{numero_presupuesto:06d}"

    # QR
    qr_data = f"Presupuesto {numero_presupuesto} - Cliente {cliente_id}"
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    logo_path = url_for("static", filename="img/ong.png", _external=True)

    # Renderizamos HTML
    rendered = render_template(
        "presupuesto_pdf.html",
        cliente=cliente,
        examenes=examenes,
        total=total,
        fecha=datetime.now().strftime("%d/%m/%Y"),
        logo_path=logo_path,
        numero_presupuesto=numero_presupuesto,
        qr_base64=qr_base64,
    )

    # Solo generamos PDF en producción
    if IS_PRODUCTION:
        pdf = HTML(string=rendered).write_pdf()
        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=presupuesto.pdf"
        return response
    else:
        # En local solo mostramos HTML
        return rendered

# Páginas adicionales
@app.route("/autolab")
def autolab():
    return render_template("autolab.html")

@app.route("/aliados")
def aliados():
    return render_template("aliados.html")

if __name__ == "__main__":
    app.run(debug=True)