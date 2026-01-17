from flask import Flask, render_template, request, redirect, url_for, session
from db import conectar
from psycopg2.extras import DictCursor
import psycopg2
from functools import wraps
from flask import session, redirect, url_for
from flask import request, jsonify, make_response, Response
from datetime import datetime
import qrcode
import io
import base64
from werkzeug.utils import secure_filename
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from io import BytesIO
from whitenoise import WhiteNoise


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.wsgi_app = WhiteNoise(
    app.wsgi_app, root=os.path.join(BASE_DIR, "static"), prefix="static/"
)


# Página principal
@app.route("/")
def index():
    return render_template("index.html")


app.secret_key = "mi_clave_secreta"

import os
import psycopg2


def conectar():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # PRODUCCIÓN (Railway)
        return psycopg2.connect(database_url)


# Este es el sistema de seguridad básico.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "cliente_id" not in session:
            return
        redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


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


# para registrar los examenes en el area de personal
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

        if not fecha:
            return
        if not resultado:
            return
        try:
            from datetime import datetime

            fecha_valida = datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return

        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO examenes_realizados (paciente_id, examen_id, fecha, resultado) VALUES (%s, %s, %s, %s)",
            (paciente_id, examenes_id, fecha, resultado),
        )
        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for("panel_personal"))  # Regresar al inicio

    return render_template(
        "registrar_examenes.html", pacientes=pacientes, examenes=examenes
    )


@app.route("/examenes_realizados/<paciente_id>", methods=["GET"])
def examenes_realizados(paciente_id):
    conexion = conectar()
    cursor = conexion.cursor()

    # Obtener los exámenes realizados para el paciente específico
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

    # Verificamos si hay exámenes
    if not examenes:
        return "Este paciente no tiene exámenes registrados."

    return render_template(
        "examenes_realizados.html", paciente_id=paciente_id, examenes=examenes
    )


# este es para logear el cliente
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        contraseña = request.form["contraseña"]

        # Verificar si el cliente existe en la base de datos
        conexion = conectar()
        cursor = conexion.cursor(cursor_factory=DictCursor)
        cursor.execute(
            "SELECT * FROM clientes WHERE email = %s AND contraseña = %s",
            (email, contraseña),
        )
        cliente = cursor.fetchone()

        if cliente:  # Si el cliente existe
            # Guardamos la información del cliente en la sesión (para mantenerlo logueado)
            session["cliente_id"] = int(cliente["id"])
            session["cliente_nombre"] = cliente["nombre"]
            return redirect(
                url_for("dashboard", cliente_id=cliente["id"])
            )  # Redirigir al perfil del cliente
        else:
            # Si las credenciales no coinciden
            return render_template(
                "login.html", error="Correo o contraseñas incorrectos"
            )

    return render_template("login.html")


# perfil de el usuario
@app.route("/perfil")
def perfil():
    if "cliente_id" not in session:
        return redirect(url_for("login"))

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    cursor.execute(
        """
        SELECT nombre, email, telefono, cedula
        FROM clientes
        WHERE id = %s
    """,
        (session["cliente_id"],),
    )

    cliente = cursor.fetchone()
    conexion.close()
    cursor.close()

    if not cliente:
        return "Cliente no encontrado", 404

    return render_template("perfil.html", cliente=cliente)


# area de registro de los clientes, por si no tiene usuario
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        cedula = request.form["cedula"]
        telefono = request.form["telefono"]
        contraseña = request.form["contraseña"]

        # Guardar en la base de datos (no olvides validar)
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO clientes (nombre, email, cedula, telefono, contraseña) VALUES (%s, %s, %s, %s, %s)",
            (nombre, email, cedula, telefono, contraseña),
        )
        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for("login"))  # Redirigir al login después de registrar

    return render_template("registro.html")


# consulta de examenes disponibles
@app.route("/examenes_disponibles", methods=["GET"])
def examenes_disponibles():
    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    # Obtener todos los exámenes disponibles
    cursor.execute(" SELECT * FROM examenes")
    examenes = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("examenes_disponibles.html", examenes=examenes)


# login del personal, donde se puede logear
@app.route("/login_personal", methods=["GET", "POST"])
def login_personal():
    if request.method == "POST":
        cedula = request.form["cedula"]
        contraseña = request.form["contraseña"]

        conexion = conectar()
        cursor = conexion.cursor(cursor_factory=DictCursor)

        cursor.execute(
            "SELECT * FROM personal WHERE cedula = %s AND contraseña = %s",
            (cedula, contraseña),
        )
        personal = cursor.fetchone()

        cursor.close()
        conexion.close()

        if personal:
            session["personal_id"] = int(personal["id"])
            session["personal_nombre"] = personal["nombre"]
            session["personal_rol"] = personal["rol"]
            return redirect(url_for("panel_personal"))
        else:
            return "cedula o contraseña incorrecta"

    return render_template("login_personal.html")


