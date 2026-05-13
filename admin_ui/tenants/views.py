import json
from functools import wraps

import yaml
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from .db import Config, Tenant, User, ensure_setup, get_session, load_config_yaml, verify_password
from .forms import LoginForm

ensure_setup()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect(reverse("login"))
        request.user_data = user
        return view_func(request, *args, **kwargs)

    return wrapper


def get_current_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role.name,
            "tenant_id": user.tenant_id,
        }
    finally:
        session.close()


def home(request):
    user = get_current_user(request)
    if not user:
        return redirect(reverse("login"))
    if user["role"] == "admin":
        return redirect(reverse("tenant_list"))
    if user["role"] == "tenant" and user["tenant_id"]:
        return redirect(reverse("tenant_detail", args=[user["tenant_id"]]))
    return redirect(reverse("login"))


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]
            session = get_session()
            try:
                user = session.query(User).filter_by(username=username).first()
                if user and verify_password(password, user.password_hash):
                    request.session["user_id"] = user.id
                    request.session["user_role"] = user.role.name
                    if user.role.name == "admin":
                        return redirect(reverse("tenant_list"))
                    if user.role.name == "tenant" and user.tenant_id:
                        return redirect(reverse("tenant_detail", args=[user.tenant_id]))
                    messages.error(request, "Tenant login does not have an assigned tenant.")
                else:
                    messages.error(request, "Invalid username or password.")
            finally:
                session.close()
    else:
        form = LoginForm()
    return render(request, "tenants/login.html", {"form": form})


def logout_view(request):
    request.session.flush()
    return redirect(reverse("login"))


def _load_tenant(request, tenant_id):
    session = get_session()
    try:
        tenant = session.query(Tenant).filter_by(id=tenant_id).first()
        return tenant
    finally:
        session.close()


def _authorize_tenant_access(request, tenant_id):
    user = get_current_user(request)
    if not user:
        return None, redirect(reverse("login"))
    if user["role"] == "admin":
        return _load_tenant(request, tenant_id), None
    if user["role"] == "tenant" and user["tenant_id"] == tenant_id:
        return _load_tenant(request, tenant_id), None
    messages.error(request, "You do not have permission to view this tenant.")
    return None, redirect(reverse("home"))


@login_required
def tenant_list(request):
    if request.user_data["role"] != "admin":
        messages.error(request, "Only admin users can view all tenants.")
        return redirect(reverse("home"))

    session = get_session()
    try:
        tenants = session.query(Tenant).order_by(Tenant.name).all()
        tenant_data = [
            {"id": t.id, "name": t.name, "slug": t.slug, "description": t.description or ""}
            for t in tenants
        ]
    finally:
        session.close()

    return render(request, "tenants/tenant_list.html", {"tenants": tenant_data, "user": request.user_data})


def _render_tenant_page(request, tenant, active_menu, content_title, content_body, config_sections=None, selected_section=None):
    return render(
        request,
        "tenants/tenant_dashboard.html",
        {
            "tenant": tenant,
            "user": request.user_data,
            "active_menu": active_menu,
            "content_title": content_title,
            "content_body": content_body,
            "config_sections": config_sections or [],
            "selected_section": selected_section,
        },
    )


@login_required
def tenant_detail(request, tenant_id):
    tenant, error = _authorize_tenant_access(request, tenant_id)
    if error:
        return error
    return redirect(reverse("tenant_config", args=[tenant_id]))


@login_required
def tenant_config(request, tenant_id):
    tenant, error = _authorize_tenant_access(request, tenant_id)
    if error:
        return error

    session = get_session()
    try:
        configs = (
            session.query(Config).filter_by(tenant_id=tenant_id).order_by(Config.section).all()
        )
        sections = [c.section for c in configs]
        selected_section = request.GET.get("tab", sections[0] if sections else "Source")
        current_config = next((c for c in configs if c.section == selected_section), None)
        content_body = "No configuration data available."
        if current_config:
            try:
                parsed = json.loads(current_config.data)
                content_body = yaml.safe_dump(parsed, sort_keys=False, allow_unicode=True)
            except Exception:
                content_body = current_config.data
    finally:
        session.close()

    return _render_tenant_page(
        request,
        tenant,
        active_menu="config",
        content_title=f"Config: {selected_section}",
        content_body=content_body,
        config_sections=sections,
        selected_section=selected_section,
    )


@login_required
def tenant_unstructured(request, tenant_id):
    tenant, error = _authorize_tenant_access(request, tenant_id)
    if error:
        return error
    return _render_tenant_page(
        request,
        tenant,
        active_menu="unstructured",
        content_title="Unstructured Data",
        content_body="This page is a placeholder for unstructured data exploration and upload.",
    )


@login_required
def tenant_structured(request, tenant_id):
    tenant, error = _authorize_tenant_access(request, tenant_id)
    if error:
        return error
    return _render_tenant_page(
        request,
        tenant,
        active_menu="structured",
        content_title="Structured Data",
        content_body="This page is a placeholder for structured data definitions and dataset mappings.",
    )


@login_required
def tenant_retrieval(request, tenant_id):
    tenant, error = _authorize_tenant_access(request, tenant_id)
    if error:
        return error
    return _render_tenant_page(
        request,
        tenant,
        active_menu="retrieval",
        content_title="Retrieval",
        content_body="This page is a placeholder for retrieval and search pipeline controls.",
    )


@login_required
def tenant_logs(request, tenant_id):
    tenant, error = _authorize_tenant_access(request, tenant_id)
    if error:
        return error
    return _render_tenant_page(
        request,
        tenant,
        active_menu="logs",
        content_title="Logs",
        content_body="This page is a placeholder for tenant logs and operational history.",
    )
