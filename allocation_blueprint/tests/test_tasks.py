"""apply_blueprint gives a new allocation its resource's blueprint attributes; check_blueprint_attributes
checks existing allocations against their blueprints."""

import pytest

from allocation_blueprint.tasks import (
    BlueprintValueError,
    apply_blueprint,
    check_blueprint_attributes,
    report_blueprint_differences,
)


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


def test_check_leaves_a_value_that_differs_only_in_case_alone(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    """A mixed-case path names a share that exists: lowercasing it would point the allocation elsewhere."""
    make_blueprint(storage_resource, {"vast_path": "/smb/smithlab"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("vast_path"), value="/smb/SmithLab"
    )

    result = check_blueprint_attributes()

    assert result["mismatches"] == []
    assert [entry["attribute"] for entry in result["case_differences"]] == ["vast_path"]
    assert attribute_values(allocation) == {"vast_path": "/smb/SmithLab"}


def test_check_doesnt_create_attributes_on_an_allocation_that_differs_in_case(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    """Its share's name isn't the blueprint's, so a value made from the blueprint could name the wrong share.
    The missing attribute comes before the one that differs, so the check has to see the whole allocation first."""
    make_blueprint(storage_resource, {"vast_path": "/smb/smithlab", "sf_vol_path": "rstore-cifs:smithlab"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("sf_vol_path"), value="rstore-cifs:SmithLab"
    )

    result = check_blueprint_attributes()

    assert result["created"] == []
    assert [(entry["allocation"], entry["attribute"]) for entry in result["not_created"]] == [
        (allocation.pk, "vast_path")
    ]
    assert "1 not created" in result["message"]
    assert attribute_values(allocation) == {"sf_vol_path": "rstore-cifs:SmithLab"}


def test_check_still_creates_attributes_on_other_allocations(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    make_blueprint(storage_resource, {"vast_path": "/smb/smithlab", "sf_vol_path": "rstore-cifs:smithlab"})
    differs = make_allocation(storage_resource, status="Active")
    differs.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("sf_vol_path"), value="rstore-cifs:SmithLab"
    )
    follows = make_allocation(storage_resource, status="Active")

    result = check_blueprint_attributes()

    assert {entry["allocation"] for entry in result["created"]} == {follows.pk}
    assert attribute_values(follows) == {"vast_path": "/smb/smithlab", "sf_vol_path": "rstore-cifs:smithlab"}


def test_check_still_creates_attributes_on_an_allocation_with_an_ordinary_mismatch(
    make_allocation, storage_resource, make_blueprint, make_project_attribute, make_attribute_type
):
    """Only a difference in case says the allocation's names aren't the blueprint's; a changed quota doesn't."""
    make_project_attribute("Group", "smithlab")
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1", "Storage Path": "/cluster/tufts/{project.Group}"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("Storage Quota (TB)"), value="5"
    )

    result = check_blueprint_attributes()

    assert [entry["attribute"] for entry in result["created"]] == ["Storage Path"]
    assert result["not_created"] == []


# report_blueprint_differences


def test_report_lists_what_would_be_created_without_creating_it(
    make_allocation, storage_resource, make_blueprint, make_project_attribute
):
    make_project_attribute("Group", "smithlab")
    make_blueprint(storage_resource, {"Storage Path": "/cluster/tufts/{project.Group}", "Notes": ""})
    allocation = make_allocation(storage_resource, status="Active")

    result = report_blueprint_differences()

    assert result["checked"] == 1
    assert result["missing"] == [
        {"allocation": allocation.pk, "attribute": "Storage Path", "value": "/cluster/tufts/smithlab"},
        {"allocation": allocation.pk, "attribute": "Notes", "value": ""},
    ]
    assert attribute_values(allocation) == {}


def test_report_lists_values_that_differ_only_in_case_apart_from_mismatches(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    """Older shares can be mixed case while keys are lowercase: expected, so kept out of the mismatches."""
    make_blueprint(storage_resource, {"vast_path": "/smb/smithlab"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("vast_path"), value="/smb/SmithLab"
    )

    result = report_blueprint_differences()

    assert result["missing"] == []
    assert result["mismatches"] == []
    assert result["case_differences"] == [
        {"allocation": allocation.pk, "attribute": "vast_path", "expected": "/smb/smithlab", "actual": "/smb/SmithLab"}
    ]
    assert "1 differing only in case" in result["message"]
    assert attribute_values(allocation) == {"vast_path": "/smb/SmithLab"}


def test_report_lists_what_it_wouldnt_create_on_an_allocation_that_differs_in_case(
    make_allocation, storage_resource, make_blueprint, make_attribute_type
):
    make_blueprint(storage_resource, {"sf_vol_path": "rstore-cifs:smithlab", "vast_path": "/smb/smithlab"})
    allocation = make_allocation(storage_resource, status="Active")
    allocation.allocationattribute_set.create(
        allocation_attribute_type=make_attribute_type("sf_vol_path"), value="rstore-cifs:SmithLab"
    )

    result = report_blueprint_differences()

    assert result["missing"] == []
    [entry] = result["not_created"]
    assert entry["allocation"] == allocation.pk
    assert entry["attribute"] == "vast_path"
    assert entry["value"] == "/smb/smithlab"
    assert "sf_vol_path" in entry["reason"]


def test_report_checks_only_active_allocations_with_a_blueprint(
    make_allocation, storage_resource, make_resource, make_blueprint
):
    make_blueprint(storage_resource, {"Storage Quota (TB)": "1"})
    active = make_allocation(storage_resource, status="Active")
    make_allocation(storage_resource, status="Expired")
    make_allocation(make_resource("cluster", "Cluster"), status="Active")

    result = report_blueprint_differences()

    assert result["checked"] == 1
    assert [entry["allocation"] for entry in result["missing"]] == [active.pk]


def test_report_lists_a_bad_placeholder(make_allocation, storage_resource, make_blueprint):
    make_blueprint(storage_resource, {"Storage Path": "/cluster/tufts/{project.Group}"})
    allocation = make_allocation(storage_resource, status="Active")

    result = report_blueprint_differences()

    assert [(entry["allocation"], entry["attribute"]) for entry in result["failed"]] == [
        (allocation.pk, "Storage Path")
    ]
    assert result["missing"] == []
