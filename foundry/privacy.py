"""Remove credentials at evidence write boundaries. Projects still de-identify business data."""
import os
import re

SECRET_FIELDS = {"authorization", "password", "access_token", "refresh_token", "api_key", "client_secret"}


def scrub(value):
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key.lower().replace("-", "_") in SECRET_FIELDS else scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        token = os.getenv("OPENAI_API_KEY")
        if token:
            value = value.replace(token, "[redacted]")
        value = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
        return re.sub(r"""(?i)(["'](?:password|api[_-]key|access_token|refresh_token|client_secret)["']\s*:\s*["'])[^"']*(["'])""",
                      r"\1[redacted]\2", value)
    return value
