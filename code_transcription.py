# code_transcription.py

import os
import re
import argparse
from typing import List, Optional, Pattern


def contains_only_comments_or_blank(text: str, comment_prefix: str = '#') -> bool:
    """
    Verifica si el texto está vacío o solo contiene comentarios y líneas en blanco.

    Args:
        text (str): Contenido del archivo.
        comment_prefix (str, optional): Prefijo que indica un comentario. Defaults to '#'.

    Returns:
        bool: True si cumple la condición, False de lo contrario.
    """
    for line in text.splitlines():
        stripped_line = line.strip()
        if stripped_line and not stripped_line.startswith(comment_prefix):
            return False
    return True


def es_test(nombre_archivo: str) -> bool:
    """
    Determina si un archivo es un archivo de test según su nombre.

    Args:
        nombre_archivo (str): Nombre del archivo.

    Returns:
        bool: True si es un archivo de test, False de lo contrario.
    """
    test_patterns = [
        re.compile(r'^test_.*\.py$'),
        re.compile(r'^tests_.*\.py$'),
        re.compile(r'.*_test\.py$'),
        re.compile(r'.*_tests\.py$')
    ]
    return any(pattern.match(nombre_archivo) for pattern in test_patterns)


def determine_file_inclusion(
    modo: str,
    nombre_archivo: str,
    include_patterns: Optional[List[Pattern]] = None,
    exclude_patterns: Optional[List[Pattern]] = None
) -> bool:
    """
    Determina si se incluye el archivo según el modo y patrones de inclusión/exclusión.

    Args:
        modo (str): Modo de inclusión ('solo_modulos', 'solo_tests', 'todo').
        nombre_archivo (str): Nombre del archivo.
        include_patterns (Optional[List[Pattern]], optional): Patrones para incluir archivos. Defaults to None.
        exclude_patterns (Optional[List[Pattern]], optional): Patrones para excluir archivos. Defaults to None.

    Returns:
        bool: True si se debe incluir el archivo, False de lo contrario.
    """
    incluir = True

    if include_patterns:
        incluir = any(pattern.search(nombre_archivo) for pattern in include_patterns)
    if exclude_patterns:
        if any(pattern.search(nombre_archivo) for pattern in exclude_patterns):
            incluir = False

    es_test_archivo = es_test(nombre_archivo)

    if modo == 'solo_modulos':
        incluir = incluir and not es_test_archivo
    elif modo == 'solo_tests':
        incluir = incluir and es_test_archivo
    elif modo == 'todo':
        pass  # Mantiene el valor de 'incluir' basado en patrones
    else:
        incluir = False

    return incluir


def list_functions(ruta_archivo: str) -> List[str]:
    """
    Extrae los nombres de las funciones definidas en un archivo Python.

    Args:
        ruta_archivo (str): Ruta del archivo Python.

    Returns:
        List[str]: Lista de nombres de funciones con su firma.
    """
    import ast

    funciones = []
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = f.read()

        tree = ast.parse(contenido)
        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.FunctionDef):
                parametros = [arg.arg for arg in nodo.args.args]
                firma = f"{nodo.name}({', '.join(parametros)})"
                funciones.append(firma)
    except Exception as e:
        print(f"Error al procesar {ruta_archivo}: {e}")
    return funciones


def list_classes(ruta_archivo: str) -> List[str]:
    """
    Extrae los nombres de las clases definidas en un archivo Python.

    Args:
        ruta_archivo (str): Ruta del archivo Python.

    Returns:
        List[str]: Lista de nombres de clases.
    """
    import ast

    clases = []
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = f.read()

        tree = ast.parse(contenido)
        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.ClassDef):
                clases.append(nodo.name)
    except Exception as e:
        print(f"Error al procesar {ruta_archivo}: {e}")
    return clases


