from __future__ import annotations

import html
import hmac
import secrets
import string
from hashlib import sha256


CAPTCHA_SESSION_KEY = "captcha_digest"
CAPTCHA_TEST_SESSION_KEY = "captcha_test_answer"
CAPTCHA_ALPHABET = "".join(
    char for char in string.ascii_uppercase + string.digits if char not in "0O1IL"
)


def generate_captcha_code(length: int = 5) -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(length))


def normalize_captcha_answer(answer: str) -> str:
    return "".join(answer.upper().split())


def captcha_digest(code: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"),
        normalize_captcha_answer(code).encode("utf-8"),
        sha256,
    ).hexdigest()


def captcha_matches(expected_digest: str | None, submitted: str, secret_key: str) -> bool:
    if not expected_digest:
        return False
    submitted_digest = captcha_digest(submitted, secret_key)
    return hmac.compare_digest(expected_digest, submitted_digest)


def render_captcha_svg(code: str) -> str:
    escaped_code = html.escape(code)
    chars = []
    for index, char in enumerate(escaped_code):
        chars.append(
            f'<text x="{28 + index * 27}" y="{48 + ((index % 2) * 5)}" '
            f'rotate="{[-8, 6, -4, 9, -6][index % 5]}">{char}</text>'
        )
    noise_lines = "\n".join(
        f'<line x1="{12 + index * 29}" y1="{18 + (index % 3) * 13}" '
        f'x2="{42 + index * 24}" y2="{70 - (index % 4) * 9}" />'
        for index in range(6)
    )
    noise_dots = "\n".join(
        f'<circle cx="{18 + (index * 19) % 150}" cy="{20 + (index * 23) % 42}" r="1.7" />'
        for index in range(18)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="180" height="76" viewBox="0 0 180 76" role="img" aria-label="CAPTCHA image">
  <rect width="180" height="76" rx="8" fill="#f4f8f9"/>
  <g stroke="#9ab3bb" stroke-width="2" stroke-linecap="round" opacity="0.75">
    {noise_lines}
  </g>
  <g fill="#0b5562" opacity="0.55">
    {noise_dots}
  </g>
  <g fill="#1c232b" font-family="Menlo, Consolas, monospace" font-size="34" font-weight="800">
    {"".join(chars)}
  </g>
</svg>
"""
