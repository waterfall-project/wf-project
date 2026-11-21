# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The authority of the platform under Compose signs the certificate of each server (US-2840).

Its root is the operator's when they provide one, else one made at the first start and kept; each
server gets a key readable by its user alone and a certificate for its name, which a client that
trusts the root alone accepts, under that name only.
"""

import os
import ssl
import stat
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

from waterfall.platform import authority
from waterfall.platform.authority import Authority, AuthorityError, Served

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)


def folders(root: Path) -> tuple[Path, Path, Path, Path]:
    """Give the folders of a run: provided, kept, trust, certificates."""
    provided = root / "provided"
    provided.mkdir()
    return provided, root / "kept", root / "trust", root / "certificates"


def own(name: str) -> Served:
    """Name a server that runs as the user of the test, who may give a file to itself alone."""
    return Served(name, os.getuid(), os.getgid())


def certificate(path: Path) -> x509.Certificate:
    """Read the first certificate of a file."""
    return x509.load_pem_x509_certificates(path.read_bytes())[0]


def names(of: x509.Certificate) -> list[str]:
    """Give the names a certificate is valid for, its addresses as text."""
    extension = of.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    return [str(name.value) for name in extension]


def operators_authority(folder: Path, *, ca: bool = True, days: int = 3650) -> Authority:
    """Write in a folder an authority as an operator provides it, in RSA, and give it."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Operator root")])
    built = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW - timedelta(days=1))
        .not_valid_after(NOW + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    (folder / "ca.crt").write_bytes(built.public_bytes(serialization.Encoding.PEM))
    (folder / "ca.key").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return Authority((built,), key)


@pytest.mark.requirement("WF-SEC-0010-A")
def test_each_server_gets_its_key_alone_and_a_certificate_the_root_vouches_for_its_name(
    tmp_path: Path,
) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    authority.run(provided, kept, trust, certificates, [own("postgres"), own("api")])
    root = trust / "root.crt"
    for name in ("postgres", "api"):
        folder = certificates / name
        assert stat.S_IMODE((folder / "tls.key").stat().st_mode) == 0o600
        assert stat.S_IMODE((folder / "tls.crt").stat().st_mode) == 0o644
        assert (folder / "ca.crt").read_bytes() == root.read_bytes()
        assert names(certificate(folder / "tls.crt")) == [name, "localhost", "127.0.0.1"]
        # A server of Python serves it, and a client that trusts the root alone accepts it.
        served = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        served.load_cert_chain(folder / "tls.crt", folder / "tls.key")
    issued = certificate(certificates / "postgres" / "tls.crt")
    issued.verify_directly_issued_by(certificate(root))
    usage = issued.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert not usage.ca


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_root_made_at_the_first_start_is_kept_and_signs_again_at_the_next(
    tmp_path: Path,
) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    first = authority.run(provided, kept, trust, certificates, [own("redis")])
    assert stat.S_IMODE((kept / "root.key").stat().st_mode) == 0o600
    issued_first = (certificates / "redis" / "tls.crt").read_bytes()
    second = authority.run(provided, kept, trust, certificates, [own("redis")])
    assert first.pem() == second.pem() == (trust / "root.crt").read_bytes()
    # Issued again, by the same root.
    assert (certificates / "redis" / "tls.crt").read_bytes() != issued_first
    certificate(certificates / "redis" / "tls.crt").verify_directly_issued_by(second.issuer)


def test_the_root_made_is_an_authority_that_signs_nothing_but_certificates_of_servers() -> None:
    made = authority.made(NOW)
    constraints = made.issuer.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert (constraints.ca, constraints.path_length) == (True, 0)
    assert made.issuer.not_valid_after_utc - NOW == authority.ROOT_LIFETIME
    _, chain = authority.issued(made, "keycloak", NOW)
    leaf = x509.load_pem_x509_certificates(chain)[0]
    assert leaf.not_valid_after_utc - NOW == authority.LEAF_LIFETIME
    assert leaf.not_valid_before_utc == NOW - authority.BACKDATE


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_authority_of_the_operator_signs_in_place_of_one_made(tmp_path: Path) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    given = operators_authority(provided)
    authority.run(provided, kept, trust, certificates, [own("storage")])
    assert (trust / "root.crt").read_bytes() == given.pem()
    certificate(certificates / "storage" / "tls.crt").verify_directly_issued_by(given.issuer)
    assert not kept.exists()


def test_a_certificate_of_a_server_never_outlives_the_authority_that_signs_it(
    tmp_path: Path,
) -> None:
    given = operators_authority(tmp_path, days=30)
    _, chain = authority.issued(given, "api", NOW)
    leaf = x509.load_pem_x509_certificates(chain)[0]
    assert leaf.not_valid_after_utc == given.issuer.not_valid_after_utc


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.parametrize("left", ["ca.crt", "ca.key"])
def test_half_an_authority_provided_stops_the_command_naming_what_lacks(
    left: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    operators_authority(provided)
    (provided / left).unlink()
    arguments = [
        f"--provided={provided}",
        f"--kept={kept}",
        f"--trust={trust}",
        f"--certificates={certificates}",
        "postgres:999:999",
    ]
    assert authority.main(arguments) == 1
    assert f"the authority provided lacks {provided / left}" in capsys.readouterr().err
    assert not trust.exists()
    assert not certificates.exists()


@pytest.mark.requirement("WF-SEC-0010-A")
def test_an_authority_whose_key_is_not_that_of_its_certificate_is_refused(tmp_path: Path) -> None:
    provided, kept, *_ = folders(tmp_path)
    operators_authority(provided)
    other = ec.generate_private_key(ec.SECP256R1())
    (provided / "ca.key").write_bytes(
        other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    with pytest.raises(AuthorityError, match="is not that of the certificate"):
        authority.authority_of(provided, kept, NOW)


def test_a_certificate_that_is_no_authority_is_refused(tmp_path: Path) -> None:
    operators_authority(tmp_path, ca=False)
    with pytest.raises(AuthorityError, match="is not a certificate of authority"):
        authority.authority_of(tmp_path, tmp_path / "kept", NOW)


def of_authority(
    name: str,
    key: ec.EllipticCurvePrivateKey,
    signer: tuple[x509.Name, ec.EllipticCurvePrivateKey] | None = None,
    *,
    path_length: int | None = None,
    signs_certificates: bool = True,
) -> x509.Certificate:
    """Make a certificate of authority, signed by ``signer``, a name and its key, else by itself."""
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    issuer, signing = signer or (subject, key)
    usage = x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=signs_certificates,
        crl_sign=True,
        encipher_only=False,
        decipher_only=False,
    )
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW - timedelta(days=1))
        .not_valid_after(NOW + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=path_length), critical=True)
        .add_extension(usage, critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(signing.public_key()),
            critical=False,
        )
        .sign(signing, hashes.SHA256())
    )


