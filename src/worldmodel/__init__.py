"""WorldModel RMC research prototype."""

from .breakthrough_engine import BreakthroughResearchEngine
from .compiler import MechanismCompiler, CompilerResult
from .engine import ResearchEngine
from .frontier_engine import FrontierResearchEngine
from .historical_engine import HistoricalResearchEngine
from .physics_engine import PhysicsDiscoveryEngine
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
    "FrontierResearchEngine",
    "HistoricalResearchEngine",
    "PhysicsDiscoveryEngine",
    "CausalOntologyLearner",
    "OntologyResult",
    "OpenWorldBayes",
    "ReflexiveMarketSimulator",
    "StrategicMarketSimulator",
    "StrategicResearchEngine",
]
__version__ = "0.7.0"
