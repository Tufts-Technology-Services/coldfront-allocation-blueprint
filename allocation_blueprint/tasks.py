import logging

from coldfront.core.allocation.models import Allocation

from .models import AllocationBlueprint
from .utils import get_attribute_value

logger = logging.getLogger(__name__)


class BlueprintValueError(ValueError):
    """Some of a blueprint's initial values couldn't be filled in for an allocation.

    Raised once the task has created every attribute it could, so the task is recorded as failed.
    """


def apply_blueprint(allocation_id):
    allocation = Allocation.objects.get(id=allocation_id)
    resource = allocation.get_parent_resource
    blueprint = AllocationBlueprint.objects.filter(resource=resource).first() if resource else None
    if blueprint is None:
        message = f"No allocation blueprint for {resource.name if resource else 'an allocation without a resource'}; nothing created for allocation {allocation.id}."
        logger.debug(message)
        return {"created_attributes": [], "message": message}

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
        # raised only now, so the attributes that could be created were: the task is recorded as
        # failed, naming what's missing, and someone fills those in by hand
        reasons = "; ".join(f"{name}: {reason}" for name, reason in failed.items())
        raise BlueprintValueError(
            f"Couldn't fill in {len(failed)} of blueprint {blueprint.id}'s attributes for allocation "
            f"{allocation.id} ({reasons}). Created: {', '.join(created) or 'none'}."
        )
    return {
        "created_attributes": created,
        "message": f"Created allocation attributes for allocation {allocation.id} based on blueprint {blueprint.id}",
    }
