from django.urls import path
from . import views


urlpatterns = [
    path('', views.AllocationBlueprintListView.as_view(), name='blueprint_list'),
    path('<int:pk>/', views.AllocationBlueprintDetailView.as_view(), name='blueprint_detail'),
    path('create/', views.AllocationBlueprintCreateView.as_view(), name='blueprint_create'),
    path('update/<int:pk>/', views.AllocationBlueprintUpdateView.as_view(), name='blueprint_update'),
    path('delete/<int:pk>/', views.AllocationBlueprintDeleteView.as_view(), name='blueprint_delete'),
]