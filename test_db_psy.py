from db import conectar

conexion = conectar ()

if conexion:
    print(" CONECTADO EXISTOSAMENTE")

else:
    print(" NO SE PUDO CONECTAR, REVISA LA CONEXION")