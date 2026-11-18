import logging

from coldfront.core.allocation.models import Allocation

from .models import AllocationBlueprint
from .utils import get_attribute_value

logger = logging.getLogger(__name__)


class BlueprintValueError(ValueError):
    """Some of a blueprint's initial values couldn't be filled in for an allocation.

    Raised once the task has created every attribute it could, so the task is recorded as failed.
    """


def blueprint_value_for(allocation_id, attribute_blueprint):
    """The attribute blueprint's initial value for the allocation, placeholders filled in ("" if it has none).

    Raises ValueError if a placeholder can't be filled in.
    """
    return get_attribute_value(allocation_id, attribute_blueprint.value) if attribute_blueprint.value else ""


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
            value = blueprint_value_for(allocation_id, attribute_blueprint)
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


def check_blueprint_attributes():
    """Check that active allocations have every attribute their resource's blueprint defines.

    Goes through the Active allocations of every resource that has a blueprint. A missing attribute is created with the blueprint's initial
    value, placeholders filled in as ``apply_blueprint`` does. An existing attribute whose value
    differs from the blueprint's is left as it is and reported as a mismatch; a blueprint attribute
    with no initial value never mismatches.

    Returns a dict with ``checked`` (how many allocations), ``created``, ``mismatches`` and
    ``failed`` (placeholders that couldn't be filled in), each a list of dicts naming the
    allocation and attribute, and a ``message``.
    """
    blueprints = {
        blueprint.resource_id: blueprint
        for blueprint in AllocationBlueprint.objects.prefetch_related(
            "allocationattributeblueprint_set__allocation_attribute_type"
        )
    }
    allocations = (
        Allocation.objects.filter(status__name="Active", resources__in=list(blueprints)).distinct().order_by("pk")
    )

    checked, created, mismatches, failed = 0, [], [], []
    for allocation in allocations:
        # the same resource apply_blueprint would take the blueprint from
        resource = allocation.get_parent_resource
        blueprint = blueprints.get(resource.pk) if resource else None
        if blueprint is None:
            continue
        checked += 1
        existing = {}
        for attribute in allocation.allocationattribute_set.all():
            existing.setdefault(attribute.allocation_attribute_type_id, []).append(attribute.value)

        for attribute_blueprint in blueprint.allocationattributeblueprint_set.all():
            attribute_type = attribute_blueprint.allocation_attribute_type
            current = existing.get(attribute_type.pk)
            if current and not attribute_blueprint.value:
                # no initial value, so nothing to compare against
                continue
            try:
                expected = blueprint_value_for(allocation.pk, attribute_blueprint)
            except ValueError as e:
                failed.append({"allocation": allocation.pk, "attribute": attribute_type.name, "reason": str(e)})
                continue
            if current is None:
                allocation.allocationattribute_set.create(allocation_attribute_type=attribute_type, value=expected)
                created.append({"allocation": allocation.pk, "attribute": attribute_type.name, "value": expected})
                continue
            mismatches.extend(
                {"allocation": allocation.pk, "attribute": attribute_type.name, "expected": expected, "actual": value}
                for value in current
                if value != expected
            )

    message = (
        f"Checked {checked} active allocations against their blueprints: created {len(created)} attributes, "
        f"found {len(mismatches)} mismatches, couldn't fill in {len(failed)} values."
    )
    logger.info(message)
    return {"checked": checked, "created": created, "mismatches": mismatches, "failed": failed, "message": message}
