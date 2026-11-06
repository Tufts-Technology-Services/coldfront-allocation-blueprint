from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Prefetch
from django.views.generic import ListView

from .models import AllocationAttributeBlueprint, AllocationBlueprint


class AllocationBlueprintListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """For staff: the attributes each resource's new allocations get, grouped by resource type.

    Read-only. Blueprints are edited in the admin, and the page links there for anyone allowed to.
    """

    template_name = "allocation_blueprint/allocationblueprint_list.html"
    context_object_name = "allocation_blueprints"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        # ordered by resource type, then resource, so the template can group them by type
        return (
            AllocationBlueprint.objects.select_related("resource__resource_type")
            .prefetch_related(
                Prefetch(
                    "allocationattributeblueprint_set",
                    queryset=AllocationAttributeBlueprint.objects.select_related("allocation_attribute_type").order_by(
                        "allocation_attribute_type__name"
                    ),
                    to_attr="ordered_attribute_blueprints",
                )
            )
            .order_by("resource__resource_type__name", "resource__name")
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "can_edit_blueprints": self.request.user.has_perm("allocation_blueprint.change_allocationblueprint"),
        }
