'''
Proyecto Final - Programacion para Extraccion de Datos
integrantes:
    -- De La Cruz Ramirez Jeremy Yael
    -- Ramirez Cardenas Luis Armando
Grupo: 951
Fecha:
Profesor: Josue Miguel Flores Parra
'''

import logging
import os
import sys
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import mysql.connector
from sqlalchemy import create_engine
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy.exc import OperationalError
from mysql.connector import Error
from tkinter import *
from tkinter import simpledialog, messagebox
root = Tk()
root.withdraw()

# ----------- Aquí van tus funciones originales sin modificar -----------

def extraccion():
    messagebox.showinfo("Entrando a pagina IMDB", "Favor de esperar 8)")
    driver = ChromeDriverManager().install()
    s = Service(driver)
    opc = Options()
    opc.add_argument("--window-size=1020,1200")
    navegador = webdriver.Chrome(options=opc, service=s)
    navegador.get("https://www.imdb.com/es-es/")
    wait = WebDriverWait(navegador, 10)
    time.sleep(15)

    menu_btn = navegador.find_element(By.CSS_SELECTOR, "label[aria-label='Abrir panel de navegación']")
    menu_btn.click()
    time.sleep(5)

    menu_peliculas = navegador.find_element(By.CSS_SELECTOR, "label[aria-label='Desplegar enlaces de navegación de Películas']")
    menu_peliculas.click()
    time.sleep(2)

    mejores_250_btn = navegador.find_element(By.LINK_TEXT, "Las 250 películas mejor valoradas")
    mejores_250_btn.click()
    time.sleep(5)

    movies_data = {"name_movie": [], "year_movie": [],
                   "score_movie": [], "time_movie": []}

    soup = BeautifulSoup(navegador.page_source, "html.parser")
    datos_paginas = soup.find_all("div", attrs={"class": "sc-4b408797-0 eFrxXF cli-children"})
    if datos_paginas:
        for item in datos_paginas:
            nombre = item.find("h3", attrs={"class": "ipc-title__text"})
            if nombre:
                movies_data["name_movie"].append(f"Pelicula: [{nombre.text.strip()}]")
            else:
                movies_data["name_movie"].append("Nombre de la película no encontrado")

            metadatos = item.find_all("span", attrs={"class": "sc-4b408797-8 iurwGb cli-title-metadata-item"})
            if len(metadatos) >= 1:
                movies_data["year_movie"].append(f"Año: {metadatos[0].text.strip()}")
            else:
                movies_data["year_movie"].append("Año no encontrado")

            if len(metadatos) >= 2:
                movies_data["time_movie"].append(f"Tiempo: {metadatos[1].text.strip()}")
            else:
                movies_data["time_movie"].append("Tiempo no encontrado")

            puntuacion = item.find("span", attrs={"class": "ipc-rating-star--rating"})
            if puntuacion:
                movies_data["score_movie"].append(f"Puntaje: {puntuacion.text.strip()}")
            else:
                movies_data["score_movie"].append("No se encontró puntuación")
    time.sleep(3)
    navegador.close()
    print(movies_data)

    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    nombre_carpeta = "Extraccion de datos"
    ruta_carpeta = os.path.join(ruta_actual, nombre_carpeta)
    os.makedirs(ruta_carpeta, exist_ok=True)
    print(f"Carpeta creada en: {ruta_carpeta}")
    df = pd.DataFrame(movies_data)
    print(df.sample(5))
    df.to_csv("Extraccion de datos/movies.csv")


