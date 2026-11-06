"""The staff page showing which attributes each resource's new allocations get, by resource type."""

import pytest
from django.contrib.auth.models import User
from django.urls import NoReverseMatch, reverse


@pytest.fixture
def staff_client(client, db):
    client.force_login(User.objects.create_user("staff", "staff@example.com", "secret", is_staff=True))
    return client


def page_text(response):
    """The page's blueprints section: the navbar and footer could mention resource types too."""
    html = response.content.decode()
    return html[html.index('id="allocation-blueprints"') :]


def test_someone_not_logged_in_is_sent_to_log_in(client, db):
    response = client.get(reverse("blueprint_list"))

    assert response.status_code == 302
    assert "login" in response.url


def test_a_user_who_isnt_staff_is_refused(client, db):
    client.force_login(User.objects.create_user("user", "user@example.com", "secret"))

    response = client.get(reverse("blueprint_list"))

    assert response.status_code == 403


def test_staff_see_each_resource_types_blueprints(staff_client, make_resource, make_blueprint):
    make_blueprint(
        make_resource("hpc-storage", "Storage"),
        {"Storage Quota (TB)": "1", "Storage Path": "/cluster/tufts/{project.Group}", "Notes": ""},
    )
    make_blueprint(make_resource("hpc-cluster", "Cluster"), {"Slurm Account": "{project.Group}"})

    response = staff_client.get(reverse("blueprint_list"))

    assert response.status_code == 200
    text = page_text(response)
    for expected in ["hpc-storage", "Storage Quota (TB)", "/cluster/tufts/{project.Group}", "(empty)"]:
        assert expected in text
    # resource types in name order, each with its resources' blueprints
    assert text.index("Cluster") < text.index("hpc-cluster") < text.index("Storage") < text.index("hpc-storage")
    # a resource's attributes in name order
    assert text.index("Notes") < text.index("Storage Path") < text.index("Storage Quota (TB)")


def test_with_no_blueprints_the_page_says_so(staff_client):
    response = staff_client.get(reverse("blueprint_list"))

    assert "There are no allocation blueprints to display." in page_text(response)


def test_only_someone_who_can_change_blueprints_gets_a_link_to_edit_them(
    client, staff_client, make_resource, make_blueprint
):
    blueprint = make_blueprint(make_resource("hpc-storage"), {"Storage Quota (TB)": "1"})
    edit_link = reverse("admin:allocation_blueprint_allocationblueprint_change", args=[blueprint.pk])

    assert edit_link not in page_text(staff_client.get(reverse("blueprint_list")))

    client.force_login(User.objects.create_superuser("admin", "admin@example.com", "secret"))
    assert edit_link in page_text(client.get(reverse("blueprint_list")))


@pytest.mark.parametrize("name", ["blueprint_detail", "blueprint_create", "blueprint_update", "blueprint_delete"])
def test_the_other_blueprint_pages_are_gone(name):
    with pytest.raises(NoReverseMatch):
        reverse(name, args=[1])