def provide(folder: Path, chain: list[x509.Certificate], key: ec.EllipticCurvePrivateKey) -> None:
    """Write ``ca.crt``, the certificates of a chain in their order, and ``ca.key``."""
    pem = b"".join(each.public_bytes(serialization.Encoding.PEM) for each in chain)
    (folder / "ca.crt").write_bytes(pem)
    (folder / "ca.key").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_an_intermediate_authority_followed_by_its_root_signs_what_its_root_vouches_for(
    tmp_path: Path,
) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    root_key = ec.generate_private_key(ec.SECP256R1())
    intermediate_key = ec.generate_private_key(ec.SECP256R1())
    root = of_authority("Operator root", root_key, path_length=1)
    intermediate = of_authority(
        "Operator intermediate", intermediate_key, (root.subject, root_key), path_length=0
    )
    provide(provided, [intermediate, root], intermediate_key)
    authority.run(provided, kept, trust, certificates, [own("api")])
    leaf = certificate(certificates / "api" / "tls.crt")
    leaf.verify_directly_issued_by(intermediate)
    # The server serves its chain; a client that trusts the root alone accepts it.
    client = ssl.create_default_context(cafile=root_only(tmp_path, root))
    served = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    served.load_cert_chain(certificates / "api" / "tls.crt", certificates / "api" / "tls.key")
    assert handshake(served, client, "api")


def root_only(folder: Path, root: x509.Certificate) -> Path:
    """Write a root alone in a file, and give its path."""
    path = folder / "root-only.crt"
    path.write_bytes(root.public_bytes(serialization.Encoding.PEM))
    return path


