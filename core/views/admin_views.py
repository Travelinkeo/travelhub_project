# core/views/admin_views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import SaaSMixin
from core.models import CronApiKey, FeatureFlag

# --- Vistas para FeatureFlag ---


class FeatureFlagListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = FeatureFlag
    template_name = "core/admin/featureflag_list.html"
    context_object_name = "feature_flags"
    paginate_by = 30

    def get_queryset(self):
        q = self.request.GET.get("q")
        queryset = FeatureFlag.objects.select_related("agencia").order_by("nombre")
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(description__icontains=q))
        return queryset


class FeatureFlagCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = FeatureFlag
    template_name = "core/admin/featureflag_form.html"
    fields = ["nombre", "description", "enabled", "rollout_percentage", "agencia"]
    success_url = reverse_lazy("core_admin:featureflag_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            if field.widget.input_type == "checkbox":
                field.widget.attrs["class"] = (
                    "h-5 w-5 rounded border-border-color text-primary focus:ring-primary"
                )
            else:
                field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Feature Flag creada exitosamente.")
        return super().form_valid(form)


class FeatureFlagUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = FeatureFlag
    template_name = "core/admin/featureflag_form.html"
    fields = ["nombre", "description", "enabled", "rollout_percentage", "agencia"]
    success_url = reverse_lazy("core_admin:featureflag_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            if field.widget.input_type == "checkbox":
                field.widget.attrs["class"] = (
                    "h-5 w-5 rounded border-border-color text-primary focus:ring-primary"
                )
            else:
                field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Feature Flag actualizada exitosamente.")
        return super().form_valid(form)


class FeatureFlagDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = FeatureFlag
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("core_admin:featureflag_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Feature Flag"
        context["object_instance"] = self.object.nombre
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Feature Flag eliminada correctamente.")
        return super().delete(request, *args, **kwargs)


# --- Vistas para CronApiKey ---


class CronApiKeyListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = CronApiKey
    template_name = "core/admin/cronapikey_list.html"
    context_object_name = "cron_api_keys"
    paginate_by = 30

    def get_queryset(self):
        q = self.request.GET.get("q")
        queryset = CronApiKey.objects.select_related("agencia").order_by("name")
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(prefix__icontains=q))
        return queryset


class CronApiKeyCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = CronApiKey
    template_name = "core/admin/cronapikey_form.html"
    fields = ["name", "agencia", "is_active", "expires_at"]
    success_url = reverse_lazy("core_admin:cronapikey_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            if field.widget.input_type == "checkbox":
                field.widget.attrs["class"] = (
                    "h-5 w-5 rounded border-border-color text-primary focus:ring-primary"
                )
            else:
                field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Cron API Key creada exitosamente.")
        return super().form_valid(form)


class CronApiKeyUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = CronApiKey
    template_name = "core/admin/cronapikey_form.html"
    fields = ["name", "agencia", "is_active", "expires_at"]
    success_url = reverse_lazy("core_admin:cronapikey_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            if field.widget.input_type == "checkbox":
                field.widget.attrs["class"] = (
                    "h-5 w-5 rounded border-border-color text-primary focus:ring-primary"
                )
            else:
                field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Cron API Key actualizada exitosamente.")
        return super().form_valid(form)


class CronApiKeyDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = CronApiKey
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("core_admin:cronapikey_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Cron API Key"
        context["object_instance"] = self.object.name
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Cron API Key eliminada correctamente.")
        return super().delete(request, *args, **kwargs)
