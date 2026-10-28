"""Configuration settings for the Packaging Reporting Agent."""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    """Agent runtime configuration settings."""

    # LLM Settings
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o")
    )
    temperature: float = 0.0

    # Persistence
    db_path: str = field(
        default_factory=lambda: os.getenv("DB_PATH", "packaging_agent_state.db")
    )

    # ServiceNow
    snow_instance_url: str = field(
        default_factory=lambda: os.getenv("SNOW_INSTANCE_URL", "https://mock.service-now.com")
    )
    snow_username: str = field(
        default_factory=lambda: os.getenv("SNOW_USERNAME", "admin")
    )
    snow_password: str = field(
        default_factory=lambda: os.getenv("SNOW_PASSWORD", "")
    )
    default_assignment_group: str = field(
        default_factory=lambda: os.getenv(
            "SNOW_ASSIGNMENT_GROUP",
            "ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging",
        )
    )

    # Target Request Types
    excluded_request_types: List[str] = field(
        default_factory=lambda: ["New Application Request"]
    )
    valid_request_types: List[str] = field(
        default_factory=lambda: [
            "Existing Application",
            "Distribution",
            "ACENET",
            "Horse Application",
        ]
    )

    # Milestones (relative days post-closure)
    milestones: List[int] = field(default_factory=lambda: [1, 3, 7])

    # Telemetry Compliance Thresholds
    green_threshold: float = 90.0
    yellow_threshold: float = 70.0

    # Simulation / Mock Mode
    mock_external_services: bool = field(
        default_factory=lambda: os.getenv("MOCK_EXTERNAL_SERVICES", "true").lower()
        in ("1", "true", "yes")
    )


# Global settings singleton
settings = Settings()
