# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A realm of test: keys the test makes, served at the address Keycloak serves its keys at.

The tokens it signs go through the validation of the service as they are, against keys read
over HTTP: what is tried is the code that validates, not a stand-in of it. What depends on
Keycloak itself — its administration API, its sessions — is tried against the platform
(``test_keycloak_*.py``); the realm of test answers only the few calls of the administration API
by which a test says what the realm answers (``synchronization``).
"""

import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

if TYPE_CHECKING:
    from collections.abc import Mapping

REALM = "waterfall"
KEYS_PATH = f"/auth/realms/{REALM}/protocol/openid-connect/certs"
TOKEN_PATH = f"/auth/realms/{REALM}/protocol/openid-connect/token"
ADMIN_PATH = f"/auth/admin/realms/{REALM}"
DIRECTORY_ID = "directory-1"
AUDIENCE = "waterfall-api"
# The key the realm of test signs its tokens with, unless a test asks for another.
KEY = "key-1"
# How often the server of the realm looks whether it is asked to stop, in seconds.
POLL_INTERVAL = 0.01


def new_key() -> rsa.RSAPrivateKey:
    """Make a key of the size Keycloak signs with."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class TestRealm:
    """Keys served over HTTP, as the realm serves its own, and the tokens they sign."""

    __test__ = False

    def __init__(self) -> None:
        """Serve no key yet, on a port of the loopback chosen by the system."""
        self.keys: dict[str, rsa.RSAPrivateKey] = {}
        self.reads = 0
        # The status the keys are served with: another one plays a Keycloak that fails.
        self.status = HTTPStatus.OK
        # How long the keys take to be served: a longer delay than the client waits plays a
        # Keycloak that does not answer.
        self.delay = 0.0
        # What the realm answers to the synchronisation of its one directory: until a test sets it,
        # the realm answers none of the calls of the administration API.
        self.synchronization: bytes | None = None
        # The accounts of the realm, by subject, which the realm lends and takes back as the
        # administration API does (the language of an account): until a test gives them, none.
        self.accounts: dict[str, dict[str, Any]] | None = None
        self._stopping = threading.Event()
        self._encryption = new_key()
        realm = self

        class Handler(BaseHTTPRequestHandler):
            def _answer(self, body: bytes) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_PUT(self) -> None:
                held = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                subject = self.path.removeprefix(f"{ADMIN_PATH}/users/")
                if realm.accounts is None or subject not in realm.accounts:
                    self.send_error(501)
                    return
                realm.accounts[subject] = json.loads(held)
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_POST(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if realm.synchronization is None and realm.accounts is None:
                    self.send_error(501)
                elif self.path == TOKEN_PATH:
                    self._answer(b'{"access_token": "service", "expires_in": 300}')
                elif realm.synchronization is not None and self.path.startswith(
                    f"{ADMIN_PATH}/user-storage/{DIRECTORY_ID}/sync"
                ):
                    self._answer(realm.synchronization)
                else:
                    self.send_error(404)

            def do_GET(self) -> None:
                subject = self.path.removeprefix(f"{ADMIN_PATH}/users/")
                if realm.accounts is not None and subject in realm.accounts:
                    self._answer(json.dumps(realm.accounts[subject]).encode())
                    return
                if realm.synchronization is not None and self.path.startswith(
                    f"{ADMIN_PATH}/components"
                ):
                    directory: dict[str, Any] = {
                        "id": DIRECTORY_ID,
                        "providerId": "ldap",
                        "config": {},
                    }
                    self._answer(json.dumps([directory]).encode())
                    return
                if self.path != KEYS_PATH:
                    self.send_error(404)
                    return
                realm.reads += 1
                realm._stopping.wait(realm.delay)
                if realm.status != HTTPStatus.OK:
                    self.send_error(realm.status)
                    return
                body = json.dumps({"keys": realm.public_keys()}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # shutdown() waits for the loop to look at its flag, every poll_interval: half a second by
        # default, paid by every test that starts a realm — a third of the time of the suite.
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": POLL_INTERVAL}, daemon=True
        )
        self._thread.start()

    @property
    def address(self) -> str:
        """Where the realm is reached, as ``WATERFALL_KEYCLOAK_ADDRESS`` says it."""
        return f"http://127.0.0.1:{self._server.server_address[1]}/auth"

    @property
    def issuer(self) -> str:
        """The issuer of the tokens of the realm."""
        return f"{self.address}/realms/{REALM}"

    def remove_key(self, key_id: str) -> None:
        """Stop serving a key, as a realm that no longer trusts it."""
        del self.keys[key_id]

    def add_key(self, key_id: str) -> rsa.RSAPrivateKey:
        """Make a key and serve its public part from now on."""
        self.keys[key_id] = new_key()
        return self.keys[key_id]

    def public_keys(self) -> list[dict[str, Any]]:
        """List the keys as Keycloak does, with one for encryption the service must not use."""
        listed = [
            {**RSAAlgorithm.to_jwk(key.public_key(), as_dict=True), "kid": key_id, "use": "sig"}
            for key_id, key in self.keys.items()
        ]
        encryption = RSAAlgorithm.to_jwk(self._encryption.public_key(), as_dict=True)
        return [*listed, {**encryption, "kid": "encryption", "use": "enc", "alg": "RSA-OAEP"}]

    def token(
        self,
        subject: str,
        key_id: str,
        *,
        key: rsa.RSAPrivateKey | None = None,
        lifetime: int = 300,
        claims: Mapping[str, Any] | None = None,
    ) -> str:
        """Sign an access token for ``subject``, by the key of ``key_id`` or by another one."""
        now = int(time.time())
        payload: Mapping[str, Any] = {
            "iss": self.issuer,
            "aud": AUDIENCE,
            "sub": subject,
            "iat": now,
            "exp": now + lifetime,
            "typ": "Bearer",
            **(claims or {}),
        }
        signer = key or self.keys[key_id]
        return jwt.encode(dict(payload), signer, algorithm="RS256", headers={"kid": key_id})

    def stop(self) -> None:
        """Stop answering: the realm is unreachable from now on."""
        self._stopping.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
