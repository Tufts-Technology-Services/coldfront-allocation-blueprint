"""apply_blueprint gives a new allocation its resource's blueprint attributes; check_blueprint_attributes
checks existing allocations against their blueprints."""

import pytest

from allocation_blueprint.tasks import BlueprintValueError, apply_blueprint, check_blueprint_attributes


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


def test_a_bad_placeholder_fails_the_task_after_creating_the_others(make_allocation, storage_resource, make_blueprint):
    make_blueprint(storage_resource, {"Storage Path": "/cluster/tufts/{project.Group}", "Storage Quota (TB)": "1"})
    allocation = make_allocation(storage_resource)

    with pytest.raises(BlueprintValueError) as raised:
        apply_blueprint(allocation.pk)

    # names the attribute it couldn't fill in and why, and what it did create
    assert "Storage Path" in str(raised.value)
    assert "Group" in str(raised.value)
    assert "Storage Quota (TB)" in str(raised.value)
    assert attribute_values(allocation) == {"Storage Quota (TB)": "1"}


# check_blueprint_attributes


def test_check_creates_missing_attributes_with_placeholders_filled_in(
    make_allocation, storage_resource, make_blueprint, make_project_attribute, make_attribute_type
):
    make_project_attribute("Group", "smithlab")
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1", "Storage Path": "/cluster/tufts/{project.Group}"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("Storage Quota (TB)"), value="1"
    )

    result = check_blueprint_attributes()

    assert result["checked"] == 1
    assert result["created"] == [
        {"allocation": allocation.pk, "attribute": "Storage Path", "value": "/cluster/tufts/smithlab"}
    ]
    assert result["mismatches"] == []
    assert result["failed"] == []
    assert attribute_values(allocation) == {"Storage Quota (TB)": "1", "Storage Path": "/cluster/tufts/smithlab"}


def test_check_reports_a_mismatch_and_leaves_the_value_alone(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("Storage Quota (TB)"), value="5"
    )

    result = check_blueprint_attributes()

    assert result["created"] == []
    assert result["mismatches"] == [
        {"allocation": allocation.pk, "attribute": "Storage Quota (TB)", "expected": "1", "actual": "5"}
    ]
    assert attribute_values(allocation) == {"Storage Quota (TB)": "5"}


def test_check_compares_against_the_filled_in_placeholder(
    make_allocation, storage_resource, make_blueprint, make_project_attribute, make_attribute_type
):
    make_project_attribute("Group", "smithlab")
    make_blueprint(storage_resource, {"Storage Path": "/cluster/tufts/{project.Group}"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("Storage Path"), value="/cluster/tufts/smithlab"
    )

    result = check_blueprint_attributes()

    assert result["created"] == []
    assert result["mismatches"] == []


def test_check_never_reports_a_mismatch_for_an_attribute_with_no_initial_value(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    make_blueprint(storage_resource, {"Notes": ""})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(allocation_attribute_type=make_attribute_type("Notes"), value="hello")

    result = check_blueprint_attributes()

    assert result["mismatches"] == []
    assert attribute_values(allocation) == {"Notes": "hello"}


def test_check_skips_allocations_whose_resource_has_no_blueprint(
    make_allocation, storage_resource, make_resource, make_blueprint
):
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1"})
    covered = make_allocation(storage_resource, status="Active")
    uncovered = make_allocation(make_resource("cluster", "Cluster"), status="Active")
    no_resource = make_allocation(status="Active")

    result = check_blueprint_attributes()

    assert result["checked"] == 1
    assert [entry["allocation"] for entry in result["created"]] == [covered.pk]
    assert attribute_values(uncovered) == {}
    assert attribute_values(no_resource) == {}


def test_check_skips_allocations_that_arent_active(make_allocation, storage_resource, make_blueprint):
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1"})
    active = make_allocation(storage_resource, status="Active")
    others = [make_allocation(storage_resource, status=status) for status in ("New", "Expired", "Denied")]

    result = check_blueprint_attributes()

    assert result["checked"] == 1
    assert [entry["allocation"] for entry in result["created"]] == [active.pk]
    assert all(attribute_values(allocation) == {} for allocation in others)


def test_check_reports_a_bad_placeholder_and_carries_on(make_allocation, storage_resource, make_blueprint):
    make_blueprint(storage_resource, {"Storage Path": "/cluster/tufts/{project.Group}", "Storage Quota (TB)": "1"})
    first = make_allocation(storage_resource, status="Active")
    second = make_allocation(storage_resource, status="Active")

    result = check_blueprint_attributes()

    assert [(entry["allocation"], entry["attribute"]) for entry in result["failed"]] == [
        (first.pk, "Storage Path"),
        (second.pk, "Storage Path"),
    ]
    assert "Group" in result["failed"][0]["reason"]
    assert attribute_values(first) == {"Storage Quota (TB)": "1"}
    assert attribute_values(second) == {"Storage Quota (TB)": "1"}
