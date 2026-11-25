"""Ponto de entrada do app:  streamlit run streamlit_app.py

O agent.py usa imports relativos (foi escrito como pacote Python), então ele
é executado aqui como módulo do pacote do projeto.
"""
import runpy
import sys
from pathlib import Path

_PASTA = Path(__file__).resolve().parent
for caminho in (str(_PASTA), str(_PASTA.parent)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

runpy.run_module(f"{_PASTA.name}.agent", run_name="__main__")
