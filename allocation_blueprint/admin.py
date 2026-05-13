from django.contrib import admin
from .models import AllocationAttributeBlueprint, AllocationBlueprint


@admin.register(AllocationBlueprint)
class AllocationBlueprintAdmin(admin.ModelAdmin):
    list_display = ['resource']
    search_fields = ['resource__name']
    ordering = ['resource']


@admin.register(AllocationAttributeBlueprint)
class AllocationAttributeBlueprintAdmin(admin.ModelAdmin):
    list_display = ['blueprint', 'allocation_attribute_type', 'value']
    search_fields = ['blueprint__resource__name', 'allocation_attribute_type__name', 'value']
    ordering = ['blueprint__resource__name', 'allocation_attribute_type', 'value']
