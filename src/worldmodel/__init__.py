"""WorldModel RMC research prototype."""

from .breakthrough_engine import BreakthroughResearchEngine
from .compiler import MechanismCompiler, CompilerResult
from .engine import ResearchEngine
from .frontier_engine import FrontierResearchEngine
from .historical_engine import HistoricalResearchEngine
from .law_discovery import JointOntologyLawLearner, LatentLawCompiler
from .nonlinear_ontology import InterventionAwareOntologyLearner
from .ontology_learning import CausalOntologyLearner, OntologyResult
from .open_world import OpenWorldBayes
from .simulator import ReflexiveMarketSimulator
from .strategic import StrategicMarketSimulator
from .strategic_engine import StrategicResearchEngine
from .theory_invention import ResidualTheoryInventor

__all__ = [
    "BreakthroughResearchEngine",
    "CompilerResult",
    "CausalOntologyLearner",
    "FrontierResearchEngine",
    "HistoricalResearchEngine",
    "InterventionAwareOntologyLearner",
    "JointOntologyLawLearner",
    "LatentLawCompiler",
    "MechanismCompiler",
    "OntologyResult",
    "OpenWorldBayes",
    "ResearchEngine",
    "ResidualTheoryInventor",
    "ReflexiveMarketSimulator",
    "StrategicMarketSimulator",
    "StrategicResearchEngine",
]
__version__ = "0.5.0"
