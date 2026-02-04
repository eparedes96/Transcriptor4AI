"""
Módulo principal de calculadora.
Este docstring debería conservarse en modo Skeleton.
"""

class Calculator:
    """Clase simple para operaciones aritméticas."""

    def __init__(self, initial_value: int = 0):
        self.value = initial_value

    def add(self, number: int) -> int:
        """Suma un número al valor actual."""
        self.value += number
        return self.value

    def _internal_reset(self):
        self.value = 0

def standalone_function():
    """Función fuera de clase."""
    print("Logic executed")