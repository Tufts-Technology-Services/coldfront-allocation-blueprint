"""apply_blueprint gives a new allocation its resource's blueprint attributes."""

import pytest

from allocation_blueprint.models import AllocationBlueprint
from allocation_blueprint.tasks import apply_blueprint


@pytest.fixture
def make_blueprint(make_attribute_type):
    """A blueprint for the resource, with {attribute type name: initial value}."""

    def _make(resource, attributes):
        blueprint = AllocationBlueprint.objects.create(resource=resource)
        for name, value in attributes.items():
            blueprint.allocationattributeblueprint_set.create(
                allocation_attribute_type=make_attribute_type(name), value=value
            )
        return blueprint

    return _make


def attribute_values(allocation):
    return dict(allocation.allocationattribute_set.values_list("allocation_attribute_type__name", "value"))


def test_a_resource_without_a_blueprint_gets_nothing(make_allocation, storage_resource):
    allocation = make_allocation(storage_resource)

    result = apply_blueprint(allocation.pk)

    assert result["created_attributes"] == []
    assert "No allocation blueprint" in result["message"]
    assert attribute_values(allocation) == {}


def test_an_allocation_without_a_resource_gets_nothing(make_allocation):
    allocation = make_allocation()

    result = apply_blueprint(allocation.pk)

    assert result["created_attributes"] == []
    assert attribute_values(allocation) == {}


def test_the_blueprints_attributes_are_created_with_placeholders_filled_in(
    make_allocation, storage_resource, make_blueprint, make_project_attribute
):
    make_project_attribute("Group", "smithlab")
    make_blueprint(
        storage_resource,
        {"Storage Quota (TB)": "1", "Storage Path": "/cluster/tufts/{project.Group}", "Notes": ""},
    )
    allocation = make_allocation(storage_resource)

    result = apply_blueprint(allocation.pk)

    assert sorted(result["created_attributes"]) == ["Notes", "Storage Path", "Storage Quota (TB)"]
    assert attribute_values(allocation) == {
        "Storage Quota (TB)": "1",
        "Storage Path": "/cluster/tufts/smithlab",
        "Notes": "",
    }


def test_an_attribute_the_allocation_already_has_is_left_alone(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1", "Notes": "none"})
    allocation = make_allocation(storage_resource)
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("Storage Quota (TB)"), value="5"
    )

    result = apply_blueprint(allocation.pk)

    assert result["created_attributes"] == ["Notes"]
    assert attribute_values(allocation) == {"Storage Quota (TB)": "5", "Notes": "none"}


def test_a_bad_placeholder_skips_that_attribute_and_reports_it(make_allocation, storage_resource, make_blueprint):
    make_blueprint(storage_resource, {"Storage Path": "/cluster/tufts/{project.Group}", "Storage Quota (TB)": "1"})
    allocation = make_allocation(storage_resource)

    result = apply_blueprint(allocation.pk)

    assert result["created_attributes"] == ["Storage Quota (TB)"]
    assert list(result["failed_attributes"]) == ["Storage Path"]
    assert "Group" in result["failed_attributes"]["Storage Path"]
    assert attribute_values(allocation) == {"Storage Quota (TB)": "1"}
