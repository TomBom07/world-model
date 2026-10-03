"""WorldModel RMC research prototype."""

from .compiler import MechanismCompiler, CompilerResult
from .engine import ResearchEngine
from .simulator import ReflexiveMarketSimulator
from .strategic import StrategicMarketSimulator
from .strategic_engine import StrategicResearchEngine

__all__ = [
    "MechanismCompiler",
    "CompilerResult",
    "ResearchEngine",
    "ReflexiveMarketSimulator",
    "StrategicMarketSimulator",
    "StrategicResearchEngine",
]
__version__ = "0.2.0"
