# tests/test_directory_tree.py

import unittest
from unittest.mock import mock_open, patch
import tempfile
import os
import re
import json

from directory_tree import (
    list_functions,
    list_classes,
    DirectoryTreeGenerator
)


class TestDirectoryTreeGenerator(unittest.TestCase):

    def test_list_functions(self):
        codigo = """
        # Comentario
        def funcion1(param1, param2):
            pass

        def funcion2():
            pass

        class Clase:
            def metodo(self):
                pass
        """
        with patch("builtins.open", mock_open(read_data=codigo)):
            funciones = list_functions("dummy_path.py")
            self.assertIn("funcion1(param1, param2)", funciones)
            self.assertIn("funcion2()", funciones)
            self.assertNotIn("metodo(self)", funciones)  # Métodos dentro de clases no se consideran funciones globales

    def test_list_classes(self):
        codigo = """
        # Comentario
        class Clase1:
            pass

        class Clase2:
            def metodo(self):
                pass

        def funcion():
            pass
        """
        with patch("builtins.open", mock_open(read_data=codigo)):
            clases = list_classes("dummy_path.py")
            self.assertIn("Clase1", clases)
            self.assertIn("Clase2", clases)
            self.assertNotIn("funcion", clases)

    def test_directory_tree_generator_generate_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear estructura de directorios y archivos
            os.makedirs(os.path.join(temp_dir, "subdir1"))
            os.makedirs(os.path.join(temp_dir, "subdir2"))

            archivos = {
                "module1.py": "def func1(): pass",
                "module2.js": "function func2() {}",
                "test_module.py": "def test_func(): pass",
                "__init__.py": "",
                "readme.md": "# Readme",
                "subdir1/file1.py": "# Solo comentarios\n",
                "subdir1/file2.py": "def func3(): pass",
                "subdir2/file3.pyc": "compiled code",
                "subdir2/file4.py": "def func4(): pass"
            }

            for nombre, contenido in archivos.items():
                ruta = os.path.join(temp_dir, nombre)
                dir_path = os.path.dirname(ruta)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(contenido)

            generator = DirectoryTreeGenerator(
                ruta_inicial=temp_dir,
                extensiones=['.py', '.js'],
                patrones_incluir=None,
                patrones_excluir=[r'^__init__\.py$', r'^.*\.pyc$'],
                mostrar_funciones=True,
                mostrar_clases=False
            )
            estructura = generator.generate_structure()

            # Verificar estructura generada
            expected_structure = {
                "module1.py": ["func1()"],
                "module2.js": None,
                "test_module.py": ["test_func()"],
                "readme.md": None,
                "subdir1": {
                    "file1.py": None,  # Solo comentarios
                    "file2.py": ["func3()"]
                },
                "subdir2": {
                    "file4.py": ["func4()"]
                }
            }

            self.assertDictEqual(estructura, expected_structure)

    def test_directory_tree_generator_display_tree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear archivos y directorios
            os.makedirs(os.path.join(temp_dir, "subdir"))
            archivo = os.path.join(temp_dir, "module.py")
            with open(archivo, "w", encoding="utf-8") as f:
                f.write("def func(): pass\n")

            generator = DirectoryTreeGenerator(
                ruta_inicial=temp_dir,
                extensiones=['.py'],
                patrones_incluir=None,
                patrones_excluir=None,
                mostrar_funciones=True,
                mostrar_clases=False
            )
            estructura = generator.generate_structure()

            with patch('builtins.print') as mocked_print:
                generator.display_tree(estructura)
                # Verificar llamadas a print
                mocked_print.assert_any_call(f"{temp_dir}/")
                mocked_print.assert_any_call(f"└── module.py")
                mocked_print.assert_any_call(f"    └── func()")

    def test_directory_tree_generator_save_tree_to_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear archivos y directorios
            os.makedirs(os.path.join(temp_dir, "subdir"))
            archivo = os.path.join(temp_dir, "module.py")
            with open(archivo, "w", encoding="utf-8") as f:
                f.write("def func(): pass\n")

            generator = DirectoryTreeGenerator(
                ruta_inicial=temp_dir,
                extensiones=['.py'],
                patrones_incluir=None,
                patrones_excluir=None,
                mostrar_funciones=True,
                mostrar_clases=False
            )
            estructura = generator.generate_structure()

            salida_path = os.path.join(temp_dir, "arbol.txt")
            generator.save_tree_to_file(salida_path, estructura)

            # Leer el archivo de salida y verificar contenido
            with open(salida_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            expected_contenido = f"{temp_dir}/\n└── module.py\n    └── func()\n"
            self.assertEqual(contenido, expected_contenido)

    def test_directory_tree_generator_with_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archivo = "module_with_classes.py"
            contenido = """
            class Clase1:
                def metodo1(self):
                    pass

            def funcion1():
                pass

            class Clase2:
                pass
            """
            ruta = os.path.join(temp_dir, archivo)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)

            generator = DirectoryTreeGenerator(
                ruta_inicial=temp_dir,
                extensiones=['.py'],
                mostrar_funciones=True,
                mostrar_clases=True
            )
            estructura = generator.generate_structure()

            expected_structure = {
                "module_with_classes.py": {
                    "funciones": ["funcion1()"],
                    "clases": ["Clase1", "Clase2"]
                }
            }

            self.assertDictEqual(estructura, expected_structure)

    def test_directory_tree_generator_error_handling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archivo = "invalid_module.py"
            contenido = "def func(:\n    pass"  # Sintaxis inválida
            ruta = os.path.join(temp_dir, archivo)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)

            generator = DirectoryTreeGenerator(
                ruta_inicial=temp_dir,
                extensiones=['.py'],
                mostrar_funciones=True,
                mostrar_clases=False
            )
            with patch("builtins.print") as mocked_print:
                estructura = generator.generate_structure()
                # Debido a la sintaxis inválida, no se deberían extraer funciones
                expected_structure = {
                    "invalid_module.py": None
                }
                self.assertDictEqual(estructura, expected_structure)
                # Verificar que se imprimió un mensaje de error
                mocked_print.assert_called_with(f"Error al procesar {ruta}: invalid syntax (<unknown>, line 1)")

if __name__ == '__main__':
    unittest.main()