# panel de trabajo del personal
@app.route("/panel_personal", methods=["GET", "POST"])
def panel_personal():

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        examen_id = request.form["examen_id"]
        pdf = request.files["resultado_pdf"]

        filename = secure_filename(pdf.filename)
        ruta = f"static/resultados/pdfs/{filename}"
        pdf.save(ruta)

        cursor.execute(
            """
            INSERT INTO resultados (cliente_id, examen_id, archivo_pdf)
            VALUES (%s, %s, %s)
        """,
            (cliente_id, examen_id, ruta),
        )

        conexion.commit()

    cursor.execute("SELECT id, nombre FROM clientes")
    clientes = cursor.fetchall()

    cursor.execute("SELECT id, nombre_examen FROM examenes")
    examenes = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("panel_personal.html", clientes=clientes, examenes=examenes)


# funcion logout para todos
@app.route("/logout")
def logout():
    session.clear()
    return render_template("index.html")


# funcion solo para el personal del lab
@app.route("/registrar_examenes", methods=["GET", "POST"])
def registrar_examanes():
    if "personal_id" not in session:
        return
    redirect(url_for("login_personal"))

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT id, nombre, email FROM pacientes")
    pacientes = cursor.fetchall()

    cursor.execute(
        """ SELECT ed.id, p.nombre AS paciente, e.nombre_examen, ed.estado FROM examenes_deseados ed JOIN pacientes p ON ed.cliente_id
                   =p.id
                   JOIN examenes e ON ed.examen_id =e.id 
                   WHERE ed.estado = 'pendiente'"""
    )
    examenes_pendientes = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        "panel_personal.html",
        pacientes=pacientes,
        examenes_pendientes=examenes_pendientes,
    )


