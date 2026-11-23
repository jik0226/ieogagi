"""Diagnosis 02.10 regression: the session cookie is short-lived, Secure, HttpOnly, Strict.

The contest's round 2 static-analysis diagnosis flagged ``set_session_cookie`` because it set
no Max-Age. These tests pin the attributes on every response that sets the cookie and
check that the browser-side lifetime follows the server idle timeout (sliding renewal).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.auth.cookies import session_cookie_max_age
from app.config import Settings
from app.models import Role
from pydantic import ValidationError

from tests.factories import Factory
from tests.fixed_clock import FixedClock

ONE_HOUR = 60 * 60
TWO_WEEKS = 14 * 24 * ONE_HOUR  # upper bound named in the diagnosis report


def _session_cookies(response, name: str) -> list[tuple[str, dict[str, str]]]:
    """(value, lower-cased attributes) for every Set-Cookie of the session cookie."""
    found = []
    for raw in response.headers.get_list("set-cookie"):
        first, *rest = (part.strip() for part in raw.split(";"))
        cookie_name, _, value = first.partition("=")
        if cookie_name != name:
            continue
        attributes = {}
        for part in rest:
            key, _, attr_value = part.partition("=")
            attributes[key.lower()] = attr_value.lower()
        found.append((value, attributes))
    return found


def _assert_safe(attributes: dict[str, str], settings: Settings) -> None:
    assert "httponly" in attributes
    assert "secure" in attributes
    assert attributes.get("samesite") == "strict"
    assert attributes.get("path") == "/"
    assert "domain" not in attributes  # required by the __Host- prefix
    max_age = int(attributes["max-age"])
    assert max_age == session_cookie_max_age(settings) == settings.session_idle_minutes * 60
    assert 0 < max_age <= ONE_HOUR <= TWO_WEEKS


def test_login_cookie_has_short_max_age_and_safe_flags(factory: Factory, make_client) -> None:
    user = factory.user(factory.center(), Role.STAFF)
    response = make_client().post(
        "/api/auth/login", json={"login_id": user.login_id, "password": factory.password}
    )
    assert response.status_code == 200
    assert factory.settings.cookie_name.startswith("__Host-")
    [(_, attributes)] = _session_cookies(response, factory.settings.cookie_name)
    _assert_safe(attributes, factory.settings)


def test_authenticated_response_renews_cookie_lifetime(factory: Factory, clock: FixedClock) -> None:
    user = factory.user(factory.center(), Role.STAFF)
    client = factory.client_for(user)
    token = client.cookies.get(factory.settings.cookie_name)
    clock.set(clock.now() + timedelta(minutes=9))
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    [(value, attributes)] = _session_cookies(response, factory.settings.cookie_name)
    assert value == token  # same session, only the lifetime is renewed
    _assert_safe(attributes, factory.settings)


def test_renewal_also_covers_endpoints_returning_a_response_object(factory: Factory) -> None:
    center = factory.center()
    director = factory.user(center, Role.DIRECTOR)
    child = factory.child(center, director)
    response = factory.client_for(director).delete(f"/api/children/{child.id}")
    assert response.status_code == 204
    [(_, attributes)] = _session_cookies(response, factory.settings.cookie_name)
    _assert_safe(attributes, factory.settings)


def test_no_cookie_for_missing_or_expired_session(
    factory: Factory, make_client, clock: FixedClock
) -> None:
    anonymous = make_client().get("/api/auth/me")
    assert anonymous.status_code == 401
    assert _session_cookies(anonymous, factory.settings.cookie_name) == []

    client = factory.client_for(factory.user(factory.center(), Role.MENTOR))
    clock.set(clock.now() + timedelta(minutes=11))  # past the 10-minute idle timeout
    expired = client.get("/api/auth/me")
    assert expired.status_code == 401
    assert _session_cookies(expired, factory.settings.cookie_name) == []


def test_logout_sends_only_the_clearing_cookie(factory: Factory) -> None:
    client = factory.client_for(factory.user(factory.center(), Role.STAFF))
    assert client.get("/api/auth/me").status_code == 200
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    [(_, attributes)] = _session_cookies(logout, factory.settings.cookie_name)
    assert attributes["max-age"] == "0"
    assert "httponly" in attributes and "secure" in attributes


def test_idle_setting_caps_cookie_lifetime_at_one_hour() -> None:
    longest = Settings(env="test", session_idle_minutes=60)
    assert session_cookie_max_age(longest) == ONE_HOUR
    with pytest.raises(ValidationError):
        Settings(env="test", session_idle_minutes=61)
