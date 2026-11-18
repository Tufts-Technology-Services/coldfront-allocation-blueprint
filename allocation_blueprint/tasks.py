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


def compare_with_blueprints(create_missing):
    """Compare every active allocation of a resource with a blueprint against that blueprint.

    Returns a dict of ``checked``, how many allocations were checked, and these lists:

    - ``missing``: attributes an allocation doesn't have, with the value they'd get. With
      ``create_missing``, they're created as well.
    - ``mismatches``: existing attributes whose values differ from the blueprint's.
    - ``case_differences``: existing attributes whose values differ from the blueprint's only in case.
      Older shares can have mixed-case names while project keys are lowercase, so these are expected;
      they're kept apart so they don't bury the mismatches.
    - ``not_created``: missing attributes of allocations with a case difference. Such an allocation's
      names aren't the blueprint's, so a value made from the blueprint could name the wrong share; these
      are never created, and someone fills them in by hand.
    - ``failed``: values whose placeholders couldn't be filled in.

    Existing values are never changed.
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

    checked = 0
    found = {name: [] for name in ("missing", "mismatches", "case_differences", "not_created", "failed")}
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

        # the whole allocation is compared before anything is created: whether to create depends on
        # every attribute, whatever order the blueprint lists them in
        missing, case_differences = [], []
        for attribute_blueprint in blueprint.allocationattributeblueprint_set.all():
            attribute_type = attribute_blueprint.allocation_attribute_type
            current = existing.get(attribute_type.pk)
            if current and not attribute_blueprint.value:
                # no initial value, so nothing to compare against
                continue
            try:
                expected = blueprint_value_for(allocation.pk, attribute_blueprint)
            except ValueError as e:
                found["failed"].append(
                    {"allocation": allocation.pk, "attribute": attribute_type.name, "reason": str(e)}
                )
                continue
            if current is None:
                missing.append((attribute_type, expected))
                continue
            for value in current:
                if value == expected:
                    continue
                difference = {
                    "allocation": allocation.pk,
                    "attribute": attribute_type.name,
                    "expected": expected,
                    "actual": value,
                }
                if value.lower() == expected.lower():
                    case_differences.append(difference)
                else:
                    found["mismatches"].append(difference)

        found["case_differences"].extend(case_differences)
        differing = ", ".join(dict.fromkeys(difference["attribute"] for difference in case_differences))
        for attribute_type, value in missing:
            entry = {"allocation": allocation.pk, "attribute": attribute_type.name, "value": value}
            if case_differences:
                reason = (
                    f"its {differing} differ from the blueprint only in case, so this value may name the wrong share"
                )
                found["not_created"].append({**entry, "reason": reason})
                continue
            if create_missing:
                allocation.allocationattribute_set.create(allocation_attribute_type=attribute_type, value=value)
            found["missing"].append(entry)

    return {"checked": checked, **found}


def check_blueprint_attributes():
    """Check that active allocations have every attribute their resource's blueprint defines.

    Goes through the Active allocations of every resource that has a blueprint. A missing attribute
    is created with the blueprint's initial value, placeholders filled in as ``apply_blueprint``
    does, unless the allocation has a value differing from the blueprint's only in case (see
    ``compare_with_blueprints``). An existing attribute whose value differs from the blueprint's is
    left as it is and reported; a blueprint attribute with no initial value never differs.

    Returns a dict with ``checked`` (how many allocations), ``created``, ``mismatches``,
    ``case_differences``, ``not_created`` and ``failed`` (placeholders that couldn't be filled in),
    each a list of dicts naming the allocation and attribute, and a ``message``.
    """
    found = compare_with_blueprints(create_missing=True)
    found["created"] = found.pop("missing")
    message = (
        f"Checked {found['checked']} active allocations against their blueprints: created {len(found['created'])} "
        f"attributes ({len(found['not_created'])} not created, on allocations differing in case), found "
        f"{len(found['mismatches'])} mismatches and {len(found['case_differences'])} differing only in case, "
        f"couldn't fill in {len(found['failed'])} values."
    )
    logger.info(message)
    return {**found, "message": message}


def report_blueprint_differences():
    """Report how active allocations differ from their resource's blueprint, changing nothing.

    Checks the same allocations, in the same way, as ``check_blueprint_attributes``, but where that
    task creates a missing attribute this one lists it under ``missing`` with the value it would be
    created with. ``not_created`` lists what that task wouldn't create.

    Returns a dict with ``checked`` (how many allocations), ``missing``, ``mismatches``,
    ``case_differences``, ``not_created`` and ``failed``, each a list of dicts naming the allocation
    and attribute, and a ``message``.
    """
    found = compare_with_blueprints(create_missing=False)
    message = (
        f"Checked {found['checked']} active allocations against their blueprints, changing nothing: "
        f"{len(found['missing'])} attributes missing ({len(found['not_created'])} more that wouldn't be created, on "
        f"allocations differing in case), {len(found['mismatches'])} mismatches and "
        f"{len(found['case_differences'])} differing only in case, couldn't fill in {len(found['failed'])} values."
    )
    logger.info(message)
    return {**found, "message": message}