def migrar_a_mysql():
    import pandas as pd
    from sqlalchemy import create_engine
    import mysql.connector
    import re


    def convertir_duracion(duracion):
        """Convierte texto como '2h 22min' en minutos (int)"""
        try:
            duracion = duracion.lower()
            total = 0
            horas = re.search(r"(\d+)h", duracion)
            minutos = re.search(r"(\d+)(?:min|m)", duracion)
            if horas:
                total += int(horas.group(1)) * 60
            if minutos:
                total += int(minutos.group(1))
            return total
        except:
            return None

    # Pedir contraseña hasta que sea válida o se cancele
    while True:
        contraseña = simpledialog.askstring("Conexión a MySQL",
                                            "Favor de ingresar la contraseña de su aplicación MySQL (Workbench)")
        if contraseña is None:
            messagebox.showwarning("Cancelado", "Operación cancelada por el usuario.")
            break

        try:
            # Verificar conexión con mysql.connector
            conexion_mysql = mysql.connector.connect(
                host="localhost",
                port=3306,
                user="root",
                password=contraseña
            )
            cursor = conexion_mysql.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS Extraccion_de_datos_Movies;")
            cursor.close()
            conexion_mysql.close()
            break  # Salir del ciclo si fue exitoso
        except Error:
            messagebox.showerror("Error de conexión",
                                 "❌ Contraseña incorrecta o fallo de conexión. Inténtalo de nuevo.")

    # Si se proporcionó una contraseña válida, continuar
    if contraseña:
        # Leer CSV original
        df = pd.read_csv("Extraccion de datos/movies.csv")

        # Eliminar columna extra si existe
        if 'Unnamed: 0' in df.columns:
            df.drop(columns=['Unnamed: 0'], inplace=True)

        # Limpiar columnas
        df["name_movie"] = df["name_movie"].str.replace(r"Pelicula: \[|\]", "", regex=True)
        df["year_movie"] = df["year_movie"].str.replace("Año: ", "", regex=False)
        df["time_movie"] = df["time_movie"].str.replace("Tiempo: ", "", regex=False)
        df["score_movie"] = df["score_movie"].str.replace("Puntaje: ", "", regex=False)

        df["year_movie"] = pd.to_numeric(df["year_movie"], errors="coerce")
        df["score_movie"] = pd.to_numeric(df["score_movie"].str.replace(",", "."), errors="coerce")
        df["time_movie"] = df["time_movie"].apply(convertir_duracion)

        # Eliminar filas con valores nulos
        df.dropna(inplace=True)

        # Conexión SQLAlchemy
        try:
            engine = create_engine(f"mysql+pymysql://root:{contraseña}@localhost:3306/Extraccion_de_datos_Movies")
            df.to_sql(name='data_movies', con=engine, if_exists='append', index=False)
            print("✅ Migración completada correctamente.")
        except OperationalError as e:
            messagebox.showerror("Error", f"❌ No se pudo migrar a MySQL: {e}")

def limpieza_de_los_datos():
    import pandas as pd

    ruta_csv_original = "Extraccion de datos/movies.csv"
    df = pd.read_csv(ruta_csv_original)

    print("Datos originales:")
    print(df.head())

    print("Columnas:", df.columns)

    # Extraer nombre de la película limpio
    df["name_movie"] = df["name_movie"].str.extract(r'Pelicula: \[\d+\. (.+)\]')

    # Reemplazamos valores "Desconocido" por NaN
    df["year_movie"] = df["year_movie"].replace("Desconocido", pd.NA)
    df["score_movie"] = df["score_movie"].replace("Desconocido", pd.NA)
    df["time_movie"] = df["time_movie"].replace("Desconocido", pd.NA)

    # Limpiamos etiquetas
    df["year_movie"] = df["year_movie"].str.replace("Año: ", "", regex=False)
    df["time_movie"] = df["time_movie"].str.replace("Tiempo: ", "", regex=False)
    df["score_movie"] = df["score_movie"].str.replace("Puntaje: ", "", regex=False)

    # Convertimos año y score a número
    df["year_movie"] = pd.to_numeric(df["year_movie"], errors="coerce")
    df["score_movie"] = pd.to_numeric(df["score_movie"].str.replace(',', '.'), errors="coerce")  # Reemplaza coma

    # Función para convertir "2h 30m" en minutos
    def convertir_duracion(duracion):
        try:
            duracion = duracion.lower()
            minutos = 0
            if "h" in duracion:
                partes = duracion.split("h")
                horas = int(partes[0].strip())
                minutos += horas * 60
                if len(partes) > 1 and ("min" in partes[1] or "m" in partes[1]):
                    mins_str = partes[1].strip().replace("min", "").replace("m", "").strip()
                    if mins_str.isdigit():
                        minutos += int(mins_str)
            elif "min" in duracion or "m" in duracion:
                mins_str = duracion.replace("min", "").replace("m", "").strip()
                if mins_str.isdigit():
                    minutos = int(mins_str)
            return minutos
        except Exception as e:
            print(f"Error al convertir duración: {duracion} -> {e}")
            return None

    df["time_movie"] = df["time_movie"].apply(convertir_duracion)

    print(f"Filas antes de limpiar NaNs: {len(df)}")
    df = df[df["year_movie"].notna()]
    df = df[df["score_movie"].notna()]
    df = df[df["time_movie"].notna()]
    print(f"Filas después de limpiar NaNs: {len(df)}")

    ruta_csv_limpio = "Extraccion de datos/movies_limpio.csv"
    df.to_csv(ruta_csv_limpio, index=False)

    print(f"Datos limpios guardados en: {ruta_csv_limpio}")
    print(df.head())

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
df_dashboard = None

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background": "linear-gradient(to bottom, #A9DFBF, #58D68D)",
    "color": "white",
    "boxShadow": "2px 0 5px rgba(0,0,0,0.1)",
    "textShadow": "1px 1px 2px rgba(0,0,0,0.3)"
}

CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 2rem",
    "backgroundColor": "white",
    "borderRadius": "12px",
    "boxShadow": "0 8px 24px rgba(0,0,0,0.1)",
    "minHeight": "100vh"
}

sidebar = html.Div(
    [
        html.H2("IMDb Movies", className="display-4", style={"color": "white", "textShadow": "2px 2px 4px rgba(0,0,0,0.5)"}),
        html.Hr(style={"borderColor": "rgba(255,255,255,0.3)"}),
        html.P("Proyecto final - Dashboard", className="lead", style={"color": "white", "textShadow": "1px 1px 2px rgba(0,0,0,0.3)"}),
        dbc.Nav(
            [
                dbc.NavLink("Hogar", href="/", active="exact", style={"color": "white"}),
                dbc.NavLink("Distribución Puntajes", href="/dash1", active="exact", style={"color": "white"}),
                dbc.NavLink("Puntaje vs Año", href="/dash2", active="exact", style={"color": "white"}),
                dbc.NavLink("Distribución Duración", href="/dash3", active="exact", style={"color": "white"}),
                dbc.NavLink("Datos Origen", href="https://www.imdb.com/es-es/", target="_blank", style={"color": "white"}),
                dbc.NavLink("Trabajo en Github", href="https://github.com/ArmandoRamirez951/Programacion_extraccion_datos", target="_blank", style={"color": "white"})
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)

def pagina_hogar():
    return html.Div(
        [  # Fondo completo de la página
            html.Div(
                [  # Contenido central en forma de tarjeta
                    html.H1(
                        "Proyecto Final - Programación para Extracción de Datos",
                        className="mb-4",
                        style={
                            "fontSize": "2.5rem",
                            "fontWeight": "bold",
                            "color": "#145A32",
                            "marginBottom": "1.5rem",
                            "textShadow": "1px 1px 2px #D5F5E3"
                        }
                    ),
                    html.H4(
                        "Integrantes:",
                        className="mb-2",
                        style={
                            "fontWeight": "bold",
                            "marginTop": "1rem",
                            "marginBottom": "0.5rem",
                            "color": "#1B4F72"
                        }
                    ),
                    html.Ul(
                        [
                            html.Li("De La Cruz Ramirez Jeremy Yael"),
                            html.Li("Ramirez Cardenas Luis Armando"),
                        ],
                        className="mb-4",
                        style={
                            "listStyleType": "none",
                            "padding": 0,
                            "marginBottom": "1.5rem",
                            "fontSize": "1.1rem",
                            "color": "#2C3E50"
                        }
                    ),
                    html.P("Grupo: 951", className="mb-2", style={"fontSize": "1rem", "marginBottom": "0.5rem", "color": "#2C3E50"}),
                    html.P("Fecha:", className="mb-2", style={"fontSize": "1rem", "marginBottom": "1rem", "color": "#2C3E50"}),
                    html.H5(
                        "Profesor: Josue Miguel Flores Parra",
                        className="mb-4",
                        style={"fontWeight": "bold", "color": "#1A5276", "marginBottom": "1.5rem"}
                    ),
                    html.Img(
                        src="https://comunicacioninstitucional.uabc.mx/wp-content/uploads/2024/03/escudo-actualizado-2022-w1000px-751x1024.png",
                        style={
                            "width": "200px",
                            "height": "auto",
                            "margin": "auto",
                            "display": "block",
                            "marginBottom": "1.5rem",
                            "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                            "borderRadius": "8px"
                        }
                    ),
                    html.P(
                        "Bienvenidos al proyecto final de programación para la extracción de datos. "
                        "Aquí analizamos y visualizamos datos con Dash.",
                        className="mt-4",
                        style={
                            "fontSize": "1.1rem",
                            "lineHeight": "1.6",
                            "marginTop": "1.5rem",
                            "color": "#333",
                            "padding": "0 1rem"
                        }
                    )
                ],
                style={  # Tarjeta de contenido
                    "textAlign": "center",
                    "padding": "2.5rem",
                    "maxWidth": "850px",
                    "margin": "auto",
                    "backgroundColor": "rgba(255, 255, 255, 0.95)",
                    "borderRadius": "18px",
                    "boxShadow": "0 8px 24px rgba(0, 0, 0, 0.2)"
                }
            )
        ],
        style={  # Estilo del fondo completo
            "backgroundImage": "linear-gradient(to right top, #A9DFBF, #82E0AA, #58D68D, #45B39D, #3498DB)",
            "minHeight": "100vh",
            "backgroundSize": "cover",
            "backgroundRepeat": "no-repeat",
            "padding": "4rem",
            "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
        }
    )

def menu_dashboards():
    return html.Div(
        [
            html.H3("Menú de Dashboards", style={"color": "#145A32", "marginBottom": "1rem"}),
            html.Ul(
                [
                    html.Li("Dashboard 1", style={"padding": "10px", "cursor": "pointer", "color": "#1A5276"}),
                    html.Li("Dashboard 2", style={"padding": "10px", "cursor": "pointer", "color": "#1A5276"}),
                    html.Li("Dashboard 3", style={"padding": "10px", "cursor": "pointer", "color": "#1A5276"}),
                ],
                style={
                    "listStyleType": "none",
                    "padding": 0,
                    "margin": 0,
                }
            )
        ],
        style={
            "backgroundColor": "rgba(255, 255, 255, 0.95)",
            "padding": "1.5rem",
            "borderRadius": "12px",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
            "maxWidth": "250px",
            "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
            "marginBottom": "2rem"
        }
    )


def pagina_dash1():
    global df_dashboard
    if df_dashboard is None or df_dashboard.empty:
        return html.Div(
            html.P(
                "⚠️ No hay datos cargados. Por favor extrae y limpia los datos primero.",
                style={
                    "color": "#B03A2E",
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "fontSize": "1.3rem",
                    "padding": "1.5rem"
                }
            ),
            style={
                "backgroundColor": "#FDEDEC",
                "margin": "3rem auto",
                "maxWidth": "800px",
                "borderRadius": "12px",
                "boxShadow": "0 4px 10px rgba(0, 0, 0, 0.1)"
            }
        )

    fig = px.histogram(df_dashboard, x='score_movie', nbins=20, title='Distribución de puntajes')
    debug_text = f"Datos para 'score_movie':\n{df_dashboard['score_movie'].head(10).to_string()}"

    return html.Div(
        [
            html.H2("Visualización de Datos", style={
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "fontSize": "2rem",
                "color": "#145A32",
                "textShadow": "1px 1px #D5F5E3"
            }),
            dcc.Graph(figure=fig, style={"marginBottom": "2rem"}),

            html.Div([
                html.H4("📌 Vista Preliminar de los Puntajes", style={
                    "marginBottom": "1rem",
                    "color": "#1A5276",
                    "fontWeight": "bold",
                    "textAlign": "left"
                }),
                html.Pre(
                    debug_text,
                    style={
                        "whiteSpace": "pre-wrap",
                        "backgroundColor": "#F4F6F7",
                        "padding": "1rem",
                        "borderLeft": "6px solid #117A65",
                        "fontSize": "0.95rem",
                        "borderRadius": "8px",
                        "color": "#333",
                        "overflowX": "auto"
                    }
                )
            ])
        ],
        style={
            "padding": "2.5rem",
            "maxWidth": "950px",
            "margin": "3rem auto",
            "background": "linear-gradient(to bottom right, #D5F5E3, #ABEBC6)",
            "borderRadius": "16px",
            "boxShadow": "0 6px 16px rgba(0, 0, 0, 0.15)",
            "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
        }
    )


def pagina_dash2():
    global df_dashboard
    if df_dashboard is None or df_dashboard.empty:
        return html.Div(
            html.P(
                "⚠️ No hay datos cargados. Por favor extrae y limpia los datos primero.",
                style={
                    "color": "#B03A2E",
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "fontSize": "1.3rem",
                    "padding": "1.5rem"
                }
            ),
            style={
                "backgroundColor": "#FDEDEC",
                "margin": "3rem auto",
                "maxWidth": "800px",
                "borderRadius": "12px",
                "boxShadow": "0 4px 10px rgba(0, 0, 0, 0.1)"
            }
        )

    fig = px.scatter(
        df_dashboard,
        x='year_movie',
        y='score_movie',
        title='Puntaje vs Año de la Película',
        labels={"year_movie": "Año", "score_movie": "Puntaje"},
        template='plotly_white'
    )

    debug_text = f"Datos para 'year_movie' y 'score_movie':\n{df_dashboard[['year_movie','score_movie']].head(10).to_string()}"

    return html.Div(
        [
            html.H2("Relación entre Año y Puntaje", style={
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "fontSize": "2rem",
                "color": "#145A32",
                "textShadow": "1px 1px #D5F5E3"
            }),
            dcc.Graph(figure=fig, style={"marginBottom": "2rem"}),

            html.Div([
                html.H4("📌 Datos de muestra (Año y Puntaje)", style={
                    "marginBottom": "1rem",
                    "color": "#1A5276",
                    "fontWeight": "bold",
                    "textAlign": "left"
                }),
                html.Pre(
                    debug_text,
                    style={
                        "whiteSpace": "pre-wrap",
                        "backgroundColor": "#F4F6F7",
                        "padding": "1rem",
                        "borderLeft": "6px solid #117A65",
                        "fontSize": "0.95rem",
                        "borderRadius": "8px",
                        "color": "#333",
                        "overflowX": "auto"
                    }
                )
            ])
        ],
        style={
            "padding": "2.5rem",
            "maxWidth": "950px",
            "margin": "3rem auto",
            "background": "linear-gradient(to bottom right, #D5F5E3, #ABEBC6)",
            "borderRadius": "16px",
            "boxShadow": "0 6px 16px rgba(0, 0, 0, 0.15)",
            "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
        }
    )


def pagina_dash3():
    global df_dashboard
    if df_dashboard is None or df_dashboard.empty:
        return html.Div(
            html.P(
                "⚠️ No hay datos cargados. Por favor extrae y limpia los datos primero.",
                style={
                    "color": "#B03A2E",
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "fontSize": "1.3rem",
                    "padding": "1.5rem"
                }
            ),
            style={
                "backgroundColor": "#FDEDEC",
                "margin": "3rem auto",
                "maxWidth": "800px",
                "borderRadius": "12px",
                "boxShadow": "0 4px 10px rgba(0, 0, 0, 0.1)"
            }
        )

    fig = px.histogram(
        df_dashboard,
        x='time_movie',
        nbins=20,
        title='Distribución de Duración (minutos)',
        labels={"time_movie": "Duración (minutos)"},
        template='plotly_white'
    )

    debug_text = f"Datos para 'time_movie':\n{df_dashboard['time_movie'].head(10).to_string()}"

    return html.Div(
        [
            html.H2("Distribución de la Duración de Películas", style={
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "fontSize": "2rem",
                "color": "#145A32",
                "textShadow": "1px 1px #D5F5E3"
            }),
            dcc.Graph(figure=fig, style={"marginBottom": "2rem"}),

            html.Div([
                html.H4("📌 Datos de muestra (Duración)", style={
                    "marginBottom": "1rem",
                    "color": "#1A5276",
                    "fontWeight": "bold",
                    "textAlign": "left"
                }),
                html.Pre(
                    debug_text,
                    style={
                        "whiteSpace": "pre-wrap",
                        "backgroundColor": "#F4F6F7",
                        "padding": "1rem",
                        "borderLeft": "6px solid #117A65",
                        "fontSize": "0.95rem",
                        "borderRadius": "8px",
                        "color": "#333",
                        "overflowX": "auto"
                    }
                )
            ])
        ],
        style={
            "padding": "2.5rem",
            "maxWidth": "950px",
            "margin": "3rem auto",
            "background": "linear-gradient(to bottom right, #D5F5E3, #ABEBC6)",
            "borderRadius": "16px",
            "boxShadow": "0 6px 16px rgba(0, 0, 0, 0.15)",
            "fontFamily": "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
        }
    )



@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page_content(pathname):
    if pathname == "/":
        return pagina_hogar()
    elif pathname == "/dash1":
        return pagina_dash1()
    elif pathname == "/dash2":
        return pagina_dash2()
    elif pathname == "/dash3":
        return pagina_dash3()
    return html.Div([
        html.H1("404: Not found", className="text-danger"),
        html.P(f"La página '{pathname}' no existe.")
    ])


def iniciar_dashboard():
    messagebox.showwarning("Regresar al Menu", "Cuando requiera volver al menu presional el boton stop del programa")
    global df_dashboard
    ruta_csv_limpio = "Extraccion de datos/movies_limpio.csv"
    df_dashboard = pd.read_csv(ruta_csv_limpio)
    print("\n>>> Primeras filas del DataFrame limpio:")
    print(df_dashboard.head())

    print("\n>>> Tipos de datos:")
    print(df_dashboard.dtypes)

    print("\n>>> Valores nulos en cada columna:")
    print(df_dashboard.isnull().sum())

    if os.path.isfile(ruta_csv_limpio):
        df_dashboard = pd.read_csv(ruta_csv_limpio)
    else:
        print("Archivo limpio no encontrado. Por favor limpia los datos primero.")
        return

    app.layout = html.Div([
        dcc.Location(id="url"),
        sidebar,
        content
    ])

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(debug=False)

# ----------- Menú -----------

def menu():
    opc = 0
    while (opc != 5):
        opc = simpledialog.askinteger(" Proyecto Final - Programacio para Extraccion de Datos ",
                                      "                             MENU                        \n"
                                      "1) Extraer datos de la pagina de IMDB "
                                      "\n2) Realizar limpieza de los datos extraidos "
                                      "\n3) Migrar los datos a MYSQL "
                                      "\n4) Abrir los dashboard "
                                      "\n5) Salir del programa")
        if opc == 1:
            extraccion()
        elif opc == 2:
            limpieza_de_los_datos()
        elif opc == 3:
            migrar_a_mysql()
        elif opc == 4:
            iniciar_dashboard()
            root.withdraw()
        elif opc == 5:
            messagebox.showinfo("SAlIENDO", "Gracias Vuelva Pronto")
            root.destroy()
        else:
            messagebox.showerror("Error", "Ingrese un numero valido")

if __name__ == "__main__":
    menu()

