import logging

from coldfront.core.allocation.models import Allocation

from .models import AllocationBlueprint
from .utils import get_attribute_value

logger = logging.getLogger(__name__)


def apply_blueprint(allocation_id):
    allocation = Allocation.objects.get(id=allocation_id)
    resource = allocation.get_parent_resource
    blueprint = AllocationBlueprint.objects.filter(resource=resource).first() if resource else None
    if blueprint is None:
        message = f"No allocation blueprint for {resource.name if resource else 'an allocation without a resource'}; nothing created for allocation {allocation.id}."
        logger.debug(message)
        return {"created_attributes": [], "failed_attributes": {}, "message": message}

    created, failed = [], {}
    for attribute_blueprint in blueprint.allocationattributeblueprint_set.select_related("allocation_attribute_type"):
        attribute_type = attribute_blueprint.allocation_attribute_type
        # an attribute the allocation already has is left as it is
        if allocation.allocationattribute_set.filter(allocation_attribute_type=attribute_type).exists():
            continue
        try:
            value = get_attribute_value(allocation_id, attribute_blueprint.value) if attribute_blueprint.value else ""
        except ValueError as e:
            failed[attribute_type.name] = str(e)
            continue
        allocation.allocationattribute_set.create(allocation_attribute_type=attribute_type, value=value)
        created.append(attribute_type.name)

    logger.info(f"Created allocation attributes for allocation {allocation.id} based on blueprint {blueprint.id}")
    if failed:
        logger.warning(
            f"Failed to create some allocation attributes for allocation {allocation.id} based on blueprint {blueprint.id}: {failed}"
        )
    return {
        "created_attributes": created,
        "failed_attributes": failed,
        "message": f"Created allocation attributes for allocation {allocation.id} based on blueprint {blueprint.id}",
    }
