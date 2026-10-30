"""Root URL table: like an Express app mounting routers, or Spring @RequestMapping prefixes."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/", include("accounts.urls")),  # auth/..., users/...
    path("api/", include("tickets.urls")),  # tickets/...
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
