# Testing Guide

## Running Tests

### With Docker (recommended)

```bash
# Full test suite
docker compose -f docker-compose.test.yml run --rm web

# Run specific test files
docker exec travelhub_web python -m pytest tests/unit/ --no-header -q

# Run with coverage
docker exec travelhub_web python -m pytest tests/unit/ --cov=. --cov-report=term-missing
```

### Test Categories

| Marker | Description | Requires DB |
|--------|-------------|-------------|
| `unit` | Pure logic tests | No |
| `models` | Model validation | Yes |
| `services` | Service layer | Varies |
| `views` | View/URL tests | Yes |
| `admin` | Admin panel | Yes |
| `celery` | Task tests | Varies |
| `django_db` | Any DB access | Yes |

### Running Subsets

```bash
# Unit tests only (fast, no DB)
pytest tests/unit/ -m unit

# Services (may require DB)
pytest tests/services/ -m services

# Exclude E2E (default for CI)
pytest tests/ --ignore=tests/e2e

# All tests with coverage
pytest tests/ --cov=. --cov-fail-under=75
```

## Writing Tests

### Fixtures

Common fixtures in `tests/conftest.py`:
- `superuser` — creates a superuser
- `admin_client` — authenticated admin client
- `agencia` — creates a travel agency
- `usuario_agente` — creates an agent user linked to agency
- `mock_http_requests` — mocks all HTTP requests
- `mock_provider_chain` — mocks AI providers
- `mock_stripe` — mocks Stripe API
- `enable_db_trgm` — enables pg_trgm extension

### Factory Functions (tests/helpers.py)

- `create_test_agencia()` — creates Agencia with default values
- `create_test_user()` — creates User
- `create_test_cliente()` — creates Cliente linked to agencia
- `create_test_venta()` — creates Venta
- `create_test_boleto()` — creates BoletoImportado

### Test Structure

```python
import pytest

pytestmark = [pytest.mark.unit]  # or django_db, services, etc.

class TestFeature:
    def test_success_case(self):
        """Test: descripción breve."""
        # Arrange
        # Act
        # Assert
        assert result == expected

    def test_error_case(self):
        """Test: descripción del escenario de error."""
        with pytest.raises(ExpectedError):
            code_that_raises()
```

## CI Configuration

The `.github/workflows/ci.yml` workflow:
1. Quick pre-check: runs `tests/unit/` first
2. Full suite: all tests except E2E
3. Coverage: `--cov-fail-under=75`
4. PostgreSQL service container for DB-backed tests
