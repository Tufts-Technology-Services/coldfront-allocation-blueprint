import logging

from coldfront.core.allocation.models import AllocationAttribute

from .models import AllocationBlueprint

logger = logging.getLogger(__name__)


def apply_blueprint(allocation):
    blueprint = AllocationBlueprint.objects.get(resource=allocation.get_parent_resource)
    if blueprint:
        attribute_blueprints = blueprint.allocationattributeblueprint_set.all()
        for attribute_blueprint in attribute_blueprints:
            # don't overwrite existing attributes of the same type for the allocation, only create if it doesn't already exist
            if not AllocationAttribute.objects.filter(allocation=allocation, allocation_attribute_type=attribute_blueprint.allocation_attribute_type).exists():
                AllocationAttribute.objects.create(
                    allocation_attribute_type=attribute_blueprint.allocation_attribute_type,
                    value=attribute_blueprint.value,
                    allocation=allocation)
        logger.info(f"Created allocation attributes for allocation {allocation.id} based on blueprint {blueprint.id}")
    else:
        logger.debug(f"No allocation blueprint found for resource {allocation.get_parent_resource.name}. No attributes created for allocation {allocation.id}.")