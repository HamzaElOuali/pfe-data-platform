"""
Tests minimaux — Vérification des imports des modules src/.

Objectif : s'assurer que tous les packages Python du projet
sont importables sans erreur après installation.
"""

import importlib
import pytest


# Liste des modules à tester
MODULES = [
    "src",
    "src.ingestion",
    "src.processing",
    "src.utils",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_import_module(module_name: str):
    """Vérifie que chaque module src/ est importable sans erreur."""
    mod = importlib.import_module(module_name)
    assert mod is not None, f"Le module {module_name} n'a pas pu être importé"


def test_python_version():
    """Vérifie que Python 3.11+ est utilisé."""
    import sys
    assert sys.version_info >= (3, 11), (
        f"Python 3.11+ requis, version actuelle : {sys.version}"
    )
