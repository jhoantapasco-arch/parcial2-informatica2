import io
import os
import re
import unicodedata

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import scipy.io as sio

class ArchivoCSV:
    def __init__(self, ruta):
        self.__ruta = ruta
        self.__tiempo = "Tiempo"
        self.__condicion = "Condición"
        self.__diferencias = []

        tabla = self.__leer(ruta)
        tabla = tabla.dropna(axis=1, how="all")      # quita columnas vacias (p. ej. ';' final)

        # Se aceptan varios nombres para la columna de tiempo y de condicion
        colTiempo = self.__buscarColumna(tabla, ["Tiempo", "time_ms", "time", "tiempo_ms"])
        colCond = self.__buscarColumna(tabla, ["Condición", "condition", "condicion"])
        if colTiempo is None:
            raise ValueError("El CSV no tiene una columna de tiempo (Tiempo / time_ms).")
        if colCond is None:
            raise ValueError("El CSV no tiene una columna de condicion (Condición / condition).")
        tabla = tabla.rename(columns={colTiempo: self.__tiempo, colCond: self.__condicion})

        # Columnas numericas que vengan como texto (coma decimal)
        for c in tabla.columns:
            if c != self.__condicion and not pd.api.types.is_numeric_dtype(tabla[c]):
                conv = pd.to_numeric(tabla[c].astype(str).str.replace(",", ".", regex=False),
                                     errors="coerce")
                if conv.notna().mean() > 0.9:
                    tabla[c] = conv

        # El tiempo pasa a ser el indice de las filas
        self.__tabla = tabla.set_index(self.__tiempo)
        self.__columnas = self.__tabla.columns

    def __leer(self, ruta):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                tabla = pd.read_csv(ruta, sep=";", encoding=enc)
                if tabla.shape[1] == 1:               # separador distinto de ';'
                    tabla = pd.read_csv(ruta, sep=None, engine="python", encoding=enc)
                tabla.columns = [str(c).strip() for c in tabla.columns]
                return tabla
            except UnicodeDecodeError:
                continue
        raise ValueError("No se pudo leer el archivo (codificacion desconocida).")

    def __buscarColumna(self, tabla, nombres):
        def limpiar(t):
            t = unicodedata.normalize("NFD", str(t))
            t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
            return t.strip().lower()

        buscados = [limpiar(n) for n in nombres]
        for c in tabla.columns:
            if limpiar(c) in buscados:
                return c
        return None

    # ---------- informacion ----------
    def __str__(self):
        buffer = io.StringIO()
        self.__tabla.info(buf=buffer)                 # info() escribe en el buffer
        return ("\n===== INFORMACION DEL ARCHIVO CSV =====\n"
                "Archivo: {}\n"
                "{}\n"
                "===== ESTADISTICOS (describe) =====\n"
                "{}\n\n"
                "Condiciones: {}\n"
                "Canales disponibles: {}".format(
                    self.__ruta,
                    buffer.getvalue(),
                    self.__tabla.describe().to_string(),
                    self.verCondiciones(),
                    self.verCanales()))

    def verTabla(self):
        return self.__tabla

    def verCol(self):
        return self.__tabla.columns

    def verCondiciones(self):
        return self.__tabla[self.__condicion].unique().tolist()

    def verCanales(self):
        """Columnas numericas (canales y diferencias creadas), sin la condicion."""
        noCanales = [self.__condicion.lower(), "subject", "sujeto", "paciente", "id"]
        canales = []
        for c in self.__tabla.columns:
            if str(c).strip().lower() in noCanales:
                continue
            if pd.api.types.is_numeric_dtype(self.__tabla[c]):
                canales.append(c)
        return canales

    # ---------- diferencia interhemisferica ----------
    def diferenciaInterhemisferica(self, canal1, canal2, nombre):
        nombre = str(nombre).strip()
        if nombre == "":
            raise ValueError("El nombre de la nueva columna no puede estar vacio.")
        if nombre == self.__condicion:
            raise ValueError("Ese nombre esta reservado para la condicion.")
        if nombre in self.__tabla.columns and nombre not in self.__diferencias:
            raise ValueError("Ya existe una columna del archivo con el nombre '{}'.".format(nombre))

        self.__tabla[nombre] = self.__tabla[canal1] - self.__tabla[canal2]
        if nombre not in self.__diferencias:
            self.__diferencias.append(nombre)
        return self.__tabla[nombre]

    def mostrarDiferencia(self, canal1, canal2, nombre):
        """Grafica la columna ya creada: una curva por condicion (promedio por instante)."""
        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

        for cond in self.verCondiciones():
            sub = self.__tabla[self.__tabla[self.__condicion] == cond][nombre]
            sub = sub.groupby(level=0).mean()         # si hay varios ensayos, promedia por tiempo
            ax.plot(sub.index, sub.values, label="Condición {}".format(cond))

        ax.axvline(0, color="k", linestyle="--", linewidth=1)
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_xlabel("Tiempo (ms)")
        ax.set_ylabel("Microvoltios (µV)")
        ax.set_title("Diferencia interhemisférica: {} - {}".format(canal1, canal2))
        ax.legend()
        plt.tight_layout()

        ruta = guardarFigura("CSV_diferencia_{}.png".format(nombreSeguro(nombre)))
        plt.show()
        return ruta

    # ---------- stem + histograma + scatter ----------
    def graficarCondicion(self, condicion, canal, canal1, canal2):
        datos = self.__tabla[self.__tabla[self.__condicion] == condicion]

        fig = plt.figure(figsize=(11, 8))
        ax1 = fig.add_subplot(211)          # arriba, ancho completo
        ax2 = fig.add_subplot(223)          # abajo izquierda
        ax3 = fig.add_subplot(224)          # abajo derecha

        # a. Stem con linea vertical en t = 0 ms
        marcas, lineas, base = ax1.stem(datos.index, datos[canal], markerfmt=".", basefmt="k-")
        plt.setp(marcas, markersize=2)              # marcadores finos: hay miles de puntos
        plt.setp(lineas, linewidth=0.5)
        ax1.axvline(0, color="red", linestyle="--", label="t = 0 ms")
        ax1.set_xlabel("Tiempo (ms)")
        ax1.set_ylabel("Microvoltios (µV)")
        ax1.set_title("Stem - canal {} - condición {}".format(canal, condicion))
        ax1.legend()

        # b. Histograma del mismo canal
        ax2.hist(datos[canal], bins=20, edgecolor="black")
        ax2.set_xlabel("Microvoltios (µV)")
        ax2.set_ylabel("Frecuencia")
        ax2.set_title("Histograma - canal {}".format(canal))

        # c. Scatter de dos canales
        ax3.scatter(datos[canal1], datos[canal2], s=10)
        ax3.set_xlabel("{} (µV)".format(canal1))
        ax3.set_ylabel("{} (µV)".format(canal2))
        ax3.set_title("Scatter - {} vs {}".format(canal1, canal2))

        plt.tight_layout()

        ruta = guardarFigura("CSV_condicion_{}_{}.png".format(nombreSeguro(condicion),
                                                              nombreSeguro(canal)))
        plt.show()
        return ruta


