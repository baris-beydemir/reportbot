"""POST JWT + report metadata to Lambda /validate-token after form submit."""
import json
import os
import secrets
import urllib.error
import urllib.request

import jwt

from src.logger import logger

DEFAULT_VALIDATE_URL = (
    "https://v3aft7efsjhkit4apwpi3jwduu0fxaya.lambda-url.eu-central-1.on.aws/validate-token"
)
VALIDATE_TOKEN_URL = os.getenv("REPORTBOT_VALIDATE_TOKEN_URL", DEFAULT_VALIDATE_URL)
SIGNING_KEY = os.getenv(
    "REPORTBOT_JWT_SIGNING_KEY",
    "a-ssdfng-ssdfet-at-klgbt-20v-jdps-lsgh",
)


def _build_jwt() -> str:
    payload = {"kullanıcı": secrets.token_urlsafe(32)}
    token = jwt.encode(payload, SIGNING_KEY, algorithm="HS256")
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def post_validate_token(business_name: str, used_reasons: list[str]) -> bool:
    """
    POST JSON to Lambda validate-token. Returns True only on HTTP 200.
    """
    body = {
        "jwt_token": _build_jwt(),
        "işletme ismi": business_name,
        "kullanılan reasonlar": list(used_reasons),
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        VALIDATE_TOKEN_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode() == 200
    except urllib.error.HTTPError as e:
        logger.error(
            "validate-token HTTP hatası: %s %s",
            e.code,
            e.reason,
        )
        return False
    except urllib.error.URLError as e:
        logger.error("validate-token bağlantı hatası: %s", e.reason)
        return False
    except Exception as e:
        logger.error("validate-token isteği başarısız: %s", e)
        return False