class CodeTranscription:
    """
    Clase para generar transcripciones de archivos de código según configuraciones específicas.
    """

    def __init__(
        self,
        ruta_carpetas: str,
        modo: str = 'todo',
        extensiones: Optional[List[str]] = None,
        patrones_incluir: Optional[List[str]] = None,
        patrones_excluir: Optional[List[str]] = None,
        mostrar_clases: bool = False
    ):
        """
        Inicializa la instancia de CodeTranscription.

        Args:
            ruta_carpetas (str): Ruta de las carpetas a procesar.
            modo (str, optional): Modo de inclusión de archivos. Defaults to 'todo'.
            extensiones (Optional[List[str]], optional): Lista de extensiones de archivos a incluir. Defaults to ['.py'].
            patrones_incluir (Optional[List[str]], optional): Lista de patrones regex para incluir archivos. Defaults to None.
            patrones_excluir (Optional[List[str]], optional): Lista de patrones regex para excluir archivos. Defaults to None.
            mostrar_clases (bool, optional): Indica si se deben extraer y mostrar clases. Defaults to False.
        """
        self.ruta_carpetas = ruta_carpetas
        self.modo = modo
        self.extensiones = extensiones if extensiones else ['.py']
        self.patrones_incluir = [re.compile(pat) for pat in patrones_incluir] if patrones_incluir else None
        self.patrones_excluir = [re.compile(pat) for pat in patrones_excluir] if patrones_excluir else None
        self.mostrar_clases = mostrar_clases

    def transcribe(self, archivo_salida: str) -> None:
        """
        Genera la transcripción de los archivos según la configuración y la guarda en el archivo de salida.

        Args:
            archivo_salida (str): Ruta del archivo donde se guardará la transcripción.
        """
        try:
            with open(archivo_salida, "w", encoding="utf-8") as salida:
                salida.write("CODIGO:\n\n")
                contador_modulos = 1
                for root, dirs, files in os.walk(self.ruta_carpetas):
                    for file in files:
                        if any(file.endswith(ext) for ext in self.extensiones) and file != "__init__.py":
                            if determine_file_inclusion(
                                self.modo,
                                file,
                                include_patterns=self.patrones_incluir,
                                exclude_patterns=self.patrones_excluir
                            ):
                                ruta_completa = os.path.join(root, file)
                                try:
                                    with open(ruta_completa, "r", encoding="utf-8") as f:
                                        contenido = f.read()

                                    if contains_only_comments_or_blank(contenido):
                                        continue

                                    salida.write("-" * 200 + "\n\n")
                                    ruta_relativa = os.path.relpath(ruta_completa, self.ruta_carpetas)
                                    salida.write(f"[ARCHIVO {contador_modulos}] - {ruta_relativa}\n\n")
                                    salida.write(contenido + "\n\n")

                                    if self.mostrar_clases:
                                        clases = list_classes(ruta_completa)
                                        if clases:
                                            salida.write("CLASES:\n")
                                            for cls in clases:
                                                salida.write(f" - {cls}\n")
                                            salida.write("\n")

                                    contador_modulos += 1
                                except Exception as e:
                                    print(f"Error al procesar el archivo {ruta_completa}: {e}")
        except Exception as e:
            print(f"Error al escribir en el archivo de salida {archivo_salida}: {e}")


def parse_arguments():
    """
    Analiza los argumentos de la línea de comandos.

    Returns:
        argparse.Namespace: Objeto con los argumentos analizados.
    """
    parser = argparse.ArgumentParser(description="Genera transcripciones de archivos de código.")
    parser.add_argument('--ruta_carpetas', type=str, required=True, help='Ruta de las carpetas a procesar.')
    parser.add_argument('--modo', type=str, choices=['solo_modulos', 'solo_tests', 'todo'], default='todo',
                        help='Modo de inclusión de archivos.')
    parser.add_argument('--archivo_salida', type=str, required=True, help='Archivo de salida para la transcripción.')
    parser.add_argument('--extensiones', type=str, nargs='*', default=['.py'],
                        help='Extensiones de archivo a incluir (ej. .py .js).')
    parser.add_argument('--patrones_incluir', type=str, nargs='*', default=None,
                        help='Patrones regex para incluir archivos.')
    parser.add_argument('--patrones_excluir', type=str, nargs='*', default=None,
                        help='Patrones regex para excluir archivos.')
    parser.add_argument('--mostrar_clases', action='store_true',
                        help='Indica si se deben extraer y mostrar clases.')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    transcription = CodeTranscription(
        ruta_carpetas=args.ruta_carpetas,
        modo=args.modo,
        extensiones=args.extensiones,
        patrones_incluir=args.patrones_incluir,
        patrones_excluir=args.patrones_excluir,
        mostrar_clases=args.mostrar_clases
    )
    transcription.transcribe(args.archivo_salida)
    print(f"Transcripción completada. Archivo guardado en {args.archivo_salida}")
