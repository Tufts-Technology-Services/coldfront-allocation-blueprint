"""A blueprint and its attributes are edited together, on the blueprint's admin page."""

from django.contrib import admin
from django.urls import reverse

from coldfront.core.allocation.models import AllocationAttributeType, AttributeType
from coldfront.core.resource.models import Resource, ResourceType

from allocation_blueprint.models import AllocationAttributeBlueprint, AllocationBlueprint

INLINE_PREFIX = "allocationattributeblueprint_set"


def make_resource(name):
    return Resource.objects.create(
        resource_type=ResourceType.objects.get_or_create(name="Storage", description="storage")[0],
        name=name,
        description="a resource",
    )


def make_attribute_type(name):
    return AllocationAttributeType.objects.create(
        name=name, attribute_type=AttributeType.objects.get_or_create(name="Text")[0]
    )


def inline_management_form(total, initial=0):
    return {
        f"{INLINE_PREFIX}-TOTAL_FORMS": str(total),
        f"{INLINE_PREFIX}-INITIAL_FORMS": str(initial),
        f"{INLINE_PREFIX}-MIN_NUM_FORMS": "0",
        f"{INLINE_PREFIX}-MAX_NUM_FORMS": "1000",
    }


def test_attribute_blueprints_have_no_admin_page_of_their_own():
    assert not admin.site.is_registered(AllocationAttributeBlueprint)


def test_a_blueprints_page_shows_its_attributes(admin_client):
    blueprint = AllocationBlueprint.objects.create(resource=make_resource("hpc-storage"))
    quota = make_attribute_type("Storage Quota (TB)")
    blueprint.allocationattributeblueprint_set.create(allocation_attribute_type=quota, value="1")

    response = admin_client.get(reverse("admin:allocation_blueprint_allocationblueprint_change", args=[blueprint.pk]))

    assert response.status_code == 200
    formset = response.context["inline_admin_formsets"][0].formset
    assert formset.model is AllocationAttributeBlueprint
    assert [form.instance.value for form in formset.initial_forms] == ["1"]


def test_adding_a_blueprint_adds_its_attributes_too(admin_client):
    resource = make_resource("hpc-storage")
    quota = make_attribute_type("Storage Quota (TB)")
    path = make_attribute_type("Storage Path")

    response = admin_client.post(
        reverse("admin:allocation_blueprint_allocationblueprint_add"),
        {
            "resource": resource.pk,
            **inline_management_form(total=2),
            f"{INLINE_PREFIX}-0-allocation_attribute_type": quota.pk,
            f"{INLINE_PREFIX}-0-value": "1",
            f"{INLINE_PREFIX}-1-allocation_attribute_type": path.pk,
            f"{INLINE_PREFIX}-1-value": "/cluster/tufts/{project.Group}",
        },
    )

    assert response.status_code == 302
    blueprint = AllocationBlueprint.objects.get(resource=resource)
    assert sorted(
        blueprint.allocationattributeblueprint_set.values_list("allocation_attribute_type__name", "value")
    ) == [("Storage Path", "/cluster/tufts/{project.Group}"), ("Storage Quota (TB)", "1")]


def test_the_blueprint_list_shows_each_blueprints_attributes(admin_client):
    blueprint = AllocationBlueprint.objects.create(resource=make_resource("hpc-storage"))
    blueprint.allocationattributeblueprint_set.create(
        allocation_attribute_type=make_attribute_type("Storage Quota (TB)"), value="1"
    )

    response = admin_client.get(reverse("admin:allocation_blueprint_allocationblueprint_changelist"))

    assert response.status_code == 200
    assert "Storage Quota (TB): 1" in response.content.decode()


def test_the_blueprint_list_marks_an_attribute_with_no_initial_value(admin_client):
    blueprint = AllocationBlueprint.objects.create(resource=make_resource("hpc-storage"))
    blueprint.allocationattributeblueprint_set.create(allocation_attribute_type=make_attribute_type("Notes"), value="")
    blueprint.allocationattributeblueprint_set.create(
        allocation_attribute_type=make_attribute_type("Owner"), value=None
    )

    response = admin_client.get(reverse("admin:allocation_blueprint_allocationblueprint_changelist"))

    assert "Notes: (empty), Owner: (empty)" in response.content.decode()


def test_the_admin_section_is_called_allocation_blueprints(admin_client):
    response = admin_client.get(reverse("admin:index"))

    assert "Allocation Blueprints" in response.content.decode()
    assert "Allocation_Blueprint" not in response.content.decode()
