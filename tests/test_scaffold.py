from job_aggregator import __version__
from job_aggregator.app.core.config import Settings
from job_aggregator.app.core.logging import configure_logging


def test_package_exposes_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_defaults_are_local() -> None:
    settings = Settings()

    assert settings.environment == "local"
    assert settings.database_url.startswith("sqlite:///")


def test_logging_can_be_configured() -> None:
    configure_logging("INFO")
