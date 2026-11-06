"""Test URLconf: ColdFront's own URLs plus the plugin's, mounted where the deployment mounts them."""

from django.urls import include, path

from coldfront.config.urls import urlpatterns

urlpatterns = [*urlpatterns, path("blueprint/", include("allocation_blueprint.urls"))]
