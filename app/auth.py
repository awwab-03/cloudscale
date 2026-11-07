import functools
import logging

import jwt
from botocore.exceptions import ClientError
from flask import redirect, request, session, url_for

import aws_clients
import config
import db

log = logging.getLogger("cloudscale.auth")

_ISSUER = f"https://cognito-idp.{config.REGION}.amazonaws.com/{config.COGNITO_POOL_ID}"
_jwks = None


def _jwk_client():
    global _jwks
    if _jwks is None:
        _jwks = jwt.PyJWKClient(f"{_ISSUER}/.well-known/jwks.json")
    return _jwks


def _message(exc):
    return exc.response.get("Error", {}).get("Message", "Request failed.")


def sign_up(email, password, name):
    try:
        aws_clients.cognito().sign_up(
            ClientId=config.COGNITO_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name},
            ],
        )
        return None
    except ClientError as exc:
        return _message(exc)


def confirm_sign_up(email, code):
    try:
        aws_clients.cognito().confirm_sign_up(
            ClientId=config.COGNITO_CLIENT_ID, Username=email, ConfirmationCode=code
        )
        return None
    except ClientError as exc:
        return _message(exc)


def verify_id_token(token):
    """Verify signature, issuer, audience and token_use against the pool's JWKS."""
    signing_key = _jwk_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=config.COGNITO_CLIENT_ID,
        issuer=_ISSUER,
    )
    if claims.get("token_use") != "id":
        raise jwt.InvalidTokenError("not an id token")
    return claims


def log_in(email, password):
    """Returns (claims, error). On success the user row is upserted."""
    try:
        resp = aws_clients.cognito().initiate_auth(
            ClientId=config.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "UserNotConfirmedException":
            return None, "Please confirm your email first (use the Confirm page)."
        return None, "Incorrect email or password."
    result = resp.get("AuthenticationResult")
    if not result:
        return None, "Sign-in needs an extra step that this app does not support."
    try:
        claims = verify_id_token(result["IdToken"])
    except jwt.PyJWTError as exc:
        log.warning("token verification failed: %s", exc)
        return None, "Could not verify your sign-in. Please try again."
    sub = claims["sub"]
    mail = claims.get("email", email)
    name = claims.get("name") or mail.split("@")[0]
    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO users (sub, email, display_name) VALUES (%s, %s, %s)
               ON CONFLICT (sub) DO UPDATE SET email = EXCLUDED.email,
                                               display_name = EXCLUDED.display_name""",
            (sub, mail, name),
        )
    aws_clients.subscribe_owner(mail)
    return {"sub": sub, "email": mail, "name": name}, None


def current_user():
    return session.get("user")


def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapper
