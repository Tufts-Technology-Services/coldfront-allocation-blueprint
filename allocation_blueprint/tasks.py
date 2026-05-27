import logging

from coldfront.core.allocation.models import Allocation, AllocationAttribute

from .models import AllocationBlueprint
from .utils import get_attribute_value

logger = logging.getLogger(__name__)


def apply_blueprint(allocation_id):
    allocation = Allocation.objects.get(id=allocation_id)
    blueprint = AllocationBlueprint.objects.get(resource=allocation.get_parent_resource)
    if blueprint:
        attribute_blueprints = blueprint.allocationattributeblueprint_set.all()
        for attribute_blueprint in attribute_blueprints:
            # don't overwrite existing attributes of the same type for the allocation, only create if it doesn't already exist
            if not AllocationAttribute.objects.filter(allocation=allocation, allocation_attribute_type=attribute_blueprint.allocation_attribute_type).exists():
                if attribute_blueprint.value:
                    AllocationAttribute.objects.create(
                        allocation_attribute_type=attribute_blueprint.allocation_attribute_type,
                        value=get_attribute_value(allocation_id, attribute_blueprint.value),
                        allocation=allocation)
                else:
                    AllocationAttribute.objects.create(
                        allocation_attribute_type=attribute_blueprint.allocation_attribute_type,
                        value="",
                        allocation=allocation)
        logger.info(f"Created allocation attributes for allocation {allocation.id} based on blueprint {blueprint.id}")
    else:
        logger.debug(f"No allocation blueprint found for resource {allocation.get_parent_resource.name}. No attributes created for allocation {allocation.id}.")