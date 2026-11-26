# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The authority of the platform under Compose, and the certificate of each service (US-2840).

Every exchange between the services is encrypted, and each client checks the certificate of the
server it reaches against the root of the platform (WF-SEC-0010, TFX-02 to TFX-05, TFX-08, TFX-10,
TFX-12). That root is the operator's when they provide one — a certificate of authority and its
key, ``ca.crt`` and ``ca.key`` of the folder ``provided``, the certificate followed if need be by
those up to the root — or one made here at the first start and kept, with its key, in the folder
``kept``. The internal certificates may come from such an authority (WF-CMP-0030).

At each start of the platform, ``waterfall-authority`` issues again, for each service that serves
in TLS, a key and a certificate for its name in the network of the platform and for the loopback,
where its own health check reaches it, and writes them in the folder of that service alone, owned
by the user the service runs as, the key readable by that user alone. It writes the root, which
every client reads, in the folder of the trust. Caddy's own authority, which makes the certificate
of a local name at the door, issues only for the sites Caddy serves itself: it cannot sign those of
PostgreSQL, Redis or Keycloak.

A provided authority that cannot be read, or whose key is not that of its certificate, stops the
command, saying so; nothing is written then.
"""

import argparse
import ipaddress
import itertools
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cryptography.hazmat.primitives.asymmetric.types import CertificateIssuerPrivateKeyTypes

NAME = "waterfall-authority"
# The name of the root the platform makes when the operator provides none.
ROOT_NAME = "Waterfall platform authority"
ROOT_LIFETIME = timedelta(days=3650)
# A certificate of a service is issued again at each start of the platform; two years cover a
# platform that is not restarted between two updates.
LEAF_LIFETIME = timedelta(days=730)
# A certificate is valid from a little before it is made: the clocks of the containers may differ.
BACKDATE = timedelta(minutes=5)

# What the operator provides, in the folder ``provided``.
PROVIDED_CERTIFICATE = "ca.crt"
PROVIDED_KEY = "ca.key"
# What the platform keeps of the root it made, in the folder ``kept``.
KEPT_CERTIFICATE = "root.crt"
KEPT_KEY = "root.key"
# The root every client trusts, in the folder of the trust.
TRUSTED = "root.crt"
# What a service that serves in TLS reads, in its folder: its chain, its key, and the root.
CHAIN = "tls.crt"
KEY = "tls.key"
ROOT = "ca.crt"

PUBLIC = 0o644
PRIVATE = 0o600
# The keys that sign a certificate.
SIGNING_KEYS = (
    dsa.DSAPrivateKey,
    rsa.RSAPrivateKey,
    ec.EllipticCurvePrivateKey,
    ed25519.Ed25519PrivateKey,
    ed448.Ed448PrivateKey,
)


class AuthorityError(Exception):
    """The authority cannot be read, or a certificate cannot be written."""


@dataclass(frozen=True, slots=True)
class Authority:
    """A certificate of authority, the certificates up to its root after it, and its key."""

    certificates: tuple[x509.Certificate, ...]
    key: CertificateIssuerPrivateKeyTypes

    @property
    def issuer(self) -> x509.Certificate:
        """Give the certificate that signs those of the services."""
        return self.certificates[0]

    def pem(self) -> bytes:
        """Give the certificates of the authority in PEM, itself first: what a client trusts."""
        return b"".join(each.public_bytes(serialization.Encoding.PEM) for each in self.certificates)


@dataclass(frozen=True, slots=True)
class Served:
    """A service that serves in TLS: its name in the network, and the user it runs as."""

    name: str
    uid: int
    gid: int

    @classmethod
    def parse(cls, given: str) -> Served:
        """Read ``<name>:<uid>:<gid>``, as the command line of the service ``authority`` says it."""
        name, _, rest = given.partition(":")
        uid, _, gid = rest.partition(":")
        if not name or not uid.isdigit() or not gid.isdigit():
            message = f"{given!r} is not <name>:<uid>:<gid>"
            raise argparse.ArgumentTypeError(message)
        return cls(name, int(uid), int(gid))


def _signature(key: CertificateIssuerPrivateKeyTypes) -> hashes.SHA256 | None:
    # Ed25519 and Ed448 sign without a separate hash; every other key, with SHA-256.
    if isinstance(key, ed25519.Ed25519PrivateKey | ed448.Ed448PrivateKey):
        return None
    return hashes.SHA256()


def _certificates(path: Path) -> tuple[x509.Certificate, ...]:
    try:
        found = tuple(x509.load_pem_x509_certificates(path.read_bytes()))
    except ValueError:
        found = ()
    if not found:
        message = f"{path} holds no certificate in PEM"
        raise AuthorityError(message)
    return found


def _key(path: Path) -> CertificateIssuerPrivateKeyTypes:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (ValueError, TypeError, UnsupportedAlgorithm) as error:
        message = f"{path} holds no private key in PEM that can be read without a password"
        raise AuthorityError(message) from error
    if not isinstance(key, SIGNING_KEYS):
        message = f"{path} holds a key that cannot sign a certificate"
        raise AuthorityError(message)
    return key


def _signs_certificates(certificate: x509.Certificate, below: int) -> bool:
    """Tell whether a certificate may sign one with ``below`` authorities under it in a path.

    It is one of authority, whose length of path admits them, and whose usages, when it says them,
    include the signature of a certificate: what a client checks before it trusts a service.
    """
    try:
        constraints = certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
    except x509.ExtensionNotFound:
        return False
    too_short = constraints.path_length is not None and constraints.path_length < below
    if not constraints.ca or too_short:
        return False
    try:
        usage = certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        return True
    return usage.key_cert_sign


def _chained(certificates: Sequence[x509.Certificate], path: Path) -> None:
    """Refuse a file that holds the authority and something else than the chain up to its root.

    Each certificate after the first is the one that signed the certificate before it.
    """
    for lower, upper in itertools.pairwise(certificates):
        try:
            lower.verify_directly_issued_by(upper)
        except (ValueError, TypeError, InvalidSignature) as error:
            message = (
                f"{path} must hold the certificate of the authority alone, or followed by those up "
                "to its root, each signed by the next"
            )
            raise AuthorityError(message) from error


def loaded(certificate: Path, key: Path, now: datetime) -> Authority:
    """Read an authority, and check that it may sign: a certificate of authority, valid, its key.

    The certificates after it, if any, are those up to its root, in order, each of authority with a
    length of path that admits those under it.
    """
    certificates = _certificates(certificate)
    private = _key(key)
    issuer = certificates[0]
    if issuer.public_key() != private.public_key():
        message = f"the key {key} is not that of the certificate {certificate}"
        raise AuthorityError(message)
    _chained(certificates, certificate)
    for below, each in enumerate(certificates):
        if not _signs_certificates(each, below):
            subject = each.subject.rfc4514_string()
            message = (
                f"{certificate} is not a certificate of authority that may sign those of the "
                f"services: {subject} is not of authority, does not sign certificates, or its "
                "length of path is too short"
            )
            raise AuthorityError(message)
    if not issuer.not_valid_before_utc <= now < issuer.not_valid_after_utc:
        message = f"{certificate} is not valid now"
        raise AuthorityError(message)
    return Authority(certificates, private)


def made(now: datetime) -> Authority:
    """Make a root of the platform, signed by itself, valid ``ROOT_LIFETIME``."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Waterfall"),
            x509.NameAttribute(NameOID.COMMON_NAME, ROOT_NAME),
        ]
    )
    usage = x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=True,
        crl_sign=True,
        encipher_only=False,
        decipher_only=False,
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - BACKDATE)
        .not_valid_after(now + ROOT_LIFETIME)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(usage, critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return Authority((certificate,), key)


def authority_of(provided: Path, kept: Path, now: datetime) -> Authority:
    """Give the operator's authority, if they provide one; else the platform's, made once.

    A provided folder that holds the certificate without its key, or the key without the
    certificate, is refused: half an authority is a mistake, never a wish to have none.
    """
    certificate, key = provided / PROVIDED_CERTIFICATE, provided / PROVIDED_KEY
    if certificate.exists() or key.exists():
        for path in (certificate, key):
            if not path.is_file():
                message = f"the authority provided lacks {path}"
                raise AuthorityError(message)
        return loaded(certificate, key, now)
    certificate, key = kept / KEPT_CERTIFICATE, kept / KEPT_KEY
    if certificate.exists() and key.exists():
        return loaded(certificate, key, now)
    authority = made(now)
    _write(
        key,
        authority.key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        PRIVATE,
    )
    _write(certificate, authority.pem(), PUBLIC)
    return authority


def issued(authority: Authority, name: str, now: datetime) -> tuple[bytes, bytes]:
    """Issue the key and the certificate of a service: its key, then its chain, in PEM.

    The certificate names the service as the network of the platform does, and the loopback,
    ``localhost`` and ``127.0.0.1``, where the health check of its container reaches it. It is
    valid ``LEAF_LIFETIME``, never past the authority that signs it.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    issuer = authority.issuer
    names = x509.SubjectAlternativeName(
        [
            x509.DNSName(name),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]
    )
    usage = x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
        .issuer_name(issuer.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - BACKDATE)
        .not_valid_after(min(now + LEAF_LIFETIME, issuer.not_valid_after_utc))
        .add_extension(names, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(usage, critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(_issuer_identifier(authority), critical=False)
        .sign(authority.key, _signature(authority.key))
    )
    private = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return private, certificate.public_bytes(serialization.Encoding.PEM) + authority.pem()


def _issuer_identifier(authority: Authority) -> x509.AuthorityKeyIdentifier:
    """Name the key of the authority as its certificate names it, else from the key itself.

    A client finds the issuer of a certificate by that identifier: computed otherwise than the
    authority declares its own — Helm's ``genCA``, whose Go takes a truncated SHA-256 where the
    method of RFC 5280 takes SHA-1 —, OpenSSL finds no issuer, and refuses the certificate.
    """
    try:
        declared = authority.issuer.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
    except x509.ExtensionNotFound:
        return x509.AuthorityKeyIdentifier.from_issuer_public_key(authority.key.public_key())
    return x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(declared.value)


def _write(path: Path, content: bytes, mode: int, owner: tuple[int, int] | None = None) -> None:
    """Write a file whole, its mode and its owner set before it takes its name.

    A reader finds the former file or the new one, never half of one, nor a key readable by another
    user for an instant.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    except OSError as error:
        message = f"{path} cannot be written: {error.strerror}"
        raise AuthorityError(message) from error
    try:
        with os.fdopen(descriptor, "wb") as written:
            written.write(content)
        Path(temporary).chmod(mode)
        if owner is not None:
            os.chown(temporary, *owner)
        Path(temporary).replace(path)
    except OSError as error:
        Path(temporary).unlink(missing_ok=True)
        message = f"{path} cannot be written: {error.strerror}"
        raise AuthorityError(message) from error


def run(
    provided: Path, kept: Path, trust: Path, certificates: Path, served: Sequence[Served]
) -> Authority:
    """Give each service its key and its certificate, and the clients the root they trust."""
    now = datetime.now(UTC)
    authority = authority_of(provided, kept, now)
    _write(trust / TRUSTED, authority.pem(), PUBLIC)
    for service in served:
        key, chain = issued(authority, service.name, now)
        folder = certificates / service.name
        owner = (service.uid, service.gid)
        _write(folder / ROOT, authority.pem(), PUBLIC, owner)
        _write(folder / CHAIN, chain, PUBLIC, owner)
        _write(folder / KEY, key, PRIVATE, owner)
    return authority


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=NAME, description="Issue the certificates of the services of the platform."
    )
    parser.add_argument("--provided", type=Path, required=True, help="the operator's authority")
    parser.add_argument("--kept", type=Path, required=True, help="where the made root is kept")
    parser.add_argument("--trust", type=Path, required=True, help="where the clients read it")
    parser.add_argument(
        "--certificates", type=Path, required=True, help="a folder of each service, by its name"
    )
    parser.add_argument("served", nargs="+", type=Served.parse, help="<name>:<uid>:<gid>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Issue the certificates, or say why they cannot be (status 1; 2 for a wrong command line)."""
    given = _parser().parse_args(argv)
    try:
        authority = run(given.provided, given.kept, given.trust, given.certificates, given.served)
    except AuthorityError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 1
    names = ", ".join(service.name for service in given.served)
    subject = authority.issuer.subject.rfc4514_string()
    sys.stdout.write(f"{NAME}: {names} certified by {subject}\n")
    return 0
