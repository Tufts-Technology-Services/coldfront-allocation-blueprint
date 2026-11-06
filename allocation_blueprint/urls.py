from django.urls import path

from . import views

urlpatterns = [
    path("", views.AllocationBlueprintListView.as_view(), name="blueprint_list"),
]
