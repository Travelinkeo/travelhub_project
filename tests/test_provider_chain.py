"""Tests para Provider chain."""
import pytest
from django.core.cache import cache

from apps.automation.providerchain.base import AbstractBaseProvider, ProviderResult
from apps.automation.providerchain.fallback_router import fallback_router
from apps.automation.providerchain.health import get_health_summary, run_health_checks
from apps.automation.providerchain.registry import ProviderRegistry, provider_registry
from apps.automation.providerchain.tracing import get_hourly_metrics, record_call

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# ─── Helper: provider stub ───────────────────────────────────────────────


class OkProvider(AbstractBaseProvider):
    """Ok Provider."""
    provider_name = "test_ok"
    supports_structured_output = True

    def test_connection(self):
        """Connection."""
        return True

    def generate(self, prompt, **kw):
        """Generate."""
        return ProviderResult(
            text="ok response", provider=self.provider_name, model="test-model", success=True
        )


class FailProvider(AbstractBaseProvider):
    """Fail Provider."""
    provider_name = "test_fail"
    supports_structured_output = False

    def test_connection(self):
        """Connection."""
        return False

    def generate(self, prompt, **kw):
        """Generate."""
        return ProviderResult(success=False, error="test error", provider=self.provider_name)


class EmergencyProvider(AbstractBaseProvider):
    """Emergency Provider."""
    provider_name = "test_emergency"
    supports_structured_output = False
    is_emergency_only = True

    def test_connection(self):
        """Connection."""
        return True

    def generate(self, prompt, **kw):
        """Generate."""
        return ProviderResult(
            text="emergency response",
            provider=self.provider_name,
            model="emergency",
            success=True,
        )


# ─── ProviderResult ──────────────────────────────────────────────────────


class TestProviderResult:
    """Test Provider Result."""
    def test_defaults(self):
        """Defaults."""
        r = ProviderResult()
        assert r.text == ""
        assert r.success is True
        assert r.error is None
        assert r.schema_used is False
        assert r.input_tokens == 0

    def test_full_constructor(self):
        """Full constructor."""
        r = ProviderResult(
            text="hello",
            provider="gemini",
            model="gemini-2.5-flash",
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
            success=True,
            schema_used=True,
        )
        assert r.text == "hello"
        assert r.provider == "gemini"
        assert r.input_tokens == 10


class TestAbstractBaseProvider:
    """Test Abstract Base Provider."""
    def test_cannot_instantiate_abstract(self):
        """Cannot instantiate abstract."""
        with pytest.raises(TypeError):
            AbstractBaseProvider()

    def test_concrete_provider(self):
        """Concrete provider."""
        p = OkProvider()
        assert p.provider_name == "test_ok"
        assert p.supports_structured_output is True
        assert p.is_emergency_only is False
        assert p.test_connection() is True

    def test_api_key_status_default(self):
        """Api key status default."""
        p = OkProvider()
        assert p.get_api_key_status() == {"available": False, "last_tested": None}


# ─── ProviderRegistry ────────────────────────────────────────────────────


