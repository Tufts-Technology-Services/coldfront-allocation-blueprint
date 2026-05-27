import importlib
import logging
from django.apps import AppConfig
from .constants import BLUEPRINT_ENABLE_SIGNALS

logger = logging.getLogger(__name__)


class AllocationBlueprintConfig(AppConfig):
    """
    Configuration for the allocation blueprint plugin.
    This class initializes signal receivers based on settings and tests the blueprint client configuration."""

    name = "allocation_blueprint"

    def ready(self):
        if BLUEPRINT_ENABLE_SIGNALS:
            logger.info("Allocation blueprint signals are enabled. Importing signal handlers.")
            importlib.import_module("allocation_blueprint.signals")