# funcion de seleccion de examenes en el area de clientes
@app.route("/seleccionar_examenes", methods=["POST"])
def seleccionar_examenes():
    if "cliente_id" not in session:
        return redirect(url_for("login"))

    cliente_id = session["cliente_id"]
    examen_ids = request.form.getlist("examenes_deseados")

    conexion = conectar()
    cursor = conexion.cursor()

    for examen_id in examen_ids:
        cursor.execute(
            """INSERT INTO examenes_deseados(cliente_id, examen_id) VALUES (%s, %s)""",
            (cliente_id, examen_id),
        )

    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for("dashboard"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "cliente_id" not in session:
        return redirect(url_for("login"))

    cliente_id = session["cliente_id"]

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    if request.method == "POST":
        seleccionados = request.form.getlist("examenes")

        for examen_id in seleccionados:
            cursor.execute(
                """
                INSERT INTO examenes_deseados (cliente_id, examen_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """,
                (cliente_id, examen_id),
            )

        conexion.commit()
        cursor.close()
        conexion.close()

        # 🔥 ESTA LÍNEA ES LA CLAVE
        return redirect(url_for("dashboard"))

    cursor.execute(
        """
        SELECT id, nombre_examen, precio
        FROM examenes
        ORDER BY nombre_examen
    """
    )
    examenes = cursor.fetchall() or []

    cursor.execute(
        """
        SELECT e.id, e.nombre_examen
        FROM examenes_deseados ed
        JOIN examenes e ON ed.examen_id = e.id
        WHERE ed.cliente_id = %s
    """,
        (cliente_id,),
    )
    pendientes = cursor.fetchall() or []

    cursor.execute(
        """ SELECT COALESCE(SUM(e.precio), 0) AS total FROM examenes_deseados ed JOIN examenes e ON ed.examen_id = e.id WHERE ed.cliente_id = %s """,
        (cliente_id,),
    )

    total = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT 
            r.archivo_pdf,
            r.fecha,
            e.nombre_examen
        FROM resultados r
        JOIN examenes e ON e.id = r.examen_id
        WHERE r.cliente_id = %s
    """,
        (session["cliente_id"],),
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


@app.route("/quitar_examen/<int:examen_id>", methods=["POST"])
def quitar_examen(examen_id):
    if "cliente_id" not in session:
        return redirect(url_for("login"))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute(
        """ DELETE FROM examenes_deseados WHERE cliente_id = %s and examen_id = %s """,
        (session["cliente_id"], examen_id),
    )

    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for("dashboard"))


# esto es solo  del admin
@app.route("/agregar_examen_db", methods=["GET", "POST"])
def agregar_examen_db():
    mensaje = None

    conexion = conectar()
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre_examen = request.form.get("nombre_examen")
        descripcion = request.form.get("descripcion")
        precio = request.form.get("precio")

        cursor.execute(
            """
            INSERT INTO examenes (nombre_examen, descripcion, precio)
            VALUES (%s, %s, %s)
        """,
            (nombre_examen, descripcion, precio),
        )

        conexion.commit()
        mensaje = "Examen agregado correctamente"

    # ESTO sí puede ir fuera
    cursor.execute(
        """
        SELECT id, nombre_examen, descripcion, precio
        FROM examenes
        ORDER BY id DESC
    """
    )
    examenes = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("agregar_examen_db.html", mensaje=mensaje, examenes=examenes)


@app.route("/presupuesto_pdf")
def presupuesto_pdf():

    if "cliente_id" not in session:
        return redirect(url_for("login"))

    cliente_id = session["cliente_id"]

    conexion = conectar()
    cursor = conexion.cursor(cursor_factory=DictCursor)

    cursor.execute(
        """
        SELECT nombre
        FROM clientes
        WHERE id = %s
    """,
        (cliente_id,),
    )
    cliente = cursor.fetchone()

    cursor.execute(
        """
        SELECT e.nombre_examen, e.precio
        FROM examenes_deseados ed
        JOIN examenes e ON e.id = ed.examen_id
        WHERE ed.cliente_id = %s
    """,
        (cliente_id,),
    )
    examenes = cursor.fetchall()

    cursor.close()
    conexion.close()

    total = sum(e["precio"] for e in examenes)

    # =========================
    # PDF EN MEMORIA
    # =========================
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # =========================
    # BRANDING
    # =========================
    color_principal = HexColor("#3C0606")
    color_secundario = HexColor("#732323")

    logo_path = "static/img/ong.png"
    logo = ImageReader (logo_path)

    
    
    p.drawImage(
                logo,
                2 * cm,
                height - 4 * cm,
                width=3 * cm,
                height=3 * cm,
                preserveAspectRatio=True,
                mask="auto",
            )
       

    # =========================


# ENCABEZADO
# =========================
    text_x = 6*cm
    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(color_principal)
    p.drawString(text_x, height - 2.2 * cm, "LABORATORIO CLÍNICO ONG, C.A.")

    p.setFont("Helvetica", 9)
    p.setFillColor(color_secundario)
    p.drawString(text_x, height - 2.9 * cm, "RIF: J-29703979-1")

    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(color_secundario)
    p.drawString(text_x, height - 3.7 * cm, "Presupuesto de Exámenes Clínicos")

    p.setStrokeColor(color_principal)
    p.setLineWidth(1)
    p.line(2 * cm, height - 4.2 * cm, width - 2 * cm, height - 4.2 * cm)

    # =========================
    # INFORMACIÓN DEL PACIENTE
    # =========================
    p.setFont("Helvetica", 10)
    p.setFillColorRGB(0, 0, 0)

    p.drawString(2 * cm, height - 5.3 * cm, f"Paciente: {cliente['nombre']}")
    p.drawString(
        2 * cm,
        height - 6.0 * cm,
        f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y')}",
    )
    p.drawString(2 * cm, height - 6.7 * cm, "Validez del presupuesto: 7 días")

    # =========================
    # TABLA DE EXÁMENES
    # =========================
    y = height - 8.3 * cm

    p.setFont("Helvetica-Bold", 10)
    p.drawString(2 * cm, y, "Examen solicitado")
    p.drawRightString(17 * cm, y, "Precio")

    y -= 0.3 * cm
    p.line(2 * cm, y, width - 2 * cm, y)

    p.setFont("Helvetica", 10)

    for e in examenes:
        y -= 0.7 * cm
        p.drawString(2 * cm, y, e["nombre_examen"])
        p.drawRightString(17 * cm, y, f"${e['precio']:.2f}")

    # =========================
    # TOTAL
    # =========================
    y -= 1 * cm
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(17 * cm, y, f"TOTAL A PAGAR: ${total:.2f}")

    # =========================
    # NOTA LEGAL
    # =========================

    # Línea separadora
    p.setStrokeColor(color_principal)
    p.setLineWidth(0.5)
    p.line(2*cm, 2.8*cm, width - 2*cm, 2.8*cm)

    # Texto legal
    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawCentredString(
        width / 2,
        2.1*cm,
        "Para que este documento sea válido, debe presentarse al laboratorio para su firma y sello."
    )

    p.drawCentredString(
        width / 2,
        1.7*cm,
        "De lo contrario, no será validado."
    )

    # =========================
    # PIE DE PÁGINA
    # =========================
    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.drawCentredString(
        width / 2,
        1.5 * cm,
        "Los precios están sujetos a la tasa cambiaria del Banco Central De Venezuela",
        "Laboratorio Clínico ONG, C.A. • J-29703979-1 ",
    )

    p.showPage()
    p.save()
    buffer.seek(0)

    return Response(
        buffer,
    mimetype="application/pdf",
    headers={"Content-Disposition": "inline; filename=presupuesto_examenes.pdf"},
)


@app.route("/autolab")
def autolab():
    return render_template("autolab.html")


@app.route("/aliados")
def aliados():
    return render_template("aliados.html")


if __name__ == "__main__":
    app.run(debug=True)
