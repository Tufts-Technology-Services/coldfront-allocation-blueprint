from django import forms
from .models import AllocationBlueprint

class AllocationBlueprintForm(forms.ModelForm):
    class Meta:
        model = AllocationBlueprint
        fields = '__all__'