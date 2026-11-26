# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The authority of the trial of the chart, and the certificates it issues, by OpenSSL (US-2800).

The domain the platform is published under, ``waterfall.localhost``, has a certificate an authority
of the trial signs, which the front and the trial alone trust; so have the components an operator
provides (``wftools.chartdata``).
"""

from typing import TYPE_CHECKING

from wftools.chartrun import Read, output

if TYPE_CHECKING:
    from pathlib import Path

KEY = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-noenc"]
"""A key of the trial, made with its request: P-256, unencrypted."""


def make_authority(read: Read, folder: Path, domain: str) -> None:
    """Make an authority of the trial, and the certificate of the domain it signs, by OpenSSL."""
    authority = folder / "ca"
    output(
        read,
        [
            "openssl",
            "req",
            "-x509",
            *KEY,
            "-days",
            "1",
            "-subj",
            "/CN=Waterfall trial",
            "-keyout",
            f"{authority}.key",
            "-out",
            f"{authority}.crt",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        ],
        "make the authority of the trial",
    )
    issue(read, folder, "tls", domain)


def issue(read: Read, folder: Path, stem: str, name: str) -> None:
    """Issue, by the authority of the trial, the key and the certificate of a server of a name.

    They are ``<stem>.key`` and ``<stem>.crt`` of the folder, beside the authority, ``ca.crt``.
    """
    extensions = folder / f"{stem}.ext"
    extensions.write_text(
        f"subjectAltName=DNS:{name}\nbasicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\n"
        "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid\n",
        encoding="utf-8",
    )
    authority, certificate = folder / "ca", folder / stem
    output(
        read,
        [
            "openssl",
            "req",
            *KEY,
            "-subj",
            f"/CN={name}",
            "-keyout",
            f"{certificate}.key",
            "-out",
            f"{certificate}.csr",
        ],
        "make the key and the request of the certificate",
    )
    output(
        read,
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            f"{certificate}.csr",
            "-days",
            "1",
            "-CA",
            f"{authority}.crt",
            "-CAkey",
            f"{authority}.key",
            "-out",
            f"{certificate}.crt",
            "-extfile",
            str(extensions),
        ],
        "sign the certificate",
    )
