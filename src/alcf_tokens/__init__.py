from importlib.metadata import version
from .cli import cli

__version__ = version("alcf-tokens")

__all__ = ["cli"]
