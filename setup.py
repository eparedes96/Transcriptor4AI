# setup.py
from setuptools import setup, find_packages

setup(
    name="transcriptor",
    version="0.1.0",
    description="Herramienta para transcribir código y generar árboles de directorios",
    author="Enrique Paredes",
    author_email="eparedesbalen@gmail.com",
    packages=find_packages(),  # Encuentra automáticamente la carpeta 'transcriptor'
    install_requires=[
        "PySimpleGUI",  # Si usas la interfaz en main.py
    ],
    entry_points={
        'console_scripts': [
            'transcriptor-cli=transcriptor.main:main',  # Permite ejecutar la interfaz vía CLI
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
