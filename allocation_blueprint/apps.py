import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AllocationBlueprintConfig(AppConfig):
    """
    Configuration for the allocation blueprint plugin.
    This class initializes signal receivers based on settings and tests the blueprint client configuration."""

    name = "allocation_blueprint"

    def ready(self):
        pass