class TestProviderRegistry:
    """Test Provider Registry."""
    def setup_method(self):
        """Setup method."""
        self.reg = ProviderRegistry()

    def test_register_and_get(self):
        """Register and get."""
        p = OkProvider()
        self.reg.register(p)
        assert self.reg.get("test_ok") is p

    def test_all(self):
        """All."""
        self.reg.register(OkProvider())
        self.reg.register(FailProvider())
        assert len(self.reg.all()) == 2

    def test_fallback_chain_order(self):
        """Fallback chain order."""
        gemini = OkProvider()
        gemini.provider_name = "gemini"
        openai = OkProvider()
        openai.provider_name = "openai"
        deepseek = EmergencyProvider()
        deepseek.provider_name = "deepseek"
        self.reg.register(gemini)
        self.reg.register(openai)
        self.reg.register(deepseek)

        chain = self.reg.fallback_chain(needs_structured=True)
        assert len(chain) == 2
        assert chain[0].provider_name == "gemini"
        assert chain[1].provider_name == "openai"

    def test_fallback_chain_excludes_emergency_for_structured(self):
        """Fallback chain excludes emergency for structured."""
        gemini = OkProvider()
        gemini.provider_name = "gemini"
        deepseek = EmergencyProvider()
        deepseek.provider_name = "deepseek"
        self.reg.register(gemini)
        self.reg.register(deepseek)

        chain = self.reg.fallback_chain(needs_structured=True)
        names = [p.provider_name for p in chain]
        assert "deepseek" not in names

    def test_fallback_chain_includes_emergency_for_text(self):
        """Fallback chain includes emergency for text."""
        gemini = OkProvider()
        gemini.provider_name = "gemini"
        deepseek = EmergencyProvider()
        deepseek.provider_name = "deepseek"
        self.reg.register(gemini)
        self.reg.register(deepseek)

        chain = self.reg.fallback_chain(needs_structured=False)
        names = [p.provider_name for p in chain]
        assert "deepseek" in names

    def test_circuit_breaker(self):
        """Circuit breaker."""
        p = OkProvider()
        self.reg.register(p)
        assert self.reg._circuit_open("test_ok") is False
        self.reg.open_circuit("test_ok")
        assert self.reg._circuit_open("test_ok") is True
        assert len(self.reg.available()) == 0
        self.reg.close_circuit("test_ok")
        assert self.reg._circuit_open("test_ok") is False
        assert len(self.reg.available()) == 1

    def test_available_excludes_circuit_open(self):
        """Available excludes circuit open."""
        p1 = OkProvider()
        p1.provider_name = "p1"
        p2 = OkProvider()
        p2.provider_name = "p2"
        self.reg.register(p1)
        self.reg.register(p2)
        self.reg.open_circuit("p1")
        avail = self.reg.available()
        assert len(avail) == 1
        assert avail[0].provider_name == "p2"


# ─── FallbackRouter ──────────────────────────────────────────────────────


class TestFallbackRouter:
    """Test Fallback Router."""
    def setup_method(self):
        """Setup method."""
        provider_registry._providers.clear()
        cache.clear()

    def _make(self, name, cls=OkProvider, **kw):
        """Make."""
        p = cls()
        p.provider_name = name
        if "supports_structured" in kw:
            p.supports_structured_output = kw["supports_structured"]
        provider_registry.register(p)
        return p

    def test_router_returns_first_ok(self):
        """Router returns first ok."""
        self._make("gemini")
        self._make("openai", cls=FailProvider)

        result = fallback_router.generate("test prompt")
        assert result.success is True
        assert result.provider == "gemini"

    def test_router_falls_back(self):
        """Router falls back."""
        self._make("gemini", cls=FailProvider)
        self._make("openai")

        result = fallback_router.generate("test prompt")
        assert result.success is True
        assert result.provider == "openai"

    def test_router_all_fail(self):
        """Router all fail."""
        self._make("gemini", cls=FailProvider)
        self._make("openai", cls=FailProvider)
        result = fallback_router.generate("test prompt")
        assert result.success is False
        assert "Todos los proveedores fallaron" in (result.error or "")

    def test_router_no_providers(self):
        """Router no providers."""
        result = fallback_router.generate("test prompt")
        assert result.success is False

    def test_router_opens_circuit_on_failure(self):
        """Router opens circuit on failure."""
        self._make("gemini", cls=FailProvider)
        self._make("openai")

        fallback_router.generate("test")
        assert provider_registry._circuit_open("gemini") is True

    def test_test_all(self):
        """Test all."""
        self._make("gemini")
        self._make("openai", cls=FailProvider)

        results = fallback_router.test_all()
        by_name = {r["name"]: r for r in results}
        assert "gemini" in by_name
        assert "openai" in by_name


# ─── Tracing ─────────────────────────────────────────────────────────────


