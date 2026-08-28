"""POSTKutsche – Redaktionskalender für Blogs, Shops und soziale Netzwerke.

Die Fassung steht ausschließlich hier. In MailBurg stand sie zusätzlich in
pyproject.toml und blieb dort auf 0.1.0 stehen, während das Programm längst
0.9.0 meldete – pip installierte danach eine Fassung, die es nicht mehr gab.
Diesen Fehler machen wir nicht zweimal: pyproject.toml liest die Zahl von hier.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
