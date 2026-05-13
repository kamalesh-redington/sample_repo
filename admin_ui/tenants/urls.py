from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("tenants/", views.tenant_list, name="tenant_list"),
    path("tenant/<int:tenant_id>/", views.tenant_detail, name="tenant_detail"),
    path("tenant/<int:tenant_id>/config/", views.tenant_config, name="tenant_config"),
    path("tenant/<int:tenant_id>/unstructured/", views.tenant_unstructured, name="tenant_unstructured"),
    path("tenant/<int:tenant_id>/structured/", views.tenant_structured, name="tenant_structured"),
    path("tenant/<int:tenant_id>/retrieval/", views.tenant_retrieval, name="tenant_retrieval"),
    path("tenant/<int:tenant_id>/logs/", views.tenant_logs, name="tenant_logs"),
]
