import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("smoke_test", ROOT / "deploy" / "oracle" / "smoke-test.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_smoke_checks_health_and_authenticated_search(monkeypatch):
    seen = []

    def fake_get(url, token=""):
        seen.append((url, token))
        return {"ok": True} if url.endswith("/health") else {"places": [{"name": "Clinic"}]}

    monkeypatch.setattr(MODULE, "get_json", fake_get)
    passed = MODULE.smoke({"PUBLIC_BASE_URL": "https://api.heybillo.tech", "INTERNAL_TOKEN": "secret"})
    assert passed == ["HTTPS health", "authenticated care search"]
    assert seen[0] == ("https://api.heybillo.tech/health", "")
    assert seen[1][1] == "secret"


@pytest.mark.parametrize("base", ["", "http://api.heybillo.tech"])
def test_smoke_requires_https(base):
    with pytest.raises(ValueError, match="HTTPS"):
        MODULE.smoke({"PUBLIC_BASE_URL": base, "INTERNAL_TOKEN": "secret"})


def test_smoke_rejects_development_token():
    with pytest.raises(ValueError, match="INTERNAL_TOKEN"):
        MODULE.smoke({"PUBLIC_BASE_URL": "https://api.heybillo.tech", "INTERNAL_TOKEN": "dev-token"})