def handshake(server: ssl.SSLContext, client: ssl.SSLContext, name: str) -> bool:
    """Tell whether a client reaches a server by its name in memory, its certificate accepted."""
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    back_in, back_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    serving = server.wrap_bio(incoming, back_out, server_side=True)
    asking = client.wrap_bio(back_in, outgoing, server_hostname=name)
    for _ in range(10):
        done = 0
        for side in (asking, serving):
            try:
                side.do_handshake()
                done += 1
            except ssl.SSLWantReadError:
                pass
        incoming.write(outgoing.read())
        back_in.write(back_out.read())
        if done == 2:
            return True
    return False


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.parametrize(
    ("given", "said"),
    [
        ("root of path 0 over an intermediate", "length of path is too short"),
        ("signs no certificate", "does not sign certificates"),
        ("another certificate after it", "each signed by the next"),
        ("root before the intermediate", "is not that of the certificate"),
        ("intermediate, then a root that did not sign it", "each signed by the next"),
    ],
)
def test_a_provided_authority_that_cannot_sign_the_certificate_of_a_server_is_refused(
    given: str, said: str, tmp_path: Path
) -> None:
    keys = [ec.generate_private_key(ec.SECP256R1()) for _ in range(3)]
    root = of_authority("Operator root", keys[0], path_length=0 if "path 0" in given else None)
    intermediate = of_authority("Operator intermediate", keys[1], (root.subject, keys[0]))
    other = of_authority("Another root", keys[2])
    chains = {
        "root of path 0 over an intermediate": ([intermediate, root], keys[1]),
        "signs no certificate": (
            [of_authority("Operator root", keys[0], signs_certificates=False)],
            keys[0],
        ),
        "another certificate after it": ([root, other], keys[0]),
        "root before the intermediate": ([root, intermediate], keys[1]),
        "intermediate, then a root that did not sign it": ([intermediate, other], keys[1]),
    }
    chain, key = chains[given]
    provide(tmp_path, chain, key)
    with pytest.raises(AuthorityError, match=said) as refused:
        authority.authority_of(tmp_path, tmp_path / "kept", NOW)
    assert str(tmp_path / "ca.crt") in str(refused.value)


def test_an_authority_no_longer_valid_is_refused(tmp_path: Path) -> None:
    operators_authority(tmp_path, days=1)
    later = NOW + timedelta(days=2)
    with pytest.raises(AuthorityError, match="is not valid now"):
        authority.authority_of(tmp_path, tmp_path / "kept", later)


def test_an_encrypted_key_or_no_certificate_is_refused(tmp_path: Path) -> None:
    given = operators_authority(tmp_path)
    (tmp_path / "ca.key").write_bytes(
        given.key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(b"a password"),
        )
    )
    with pytest.raises(AuthorityError, match="without a password"):
        authority.authority_of(tmp_path, tmp_path / "kept", NOW)
    (tmp_path / "ca.crt").write_text("no certificate\n", encoding="utf-8")
    with pytest.raises(AuthorityError, match="holds no certificate in PEM"):
        authority.authority_of(tmp_path, tmp_path / "kept", NOW)


def test_a_file_that_cannot_be_written_stops_the_command_saying_so(tmp_path: Path) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    trust.write_text("a file, where a folder is wanted\n", encoding="utf-8")
    with pytest.raises(AuthorityError, match="cannot be written"):
        authority.run(provided, kept, trust, certificates, [own("api")])


def test_the_command_says_which_servers_it_certified(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provided, kept, trust, certificates = folders(tmp_path)
    user = f"{os.getuid()}:{os.getgid()}"
    arguments = [
        f"--provided={provided}",
        f"--kept={kept}",
        f"--trust={trust}",
        f"--certificates={certificates}",
        f"postgres:{user}",
        f"keycloak:{user}",
    ]
    assert authority.main(arguments) == 0
    said = capsys.readouterr().out
    assert said.startswith("waterfall-authority: postgres, keycloak certified by ")
    assert "Waterfall platform authority" in said


@pytest.mark.parametrize("given", ["postgres", "postgres:999", "postgres:x:1", ":1:1"])
def test_a_server_not_named_with_its_user_and_group_is_refused(
    given: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    arguments = [
        f"--provided={tmp_path}",
        f"--kept={tmp_path}",
        f"--trust={tmp_path}",
        f"--certificates={tmp_path}",
        given,
    ]
    with pytest.raises(SystemExit) as stopped:
        authority.main(arguments)
    assert stopped.value.code == 2
    assert "is not <name>:<uid>:<gid>" in capsys.readouterr().err
