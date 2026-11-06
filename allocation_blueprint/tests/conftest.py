import pytest
from django.contrib.auth.models import User

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttributeType,
    AllocationStatusChoice,
    AttributeType,
)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import AttributeType as ProjectAttributeTypeBase
from coldfront.core.project.models import Project, ProjectAttribute, ProjectAttributeType, ProjectStatusChoice
from coldfront.core.resource.models import Resource, ResourceType

from allocation_blueprint.models import AllocationBlueprint


@pytest.fixture
def project(db):
    return Project.objects.create(
        title="Smith Lab",
        pi=User.objects.create_user("pi", "pi@example.com", "secret"),
        description="a project used by the tests",
        field_of_science=FieldOfScience.objects.get_or_create(description="Other")[0],
        status=ProjectStatusChoice.objects.get_or_create(name="Active")[0],
    )


@pytest.fixture
def storage_resource(db):
    return Resource.objects.create(
        resource_type=ResourceType.objects.get_or_create(name="Storage", description="storage")[0],
        name="hpc-storage",
        description="a storage resource",
    )


@pytest.fixture
def make_allocation(project):
    """An allocation of the project, on the given resources (none if not given)."""

    def _make(*resources):
        allocation = Allocation.objects.create(
            project=project,
            status=AllocationStatusChoice.objects.get_or_create(name="New")[0],
            justification="because",
        )
        allocation.resources.add(*resources)
        return allocation

    return _make


@pytest.fixture
def make_attribute_type(db):
    """Get or create an allocation attribute type of attribute type Text, by name."""

    def _make(name):
        return AllocationAttributeType.objects.get_or_create(
            name=name, defaults={"attribute_type": AttributeType.objects.get_or_create(name="Text")[0]}
        )[0]

    return _make


@pytest.fixture
def make_project_attribute(project):
    """Give the project an attribute, creating its type if needed."""

    def _make(name, value):
        return ProjectAttribute.objects.create(
            proj_attr_type=ProjectAttributeType.objects.get_or_create(
                name=name, defaults={"attribute_type": ProjectAttributeTypeBase.objects.get_or_create(name="Text")[0]}
            )[0],
            project=project,
            value=value,
        )

    return _make


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


@pytest.fixture
def make_resource(db):
    """A resource of the named resource type."""

    def _make(name, type_name="Storage"):
        return Resource.objects.create(
            resource_type=ResourceType.objects.get_or_create(name=type_name, description=type_name)[0],
            name=name,
            description="a resource",
        )

    return _make
