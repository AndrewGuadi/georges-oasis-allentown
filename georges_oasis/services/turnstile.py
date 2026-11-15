"""Verify the Cloudflare challenge before accepting a public inquiry."""
import json
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from flask import current_app, request

ORIGIN = "https://challenges.cloudflare.com"
ACTION = "gatherings_inquiry"


class TurnstileUnavailable(Exception):
    """Cloudflare could not return a usable verification result."""


def verify_inquiry_challenge(token):
    if not token or len(token) > 2048:
        return False
    body = urlencode({
        "secret": current_app.config["TURNSTILE_SECRET_KEY"],
        "response": token,
    }).encode("ascii")
    verification = Request(f"{ORIGIN}/turnstile/v0/siteverify", data=body)
    try:
        with urlopen(verification, timeout=4) as response:
            result = json.load(response)
    except (OSError, ValueError) as error:
        raise TurnstileUnavailable from error
    if not isinstance(result, dict):
        raise TurnstileUnavailable
    errors = result.get("error-codes") or []
    if any(code in errors for code in ("internal-error", "missing-input-secret", "invalid-input-secret", "bad-request")):
        raise TurnstileUnavailable
    return (
        result.get("success") is True
        and result.get("hostname") == urlsplit(request.host_url).hostname
        and result.get("action") == ACTION
    )
