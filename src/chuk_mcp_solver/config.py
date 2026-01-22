"""Configuration management for chuk-mcp-solver.

Three-tier precedence:
1. Environment variables (highest priority)
2. YAML configuration file
3. Default values (lowest priority)
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Configuration file path
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "chuk-mcp-solver" / "config.yaml"
CONFIG_PATH = Path(os.getenv("CHUK_SOLVER_CONFIG", str(DEFAULT_CONFIG_PATH)))


def load_yaml_config() -> dict[str, Any]:
    """Load configuration from YAML file.

    Returns:
        Configuration dictionary, or empty dict if file doesn't exist.
    """
    if not CONFIG_PATH.exists():
        logger.debug(f"Config file not found at {CONFIG_PATH}, using defaults")
        return {}

    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f) or {}
        logger.info(f"Loaded configuration from {CONFIG_PATH}")
        return config
    except Exception as e:
        logger.warning(f"Failed to load config from {CONFIG_PATH}: {e}")
        return {}


# Load YAML config once at module level
_yaml_config = load_yaml_config()


class Config:
    """Configuration for the solver.

    Uses three-tier precedence: env var > YAML > default.
    """

    # Default solver provider
    DEFAULT_PROVIDER = os.getenv(
        "CHUK_SOLVER_PROVIDER",
        _yaml_config.get("default_provider", "ortools"),
    )

    # Tool-specific provider overrides
    TOOL_CONFIG_MAP: dict[str, str] = {
        "solve_constraint_model": os.getenv(
            "CHUK_SOLVER_TOOL_PROVIDER",
            _yaml_config.get("tool_providers", {}).get("solve_constraint_model", DEFAULT_PROVIDER),
        ),
    }

    @classmethod
    def get_provider_for_tool(cls, tool_name: str) -> str:
        """Get the provider to use for a specific tool.

        Args:
            tool_name: Name of the tool.

        Returns:
            Provider type string.
        """
        return cls.TOOL_CONFIG_MAP.get(tool_name, cls.DEFAULT_PROVIDER)
