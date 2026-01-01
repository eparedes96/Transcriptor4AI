# setup.py
from setuptools import setup, find_packages

setup(
    name="transcriptor",
    version="0.1.0",
    description="Herramienta para transcribir código y generar árboles de directorios",
    author="Enrique Paredes",
    author_email="eparedesbalen@gmail.com",
    packages=find_packages(),
    install_requires=[
        "PySimpleGUI",  # Si usas la interfaz en main.py
    ],
    entry_points={
        'console_scripts': [
            'transcriptor-cli=transcriptor.main:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
