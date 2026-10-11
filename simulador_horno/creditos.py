"""Créditos del proyecto.

Un único lugar para los créditos que muestra la aplicación (pantalla de
bienvenida y barra lateral). No los quites al reorganizar la interfaz.
"""

UNIVERSIDAD = "Universidad de Antioquia"
FACULTAD = "Facultad de Ingeniería"
PROGRAMA = "Ingeniería de Sistemas"
ASIGNATURA = "Métodos Numéricos"
AUTOR = "Omar Alberto Torres"
DOCENTE = "Yony Ceballos"
ANIO = 2026

TITULO = "Simulador virtual de horno con control PID"
DESCRIPCION = (
    f"Proyecto de la asignatura {ASIGNATURA}, requisito de grado del programa de "
    f"{PROGRAMA} de la {UNIVERSIDAD} ({ANIO})."
)

# (rol, nombre) en el orden en que se muestran
FICHA = (
    ("Autor", AUTOR),
    ("Docente", DOCENTE),
    ("Asignatura", ASIGNATURA),
    ("Programa", PROGRAMA),
    ("Institución", f"{UNIVERSIDAD} · {FACULTAD}"),
    ("Año", str(ANIO)),
)
