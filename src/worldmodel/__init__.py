"""WorldModel RMC research prototype."""

from .compiler import MechanismCompiler, CompilerResult
from .engine import ResearchEngine
from .simulator import ReflexiveMarketSimulator

__all__ = ["MechanismCompiler", "CompilerResult", "ResearchEngine", "ReflexiveMarketSimulator"]
__version__ = "0.1.0"
