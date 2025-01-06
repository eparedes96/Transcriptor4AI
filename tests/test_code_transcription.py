# tests/test_code_transcription.py

import unittest
from unittest.mock import mock_open, patch
import tempfile
import os
import re

from code_transcription import (
    contains_only_comments_or_blank,
    es_test,
    determine_file_inclusion,
    list_functions,
    list_classes,
    CodeTranscription
)


class TestCodeTranscription(unittest.TestCase):

    def test_contains_only_comments_or_blank(self):
        # Caso con solo comentarios
        texto_comentarios = """
        # Este es un comentario
        # Otro comentario

        """
        self.assertTrue(contains_only_comments_or_blank(texto_comentarios))

        # Caso con comentarios y líneas en blanco
        texto_comentarios_blanco = """
        # Comentario


        # Otro comentario
        """
        self.assertTrue(contains_only_comments_or_blank(texto_comentarios_blanco))

        # Caso con código válido
        texto_con_codigo = """
        # Comentario
        def funcion():
            pass
        """
        self.assertFalse(contains_only_comments_or_blank(texto_con_codigo))

        # Caso vacío
        texto_vacio = ""
        self.assertTrue(contains_only_comments_or_blank(texto_vacio))

    def test_es_test(self):
        self.assertTrue(es_test("test_example.py"))
        self.assertTrue(es_test("tests_example.py"))
        self.assertTrue(es_test("example_test.py"))
        self.assertTrue(es_test("example_tests.py"))
        self.assertFalse(es_test("example.py"))
        self.assertFalse(es_test("example_test.txt"))

    def test_determine_file_inclusion(self):
        # Modo 'solo_modulos'
        self.assertTrue(determine_file_inclusion(
            modo='solo_modulos',
            nombre_archivo='module.py'
        ))
        self.assertFalse(determine_file_inclusion(
            modo='solo_modulos',
            nombre_archivo='test_module.py'
        ))

        # Modo 'solo_tests'
        self.assertTrue(determine_file_inclusion(
            modo='solo_tests',
            nombre_archivo='test_module.py'
        ))
        self.assertFalse(determine_file_inclusion(
            modo='solo_tests',
            nombre_archivo='module.py'
        ))

        # Modo 'todo'
        self.assertTrue(determine_file_inclusion(
            modo='todo',
            nombre_archivo='module.py'
        ))
        self.assertTrue(determine_file_inclusion(
            modo='todo',
            nombre_archivo='test_module.py'
        ))

        # Modo inválido
        self.assertFalse(determine_file_inclusion(
            modo='invalido',
            nombre_archivo='module.py'
        ))

        # Con patrones de inclusión/exclusión
        include_patterns = [re.compile(r'^module_.*\.py$')]
        exclude_patterns = [re.compile(r'^module_exclude_.*\.py$')]

        self.assertTrue(determine_file_inclusion(
            modo='todo',
            nombre_archivo='module_include.py',
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        ))
        self.assertFalse(determine_file_inclusion(
            modo='todo',
            nombre_archivo='module_exclude.py',
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        ))
        self.assertFalse(determine_file_inclusion(
            modo='todo',
            nombre_archivo='other_module.py',
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        ))

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

    def test_code_transcription_transcribe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear estructura de directorios y archivos
            os.makedirs(os.path.join(temp_dir, "subdir"))
            archivos = {
                "module1.py": "# Comentario\n\ndef func1():\n    pass\n",
                "module2.py": "# Solo comentarios\n# Otro comentario\n",
                "test_module.py": "# Test comentario\ndef test_func():\n    pass\n",
                "__init__.py": "# Init\n",
                "readme.md": "# Readme\n"
            }

            for nombre, contenido in archivos.items():
                ruta = os.path.join(temp_dir, "subdir" if "subdir" in nombre else "", nombre)
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(contenido)

            transcription = CodeTranscription(
                ruta_carpetas=temp_dir,
                modo='solo_modulos',
                extensiones=['.py'],
                patrones_incluir=None,
                patrones_excluir=[r'^__init__\.py$'],
                mostrar_clases=False
            )
            salida_path = os.path.join(temp_dir, "transcripcion.txt")
            transcription.transcribe(salida_path)

            # Leer el archivo de salida y verificar el contenido
            with open(salida_path, "r", encoding="utf-8") as f:
                contenido_salida = f.read()

            # Debe incluir module1.py y no incluir module2.py (solo comentarios) ni test_module.py
            self.assertIn("[ARCHIVO 1] - module1.py", contenido_salida)
            self.assertNotIn("module2.py", contenido_salida)
            self.assertNotIn("test_module.py", contenido_salida)
            self.assertNotIn("__init__.py", contenido_salida)
            self.assertNotIn("readme.md", contenido_salida)

    def test_code_transcription_with_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archivo = "module_with_classes.py"
            contenido = """
            # Comentarios
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

            transcription = CodeTranscription(
                ruta_carpetas=temp_dir,
                modo='todo',
                extensiones=['.py'],
                mostrar_clases=True
            )
            salida_path = os.path.join(temp_dir, "transcripcion_con_clases.txt")
            transcription.transcribe(salida_path)

            with open(salida_path, "r", encoding="utf-8") as f:
                salida = f.read()

            self.assertIn("[ARCHIVO 1] - module_with_classes.py", salida)
            self.assertIn("CLASES:", salida)
            self.assertIn(" - Clase1", salida)
            self.assertIn(" - Clase2", salida)

    def test_code_transcription_error_handling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archivo = "module_error.py"
            # Archivo con código inválido
            contenido = "def func(:\n    pass"
            ruta = os.path.join(temp_dir, archivo)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)

            transcription = CodeTranscription(
                ruta_carpetas=temp_dir,
                modo='todo',
                extensiones=['.py'],
                mostrar_clases=False
            )
            salida_path = os.path.join(temp_dir, "transcripcion_error.txt")
            with patch("builtins.print") as mocked_print:
                transcription.transcribe(salida_path)
                # Verificar que se imprimió un mensaje de error
                mocked_print.assert_called_with(
                    f"Error al procesar el archivo {ruta}: invalid syntax (<unknown>, line 1)")

            # El archivo de salida debería existir pero sin contenido de módulos válidos
            with open(salida_path, "r", encoding="utf-8") as f:
                salida = f.read()
            self.assertEqual(salida, "CODIGO:\n\n")


if __name__ == '__main__':
    unittest.main()