class ArchivoMAT:
    def __init__(self, ruta):
        self.__ruta = ruta
        self.__datos = sio.loadmat(ruta)
        self.__variables = sio.whosmat(ruta)
        self.__llaves = list(self.__datos.keys())
        self.__matriz = None
        self.__nombreVar = None

    def __str__(self):
        ancho = max([len(v[0]) for v in self.__variables] + [8])
        linea = "-" * (ancho + 44)
        texto = "\n===== VARIABLES DEL ARCHIVO MAT =====\n"
        texto += "Archivo: {}\n".format(self.__ruta)
        texto += linea + "\n"
        texto += "{:<4}{:<{w}}  {:<18}{}\n".format("N°", "Variable", "Dimensiones", "Tipo", w=ancho)
        texto += linea + "\n"
        for i, v in enumerate(self.__variables):
            texto += "{:<4}{:<{w}}  {:<18}{}\n".format(i, v[0], str(v[1]), v[2], w=ancho)
        texto += linea + "\n"
        texto += "Llaves del diccionario: {}".format(self.__llaves)
        return texto

    def verLlaves(self):
        return self.__llaves

    def verVariables(self):
        return self.__variables

    def cargarMatriz(self, numero):
        nombre = self.__variables[numero][0]
        matriz = self.__datos[nombre]
        if not isinstance(matriz, np.ndarray) or not np.issubdtype(matriz.dtype, np.number):
            raise ValueError("La variable '{}' no es una matriz numerica.".format(nombre))
        self.__matriz = matriz
        self.__nombreVar = nombre
        return self.__matriz

    def verMatriz(self):
        return self.__matriz

    def verNombreVariable(self):
        return self.__nombreVar

    def convertir2D(self):
        """Devuelve la matriz como (canales, puntos*ensayos). No modifica la original."""
        if self.__matriz is None:
            raise ValueError("Primero debe cargar una variable.")
        if self.__matriz.ndim == 3:
            canales, puntos, ensayos = self.__matriz.shape
            return np.reshape(self.__matriz, (canales, puntos * ensayos), order="F")
        if self.__matriz.ndim == 1:
            return self.__matriz.reshape(1, -1)
        return self.__matriz

    def operarCanales(self, funcion, canales, pmin, pmax, nombre):
        matriz = self.convertir2D()
        nCanales, nPuntos = matriz.shape

        if len(canales) != 4:
            raise ValueError("Se requieren exactamente 4 canales.")
        for c in canales:
            if c < 0 or c >= nCanales:
                raise ValueError("El canal {} no existe (0 a {}).".format(c, nCanales - 1))
        if pmin < 0 or pmax > nPuntos or pmin >= pmax:
            raise ValueError("Rango de puntos invalido (0 a {}).".format(nPuntos))

        c1, c2, c3, c4 = canales
        datos1 = matriz[c1, pmin:pmax]
        datos2 = matriz[c2, pmin:pmax]
        datos3 = matriz[c3, pmin:pmax]
        datos4 = matriz[c4, pmin:pmax]

        resultado = funcion(datos1, datos2, datos3, datos4)
        tiempo = np.arange(pmin, pmax) / FS           # segundos

        # La multiplicacion de 4 señales en uV tiene unidades de uV^4
        if funcion.__name__ == "multiplicacion":
            unidad = r"Microvoltios a la cuarta ($\mu V^4$)"
        else:
            unidad = r"Microvoltios ($\mu V$)"

        fig = plt.figure(figsize=(10, 8))
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)

        ax1.plot(tiempo, datos1, label="Canal {}".format(c1))
        ax1.plot(tiempo, datos2, label="Canal {}".format(c2))
        ax1.plot(tiempo, datos3, label="Canal {}".format(c3))
        ax1.plot(tiempo, datos4, label="Canal {}".format(c4))
        ax1.set_xlabel("Tiempo (s)")
        ax1.set_ylabel(r"Microvoltios ($\mu V$)")
        ax1.set_title("Canales seleccionados")
        ax1.legend()

        ax2.plot(tiempo, resultado, color="tab:red", label=nombre)
        ax2.set_xlabel("Tiempo (s)")
        ax2.set_ylabel(unidad)
        ax2.set_title("Resultado: {} de los canales {}, {}, {} y {}".format(nombre, c1, c2, c3, c4))
        ax2.legend()

        plt.tight_layout()

        ruta = guardarFigura("MAT_operacion_{}.png".format(nombreSeguro(nombre)))
        plt.show()
        return ruta

    def estadisticos3D(self, eje1, eje2):
        if self.__matriz is None:
            raise ValueError("Primero debe cargar una variable.")
        if self.__matriz.ndim != 3:
            raise ValueError("La matriz debe estar en 3D para realizar este proceso.")
        if eje1 == eje2:
            raise ValueError("Los ejes deben ser diferentes.")

        # Se trabaja sobre la matriz 3D original, sin modificarla
        promedio = np.mean(self.__matriz, axis=(eje1, eje2))
        desviacion = np.std(self.__matriz, axis=(eje1, eje2))

        print("Forma final del promedio: {}".format(promedio.shape))
        print("Forma final de la desviacion: {}".format(desviacion.shape))

        tabla = pd.DataFrame({"Promedio": promedio, "Desviación estándar": desviacion})

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        tabla.boxplot(ax=ax)
        ax.set_xlabel("Estadístico")
        ax.set_ylabel("Microvoltios (µV)")
        ax.set_title("Promedio y desviación estándar a lo largo de los ejes {} y {}".format(eje1, eje2))
        plt.tight_layout()

        ruta = guardarFigura("MAT_boxplot_ejes_{}_{}.png".format(eje1, eje2))
        plt.show()
        return promedio, desviacion, ruta