class TestTracing:
    """Test Tracing."""
    def setup_method(self):
        """Setup method."""
        cache.clear()

    def test_record_call(self):
        """Record call."""
        record_call("gemini", "pro", 100, 10, 20, True, "test")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["total_calls"] >= 1
        assert metrics["total_errors"] == 0

    def test_record_call_failure(self):
        """Record call failure."""
        record_call("openai", "gpt4", 50, 0, 0, False, "test", error_str="429 rate limit")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["total_errors"] >= 1

    def test_record_multiple_calls(self):
        """Record multiple calls."""
        for _ in range(5):
            record_call("gemini", "flash", 10, 1, 1, True, "batch")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["total_calls"] == 5
        assert metrics["total_errors"] == 0

    def test_avg_duration(self):
        """Avg duration."""
        record_call("p", "m", 100, 0, 0, True, "t")
        record_call("p", "m", 200, 0, 0, True, "t")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["avg_duration_ms"] == 150

    def test_empty_history(self):
        """Empty history."""
        metrics = get_hourly_metrics(hours=1)
        assert metrics["total_calls"] == 0
        assert metrics["avg_duration_ms"] == 0

    def test_error_categorization(self):
        """Error categorization."""
        record_call("gemini", "m", 10, 0, 0, False, "test", error_str="429 Too Many Requests")
        record_call("gemini", "m", 10, 0, 0, False, "test", error_str="timed out")
        record_call("gemini", "m", 10, 0, 0, False, "test", error_str="401 Unauthorized")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["error_types"]["rate_limit"] >= 1
        assert metrics["error_types"]["timeout"] >= 1
        assert metrics["error_types"]["auth"] >= 1

    def test_cost_estimation(self):
        """Cost estimation."""
        record_call("gemini", "m", 100, 1000, 500, True, "test")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["estimated_cost_usd"] > 0

    def test_error_rate(self):
        """Error rate."""
        for _ in range(10):
            record_call("gemini", "m", 10, 0, 0, True, "test")
        for _ in range(2):
            record_call("gemini", "m", 10, 0, 0, False, "test", error_str="timeout")
        metrics = get_hourly_metrics(hours=1)
        assert metrics["error_rate"] == 16.67  # 2/12 = 16.67%


# ─── Health ──────────────────────────────────────────────────────────────


class TestHealth:
    """Test Health."""
    def setup_method(self):
        """Setup method."""
        provider_registry._providers.clear()
        cache.clear()
        cache.delete("health_history")
        cache.delete("health_check_providers_last_run")

    def test_get_health_summary_empty(self):
        """Get health summary empty."""
        summary = get_health_summary()
        assert summary["providers"] == []
        assert summary["api_secrets"]["total"] == 0

    def test_get_health_summary_with_providers(self):
        """Get health summary with providers."""
        p = OkProvider()
        p.provider_name = "gemini"
        provider_registry.register(p)
        summary = get_health_summary()
        assert len(summary["providers"]) == 1
        assert summary["providers"][0]["name"] == "gemini"

    def test_run_health_checks_updates_status(self, monkeypatch):
        """Run health checks updates status."""
        p = OkProvider()
        p.provider_name = "gemini"
        provider_registry.register(p)
        provider_registry.close_circuit("gemini")

        results = run_health_checks(force=True)
        provider_results = [r for r in results if r["type"] == "provider"]
        assert len(provider_results) >= 1
        ok_providers = [r for r in provider_results if r["status"] == "ok"]
        assert len(ok_providers) >= 1

    def test_run_health_checks_with_failing_provider(self, monkeypatch):
        """Run health checks with failing provider."""
        p = FailProvider()
        p.provider_name = "gemini"
        provider_registry.register(p)

        results = run_health_checks(force=True)
        provider_results = [r for r in results if r["type"] == "provider"]
        fail_providers = [r for r in provider_results if r["status"] == "fail"]
        assert len(fail_providers) >= 1

    def test_health_interval_respected(self, monkeypatch):
        """Health interval respected."""
        p = OkProvider()
        p.provider_name = "gemini"
        provider_registry.register(p)

        results_first = run_health_checks(force=True)
        assert len(results_first) >= 1

        results_second = run_health_checks(force=False)
        assert results_second == []

    def test_health_force_bypasses_interval(self):
        """Health force bypasses interval."""
        results = run_health_checks(force=True)
        assert isinstance(results, list)
