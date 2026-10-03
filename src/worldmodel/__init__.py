"""WorldModel RMC research prototype."""

from .compiler import MechanismCompiler, CompilerResult
from .engine import ResearchEngine
from .historical_engine import HistoricalResearchEngine
from .simulator import ReflexiveMarketSimulator
from .strategic import StrategicMarketSimulator
from .strategic_engine import StrategicResearchEngine

__all__ = [
    "MechanismCompiler",
    "CompilerResult",
    "ResearchEngine",
    "HistoricalResearchEngine",
    "ReflexiveMarketSimulator",
    "StrategicMarketSimulator",
    "StrategicResearchEngine",
]
__version__ = "0.3.0"