class Sistema:
    def __init__(self):
        self.__archivos = {}

    def ingresarArchivo(self, nombre, archivo):
        self.__archivos[nombre] = archivo

    def verArchivo(self, nombre):
        return self.__archivos.get(nombre, None)

    def verArchivos(self):
        return self.__archivos

    def buscarPorTipo(self, tipo):
        """Devuelve los nombres de los archivos que son de la clase indicada."""
        return [n for n, a in self.__archivos.items() if isinstance(a, tipo)]

plt.ion()

FS = 250                    # frecuencia de muestreo de los .mat (muestras/s)
CARPETA = "graficos"        # carpeta donde se guardan las imagenes



def validarEntero(t):
    while True:
        try:
            return int(t)
        except (ValueError, TypeError):
            t = input("Ingrese un numero entero: ")


def validarRango(t, minimo, maximo):
    t = validarEntero(t)
    while t < minimo or t > maximo:
        t = validarEntero(input("Ingrese un valor entre {} y {}: ".format(minimo, maximo)))
    return t


def suma(a, b, c, d):
    return a + b + c + d


def resta(a, b, c, d):
    return a - b - c - d


def multiplicacion(a, b, c, d):
    return a * b * c * d


def nombreSeguro(texto):
    """Deja solo letras, numeros, guion y guion bajo para usar en nombres de archivo."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(texto)).strip("_")


def guardarFigura(nombre):
    """Guarda la figura activa (png) dentro de CARPETA y devuelve la ruta."""
    os.makedirs(CARPETA, exist_ok=True)
    ruta = os.path.join(CARPETA, nombre)
    plt.savefig(ruta, dpi=150)
    return ruta


