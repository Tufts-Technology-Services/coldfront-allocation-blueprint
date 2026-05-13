from django.db import models

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.resource.models import Resource


class AllocationAttributeBlueprint(models.Model):
    """
    This model represents a blueprint for an allocation attribute, which defines the type of the attribute and an initial value.
    
    """
    blueprint = models.ForeignKey('AllocationBlueprint', on_delete=models.CASCADE)
    allocation_attribute_type = models.ForeignKey(AllocationAttributeType, on_delete=models.CASCADE)
    value = models.CharField(max_length=255, blank=True, null=True, verbose_name="Initial value")

    def __str__(self):
        return f"{self.allocation_attribute_type.name}: {self.value}"
    

class AllocationBlueprint(models.Model):
    """
    This model represents a blueprint for an allocation of a resource. when a resource is created, an allocation blueprint can be 
    associated with it to specify the attributes that should be automatically created for any allocations of that resource.
    """
    resource = models.OneToOneField(Resource, on_delete=models.CASCADE)

    def __str__(self):
        return f"Allocation blueprint for resource: {self.resource.name}"