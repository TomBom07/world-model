"""WorldModel RMC research prototype."""

from .breakthrough_engine import BreakthroughResearchEngine
from .compiler import MechanismCompiler, CompilerResult
from .engine import ResearchEngine
from .historical_engine import HistoricalResearchEngine
from .ontology_learning import CausalOntologyLearner, OntologyResult
from .open_world import OpenWorldBayes
from .simulator import ReflexiveMarketSimulator
from .strategic import StrategicMarketSimulator
from .strategic_engine import StrategicResearchEngine

__all__ = [
    "BreakthroughResearchEngine",
    "MechanismCompiler",
    "CompilerResult",
    "ResearchEngine",
    "HistoricalResearchEngine",
    "CausalOntologyLearner",
    "OntologyResult",
    "OpenWorldBayes",
    "ReflexiveMarketSimulator",
    "StrategicMarketSimulator",
    "StrategicResearchEngine",
]
__version__ = "0.4.0"
