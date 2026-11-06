"""The blueprint models, and that the test setup can build them."""

from coldfront.core.allocation.models import AllocationAttributeType, AttributeType
from coldfront.core.resource.models import Resource, ResourceType

from allocation_blueprint.models import AllocationAttributeBlueprint, AllocationBlueprint


def make_blueprint(resource_name):
    resource = Resource.objects.create(
        resource_type=ResourceType.objects.get_or_create(name="Storage", description="storage")[0],
        name=resource_name,
        description="a resource",
    )
    return AllocationBlueprint.objects.create(resource=resource)


def test_a_blueprint_names_its_resource(db):
    blueprint = make_blueprint("hpc-storage")

    assert str(blueprint) == "Allocation blueprint for resource: hpc-storage"


def test_an_attribute_blueprint_shows_its_type_and_initial_value(db):
    attribute_type = AllocationAttributeType.objects.create(
        name="Storage Quota (TB)", attribute_type=AttributeType.objects.get_or_create(name="Float")[0]
    )
    attribute_blueprint = AllocationAttributeBlueprint.objects.create(
        blueprint=make_blueprint("hpc-storage"), allocation_attribute_type=attribute_type, value="1"
    )

    assert str(attribute_blueprint) == "Storage Quota (TB): 1"
