from clases import *
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import scipy.io as sio


def limpiarRuta(ruta):
    """Quita espacios y comillas (al copiar la ruta en Windows suele traer comillas)."""
    return ruta.strip().strip('"').strip("'")


def pedirArchivo(sis, tipo, etiqueta):
    """Pide el nombre de un archivo cargado y verifica que exista y sea del tipo correcto."""
    if len(sis.buscarPorTipo(tipo)) == 0:
        print("No hay archivos {} cargados. Use la opcion 1.".format(etiqueta))
        return None

    print("Archivos {} cargados: {}".format(etiqueta, sis.buscarPorTipo(tipo)))
    nombre = input("Ingrese el nombre del archivo {}: ".format(etiqueta)).strip()
    archivo = sis.verArchivo(nombre)

    if archivo is None:
        print("Archivo no encontrado.")
        return None
    if not isinstance(archivo, tipo):
        print("Ese archivo no es de tipo {}.".format(etiqueta))
        return None
    return archivo


def elegirDeLista(lista, mensaje):
    """Muestra una lista numerada y devuelve el elemento elegido por el usuario."""
    for i in range(len(lista)):
        print("{}- {}".format(i, lista[i]))
    return lista[validarRango(input(mensaje), 0, len(lista) - 1)]


def main():
    sis = Sistema()

    while True:
        menu = validarRango(input(
            "\n\t>>>>> MENU PPAL <<<<<\n"
            "1- Ingresar archivo\n"
            "2- Ver informacion CSV\n"
            "3- Graficar CSV por condicion\n"
            "4- Diferencia interhemisferica CSV\n"
            "5- Ver informacion y cargar variable MAT\n"
            "6- Operar 4 canales MAT\n"
            "7- Estadisticos matriz 3D MAT\n"
            "8- Ver archivos cargados\n"
            "9- Salir\n"
            "--> "), 1, 9)
   # ------------------------------------------------------------
        if menu == 1:
            tipArch = validarRango(input(
                "\nIndique el tipo de archivo:\n"
                "1- Archivo .mat\n"
                "2- Archivo .csv\n"
                "--> "), 1, 2)

            ruta = limpiarRuta(input("Ruta del archivo: "))

            if not os.path.isfile(ruta):
                print("La ruta no existe.")
                continue

            try:
                if tipArch == 1:
                    archivo = ArchivoMAT(ruta)
                else:
                    archivo = ArchivoCSV(ruta)
            except Exception as error:
                print("No se pudo cargar el archivo: {}".format(error))
                continue

            nombre = input("Ingrese un nombre para identificar el archivo: ").strip()
            while nombre == "":
                nombre = input("El nombre no puede estar vacio: ").strip()

            if sis.verArchivo(nombre) is not None:
                print("Ya existia un archivo con ese nombre; fue reemplazado.")

            sis.ingresarArchivo(nombre, archivo)
            print("Archivo cargado correctamente.")

        # ------------------------------------------------------------
        elif menu == 2:
            archivo = pedirArchivo(sis, ArchivoCSV, "CSV")
            if archivo is not None:
                print(archivo)

        # ------------------------------------------------------------
        elif menu == 3:
            archivo = pedirArchivo(sis, ArchivoCSV, "CSV")
            if archivo is not None:
                print("\nCondiciones disponibles:")
                condicion = elegirDeLista(archivo.verCondiciones(),
                                          "Seleccione la condicion: ")

                canales = archivo.verCanales()
                if len(canales) == 0:
                    print("El archivo no tiene canales numericos.")
                    continue
                print("\nCanales disponibles:")
                canal = elegirDeLista(canales, "Seleccione el canal para stem e histograma: ")
                canal1 = elegirDeLista(canales, "Seleccione el primer canal para scatter: ")
                canal2 = elegirDeLista(canales, "Seleccione el segundo canal para scatter: ")

                try:
                    ruta = archivo.graficarCondicion(condicion, canal, canal1, canal2)
                    print("Grafico guardado en: {}".format(ruta))
                except Exception as error:
                    print("No se pudo graficar: {}".format(error))

 # ------------------------------------------------------------
        elif menu == 4:
            archivo = pedirArchivo(sis, ArchivoCSV, "CSV")
            if archivo is not None:
                canales = archivo.verCanales()
                if len(canales) < 2:
                    print("El archivo no tiene suficientes canales numericos.")
                    continue
                print("\nCanales disponibles:")
                canal1 = elegirDeLista(canales, "Seleccione el primer canal: ")
                canal2 = elegirDeLista(canales, "Seleccione el segundo canal: ")

                if canal1 == canal2:
                    print("Debe elegir dos canales diferentes.")
                    continue

                nombreNueva = input("Nombre de la nueva columna: ")

                try:
                    archivo.diferenciaInterhemisferica(canal1, canal2, nombreNueva)
                    print("\nResultado de la diferencia:")
                    print(archivo.verTabla()[nombreNueva.strip()])
                    ruta = archivo.mostrarDiferencia(canal1, canal2, nombreNueva.strip())
                    print("Grafico guardado en: {}".format(ruta))
                except Exception as error:
                    print("No se pudo calcular la diferencia: {}".format(error))

  # ------------------------------------------------------------
        elif menu == 5:
            archivo = pedirArchivo(sis, ArchivoMAT, "MAT")
            if archivo is not None:
                print(archivo)

                variables = archivo.verVariables()
                if len(variables) == 0:
                    print("El archivo no contiene variables.")
                    continue

                numero = validarRango(input("\nSeleccione el numero de la variable a cargar: "),
                                      0, len(variables) - 1)
                try:
                    matriz = archivo.cargarMatriz(numero)
                    print("\nMatriz cargada: {}".format(archivo.verNombreVariable()))
                    print("Forma: {}".format(matriz.shape))
                    print("Dimension: {}".format(matriz.ndim))
                except Exception as error:
                    print("No se pudo cargar la variable: {}".format(error))

        # ------------------------------------------------------------
        elif menu == 6:
            archivo = pedirArchivo(sis, ArchivoMAT, "MAT")
            if archivo is not None:
                matriz = archivo.verMatriz()

                if matriz is None:
                    print("Primero debe cargar una variable desde la opcion 5.")
                    continue

                matriz2D = archivo.convertir2D()          # (canales, puntos totales)
                canales, puntosTotales = matriz2D.shape

                print("\nNumero de canales disponibles: {} (0 a {})".format(canales, canales - 1))
                print("Puntos totales (2D): {}".format(puntosTotales))

                c1 = validarRango(input("Canal 1: "), 0, canales - 1)
                c2 = validarRango(input("Canal 2: "), 0, canales - 1)
                c3 = validarRango(input("Canal 3: "), 0, canales - 1)
                c4 = validarRango(input("Canal 4: "), 0, canales - 1)

                pmin = validarRango(input("Punto minimo: "), 0, puntosTotales - 1)
                pmax = validarRango(input("Punto maximo: "), pmin + 1, puntosTotales)

                print("\nOperacion:\n1- Suma\n2- Resta\n3- Multiplicacion")
                op = validarRango(input("--> "), 1, 3)

                if op == 1:
                    funcion, nombreOp = suma, "Suma"
                elif op == 2:
                    funcion, nombreOp = resta, "Resta"
                else:
                    funcion, nombreOp = multiplicacion, "Multiplicacion"

                try:
                    ruta = archivo.operarCanales(funcion, [c1, c2, c3, c4], pmin, pmax, nombreOp)
                    print("Grafico guardado en: {}".format(ruta))
                except Exception as error:
                    print("No se pudo realizar la operacion: {}".format(error))

 # ------------------------------------------------------------
        elif menu == 7:
            archivo = pedirArchivo(sis, ArchivoMAT, "MAT")
            if archivo is not None:
                matriz = archivo.verMatriz()

                if matriz is None:
                    print("Primero debe cargar una variable desde la opcion 5.")
                elif matriz.ndim != 3:
                    print("La variable cargada no es una matriz 3D.")
                else:
                    print("Forma de la matriz: {}".format(matriz.shape))
                    print("Ejes disponibles: 0 (canales), 1 (puntos), 2 (ensayos)")

                    eje1 = validarRango(input("Primer eje: "), 0, 2)
                    eje2 = validarRango(input("Segundo eje: "), 0, 2)
                    while eje1 == eje2:
                        eje2 = validarRango(
                            input("Los ejes deben ser diferentes. Segundo eje: "), 0, 2)

                    try:
                        promedio, desviacion, ruta = archivo.estadisticos3D(eje1, eje2)
                        print("Grafico guardado en: {}".format(ruta))
                    except Exception as error:
                        print("No se pudo calcular: {}".format(error))

        # ------------------------------------------------------------
        elif menu == 8:
            print("\n===== ARCHIVOS CARGADOS =====")
            archivos = sis.verArchivos()

            if len(archivos) == 0:
                print("No hay archivos cargados.")
            else:
                for nombre in archivos:
                    tipo = "CSV" if isinstance(archivos[nombre], ArchivoCSV) else "MAT"
                    print("-> {} ({})".format(nombre, tipo))

        # ------------------------------------------------------------
        elif menu == 9:
            print("Hasta luego.")
            break


if __name__ == "__main__":
    main()
    