from django.contrib import admin

from .models import AllocationAttributeBlueprint, AllocationBlueprint


class AllocationAttributeBlueprintInline(admin.TabularInline):
    """A blueprint's attributes, edited on the blueprint's own page rather than a page of their own."""

    model = AllocationAttributeBlueprint
    fields = ["allocation_attribute_type", "value"]
    ordering = ["allocation_attribute_type__name"]
    extra = 1


@admin.register(AllocationBlueprint)
class AllocationBlueprintAdmin(admin.ModelAdmin):
    list_display = ["resource", "attribute_summary"]
    search_fields = ["resource__name", "allocationattributeblueprint__allocation_attribute_type__name"]
    ordering = ["resource__name"]
    inlines = [AllocationAttributeBlueprintInline]

    def get_queryset(self, request):
        # the list shows every blueprint's attributes: fetch them all at once, not once per row
        return (
            super()
            .get_queryset(request)
            .select_related("resource")
            .prefetch_related("allocationattributeblueprint_set__allocation_attribute_type")
        )

    @admin.display(description="Attributes")
    def attribute_summary(self, blueprint):
        """Each attribute as "<type>: <initial value>", in name order, comma-separated.

        An attribute with no initial value shows "(empty)", rather than nothing or "None".
        """
        attribute_blueprints = sorted(
            blueprint.allocationattributeblueprint_set.all(),
            key=lambda attribute_blueprint: attribute_blueprint.allocation_attribute_type.name,
        )
        return ", ".join(
            f"{attribute_blueprint.allocation_attribute_type.name}: {attribute_blueprint.value or '(empty)'}"
            for attribute_blueprint in attribute_blueprints
        )
