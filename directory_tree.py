# directory_tree.py

import os
import re
import argparse
from typing import List, Optional, Pattern, Dict, Any
import ast


def list_functions(ruta_archivo: str) -> List[str]:
    """
    Extrae los nombres de las funciones definidas en un archivo Python.

    Args:
        ruta_archivo (str): Ruta del archivo Python.

    Returns:
        List[str]: Lista de nombres de funciones con su firma.
    """
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


class DirectoryTreeGenerator:
    """
    Clase para generar y mostrar un árbol de directorios con opciones configurables.
    """

    def __init__(
        self,
        ruta_inicial: str,
        extensiones: Optional[List[str]] = None,
        patrones_incluir: Optional[List[str]] = None,
        patrones_excluir: Optional[List[str]] = None,
        mostrar_funciones: bool = False,
        mostrar_clases: bool = False
    ):
        """
        Inicializa la instancia de DirectoryTreeGenerator.

        Args:
            ruta_inicial (str): Ruta del directorio inicial.
            extensiones (Optional[List[str]], optional): Lista de extensiones de archivo a incluir. Defaults to None.
            patrones_incluir (Optional[List[str]], optional): Lista de patrones regex para incluir archivos/carpas. Defaults to None.
            patrones_excluir (Optional[List[str]], optional): Lista de patrones regex para excluir archivos/carpas. Defaults to None.
            mostrar_funciones (bool, optional): Indica si se deben extraer y mostrar funciones de los archivos. Defaults to False.
            mostrar_clases (bool, optional): Indica si se deben extraer y mostrar clases de los archivos. Defaults to False.
        """
        self.ruta_inicial = os.path.abspath(ruta_inicial)
        self.extensiones = extensiones if extensiones else ['.py']
        self.patrones_incluir = [re.compile(pat) for pat in patrones_incluir] if patrones_incluir else None
        self.patrones_excluir = [re.compile(pat) for pat in patrones_excluir] if patrones_excluir else None
        self.mostrar_funciones = mostrar_funciones
        self.mostrar_clases = mostrar_clases

    def generate_structure(self) -> Dict[str, Any]:
        """
        Genera una estructura de árbol de directorios.

        Returns:
            Dict[str, Any]: Estructura anidada representando el árbol de directorios.
        """
        estructura = {}
        try:
            for root, dirs, files in os.walk(self.ruta_inicial):
                # Filtrar directorios según patrones de exclusión
                dirs[:] = [d for d in dirs if self.should_include(d)]

                path_relativa = os.path.relpath(root, self.ruta_inicial)
                if path_relativa == ".":
                    current_level = estructura
                else:
                    current_level = self.get_nested_dict(estructura, path_relativa.split(os.sep))

                for file in sorted(files):
                    if any(file.endswith(ext) for ext in self.extensiones) and file != "__init__.py":
                        if self.should_include(file):
                            ruta_completa = os.path.join(root, file)
                            file_info = {}
                            if self.mostrar_funciones or self.mostrar_clases:
                                if self.mostrar_funciones:
                                    funciones = list_functions(ruta_completa)
                                    if funciones:
                                        file_info['funciones'] = funciones
                                if self.mostrar_clases:
                                    clases = list_classes(ruta_completa)
                                    if clases:
                                        file_info['clases'] = clases
                            current_level[file] = file_info if file_info else None
                    else:
                        if self.should_include(file):
                            current_level[file] = None
        except Exception as e:
            print(f"Error al generar la estructura del directorio: {e}")
        return estructura

    def should_include(self, nombre: str) -> bool:
        """
        Determina si un archivo o carpeta debe ser incluido según los patrones.

        Args:
            nombre (str): Nombre del archivo o carpeta.

        Returns:
            bool: True si debe ser incluido, False de lo contrario.
        """
        incluir = True

        if self.patrones_incluir:
            incluir = any(pattern.search(nombre) for pattern in self.patrones_incluir)
        if self.patrones_excluir:
            if any(pattern.search(nombre) for pattern in self.patrones_excluir):
                incluir = False

        return incluir

    def get_nested_dict(self, dic: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """
        Accede o crea un diccionario anidado según una lista de claves.

        Args:
            dic (Dict[str, Any]): Diccionario base.
            keys (List[str]): Lista de claves.

        Returns:
            Dict[str, Any]: Diccionario anidado.
        """
        for key in keys:
            dic = dic.setdefault(key, {})
        return dic

    def display_tree(self, estructura: Optional[Dict[str, Any]] = None, prefix: str = "") -> None:
        """
        Muestra el árbol de directorios en la consola.

        Args:
            estructura (Optional[Dict[str, Any]], optional): Estructura del árbol. Defaults to None.
            prefix (str, optional): Prefijo para formatear el árbol. Defaults to "".
        """
        if estructura is None:
            estructura = self.generate_structure()

        def _display(subtree: Dict[str, Any], prefix: str) -> None:
            items = sorted(subtree.keys())
            for i, key in enumerate(items):
                es_ultimo = i == len(items) - 1
                connector = "└──" if es_ultimo else "├──"
                print(f"{prefix}{connector} {key}")
                nuevo_prefijo = f"{prefix}    " if es_ultimo else f"{prefix}│   "

                if isinstance(subtree[key], dict):
                    _display(subtree[key], nuevo_prefijo)
                elif isinstance(subtree[key], list):
                    for item in subtree[key]:
                        if 'def ' in item:
                            print(f"{nuevo_prefijo}├── {item}")
                        elif 'class ' in item:
                            print(f"{nuevo_prefijo}├── {item}")

        print(f"{self.ruta_inicial}/")
        _display(estructura, prefix="")

    def save_tree_to_file(self, archivo_salida: str, estructura: Optional[Dict[str, Any]] = None) -> None:
        """
        Guarda el árbol de directorios en un archivo de texto.

        Args:
            archivo_salida (str): Ruta del archivo de salida.
            estructura (Optional[Dict[str, Any]], optional): Estructura del árbol. Defaults to None.
        """
        if estructura is None:
            estructura = self.generate_structure()

        try:
            with open(archivo_salida, "w", encoding="utf-8") as f:
                f.write(f"{self.ruta_inicial}/\n")
                self._write_subtree(f, estructura, "")
            print(f"Árbol de directorios guardado en {archivo_salida}")
        except Exception as e:
            print(f"Error al escribir en el archivo {archivo_salida}: {e}")

    def _write_subtree(self, file_handle, subtree: Dict[str, Any], prefix: str) -> None:
        """
        Escribe recursivamente la estructura del árbol en el archivo.

        Args:
            file_handle: Manejador de archivo.
            subtree (Dict[str, Any]): Subárbol a escribir.
            prefix (str): Prefijo para formatear el árbol.
        """
        items = sorted(subtree.keys())
        for i, key in enumerate(items):
            es_ultimo = i == len(items) - 1
            connector = "└──" if es_ultimo else "├──"
            file_handle.write(f"{prefix}{connector} {key}\n")
            nuevo_prefijo = f"{prefix}    " if es_ultimo else f"{prefix}│   "

            if isinstance(subtree[key], dict):
                self._write_subtree(file_handle, subtree[key], nuevo_prefijo)
            elif isinstance(subtree[key], list):
                for item in subtree[key]:
                    if 'def ' in item:
                        file_handle.write(f"{nuevo_prefijo}├── {item}\n")
                    elif 'class ' in item:
                        file_handle.write(f"{nuevo_prefijo}├── {item}\n")


def parse_arguments():
    """
    Analiza los argumentos de la línea de comandos.

    Returns:
        argparse.Namespace: Objeto con los argumentos analizados.
    """
    parser = argparse.ArgumentParser(description="Genera y muestra un árbol de directorios.")
    parser.add_argument('--ruta_inicial', type=str, required=True, help='Ruta del directorio inicial.')
    parser.add_argument('--extensiones', type=str, nargs='*', default=['.py'],
                        help='Extensiones de archivo a incluir (ej. .py .js).')
    parser.add_argument('--patrones_incluir', type=str, nargs='*', default=None,
                        help='Patrones regex para incluir archivos/carpas.')
    parser.add_argument('--patrones_excluir', type=str, nargs='*', default=None,
                        help='Patrones regex para excluir archivos/carpas.')
    parser.add_argument('--mostrar_funciones', action='store_true',
                        help='Indica si se deben extraer y mostrar funciones de los archivos.')
    parser.add_argument('--mostrar_clases', action='store_true',
                        help='Indica si se deben extraer y mostrar clases de los archivos.')
    parser.add_argument('--guardar_archivo', type=str, default=None,
                        help='Ruta del archivo donde se guardará el árbol generado.')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    generator = DirectoryTreeGenerator(
        ruta_inicial=args.ruta_inicial,
        extensiones=args.extensiones,
        patrones_incluir=args.patrones_incluir,
        patrones_excluir=args.patrones_excluir,
        mostrar_funciones=args.mostrar_funciones,
        mostrar_clases=args.mostrar_clases
    )
    estructura = generator.generate_structure()
    generator.display_tree(estructura)

    if args.guardar_archivo:
        generator.save_tree_to_file(args.guardar_archivo, estructura)
