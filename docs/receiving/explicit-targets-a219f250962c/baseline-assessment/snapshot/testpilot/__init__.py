"""TestPilot: diff-aware pytest generation with a run/repair loop."""
__version__ = "0.1.0"

from .diff import ChangedFunction, changed_functions, parse_unified_diff  # noqa: F401
from .loop import LoopResult, TestPilot  # noqa: F401
from .model import OpenAICompatClient, RoutingConfig, ScriptedModel, make_client  # noqa: F401
from .sandbox import SandboxResult, run_pytest  # noqa: F401
