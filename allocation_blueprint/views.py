from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from .models import AllocationBlueprint
from .forms import AllocationBlueprintForm


class AllocationBlueprintListView(ListView):
    model = AllocationBlueprint
    template_name = 'allocation_blueprint/allocationblueprint_list.html'
    context_object_name = 'allocation_blueprints'


class AllocationBlueprintDetailView(DetailView):
    model = AllocationBlueprint
    template_name = 'allocation_blueprint/allocationblueprint_detail.html'
    context_object_name = 'allocation_blueprint'


class AllocationBlueprintCreateView(View):
    def get(self, request):
        form = AllocationBlueprintForm()
        return render(request, 'allocation_blueprint/allocationblueprint_form.html', {'form': form})

    def post(self, request):
        form = AllocationBlueprintForm(request.POST)
        if form.is_valid():
            allocation_blueprint = form.save()
            return redirect(reverse('allocation_blueprint_detail', args=[allocation_blueprint.pk]))
        return render(request, 'allocation_blueprint/allocationblueprint_form.html', {'form': form})


class AllocationBlueprintUpdateView(View):
    def get(self, request, pk):
        allocation_blueprint = get_object_or_404(AllocationBlueprint, pk=pk)
        form = AllocationBlueprintForm(instance=allocation_blueprint)
        return render(request, 'allocation_blueprint/allocationblueprint_form.html', {'form': form})

    def post(self, request, pk):
        allocation_blueprint = get_object_or_404(AllocationBlueprint, pk=pk)
        form = AllocationBlueprintForm(request.POST, instance=allocation_blueprint)
        if form.is_valid():
            allocation_blueprint = form.save()
            return redirect(reverse('allocation_blueprint_detail', args=[allocation_blueprint.pk]))
        return render(request, 'allocation_blueprint/allocationblueprint_form.html', {'form': form})


class AllocationBlueprintDeleteView(View):
    def get(self, request, pk):
        allocation_blueprint = get_object_or_404(AllocationBlueprint, pk=pk)
        return render(request, 'allocation_blueprint/allocationblueprint_confirm_delete.html', {'allocation_blueprint': allocation_blueprint})

    def post(self, request, pk):
        allocation_blueprint = get_object_or_404(AllocationBlueprint, pk=pk)
        allocation_blueprint.delete()
        return redirect(reverse('allocation_blueprint_list'))