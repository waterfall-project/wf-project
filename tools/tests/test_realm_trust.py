# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The store of trust of the application of the realm, read back without a password (#4511).

``deploy/keycloak/trust-root.sh``, which ``realm-service.sh`` and ``apply-realm.sh`` read, makes,
from the root of the platform, a store PKCS12 that Java reads without a password, by two options of
keytool that a JDK 17 or later reads. A keytool that ignores them protects the root with the
password drawn: the script must stop then, naming the cause, rather than let Keycloak's certificate
be refused without a word. Played with the keytool of the workstation, as is, then wrapped so that
it drops the options, as an older JDK would. ``apply-realm.sh`` alone — the Job of the hooks of the
chart runs it so — makes the store too, which a run of the Compose by ``realm-service.sh`` makes
once (US-2840).
"""

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

SCRIPT = REPOSITORY / "deploy" / "keycloak" / "realm-service.sh"
APPLY = REPOSITORY / "deploy" / "keycloak" / "apply-realm.sh"
KEYTOOL = shutil.which("keytool")
CAUSE = "is not readable without a password"

pytestmark = [
    pytest.mark.skipif(KEYTOOL is None or shutil.which("openssl") is None, reason="no keytool"),
    pytest.mark.unexecuted("skipped where the workstation has no keytool or no openssl"),
]


def _root(folder: Path) -> Path:
    certificate = folder / "root.crt"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "ec",
            "-pkeyopt",
            "ec_paramgen_curve:P-256",
            "-nodes",
            "-keyout",
            str(folder / "root.key"),
            "-out",
            str(certificate),
            "-subj",
            "/CN=Waterfall platform authority",
            "-days",
            "1",
        ],
        check=True,
        capture_output=True,
    )
    return certificate


def _played(folder: Path, path: str) -> subprocess.CompletedProcess[str]:
    """Run the script up to its first step after the store, which fails: kc.sh is not here."""
    environment = {
        "PATH": path,
        "HOME": str(folder),
        # The store and the session of kcadm in the folder of the test, not in /tmp.
        "TMPDIR": str(folder),
        "WATERFALL_REALM_REQUESTS": str(folder),
        "KEYCLOAK_URL": "https://keycloak:8443/auth",
        "KEYCLOAK_USER": "admin",
        "KEYCLOAK_PASSWORD": "unused",
        "WATERFALL_TLS_AUTHORITY": str(_root(folder)),
    }
    return subprocess.run(
        ["bash", str(SCRIPT), "true"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_store_of_trust_java_reads_without_a_password_lets_the_script_go_on(
    tmp_path: Path,
) -> None:
    done = _played(tmp_path, os.environ.get("PATH", ""))
    # It goes on to the temporary administrator, which kc.sh, absent here, cannot make.
    assert CAUSE not in done.stderr
    assert "no temporary administrator is made" in done.stderr


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_keytool_that_ignores_the_options_stops_the_script_naming_the_cause(
    tmp_path: Path,
) -> None:
    wrapped = tmp_path / "bin"
    wrapped.mkdir()
    keytool = wrapped / "keytool"
    # Drops every -J option, as a JDK that does not read them leaves them without effect.
    keytool.write_text(
        "#!/bin/bash\n"
        'arguments=(); for each in "$@"; do case $each in -J*) ;; *) arguments+=("$each");; esac;'
        f' done\nexec {KEYTOOL} "${{arguments[@]}}"\n',
        encoding="utf-8",
    )
    keytool.chmod(0o755)
    done = _played(tmp_path, f"{wrapped}:{os.environ.get('PATH', '')}")
    assert done.returncode == 1
    assert CAUSE in done.stderr
    assert "certProtectionAlgorithm" in done.stderr


def _applied(folder: Path, given: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run apply-realm with a java that says the options it is given, and nothing else."""
    bin_folder = folder / "bin"
    bin_folder.mkdir()
    java = bin_folder / "java"
    java.write_text('#!/bin/sh\nprintf "%s" "$JAVA_TOOL_OPTIONS"\n', encoding="utf-8")
    java.chmod(0o755)
    environment = {
        "PATH": f"{bin_folder}:{os.environ.get('PATH', '')}",
        "HOME": str(folder),
        "TMPDIR": str(folder),
        "WATERFALL_TLS_AUTHORITY": str(_root(folder)),
        **given,
    }
    return subprocess.run(
        ["sh", str(APPLY)], env=environment, capture_output=True, text=True, check=False
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_application_of_the_realm_alone_checks_keycloak_against_the_root(
    tmp_path: Path,
) -> None:
    # The Job of the chart runs apply-realm without realm-service: it makes the store itself.
    done = _applied(tmp_path, {})
    assert done.returncode == 0, done.stderr
    store = tmp_path / "realm-trust.p12"
    assert done.stdout.split() == [
        f"-Djavax.net.ssl.trustStore={store}",
        "-Djavax.net.ssl.trustStoreType=PKCS12",
    ]
    listed = subprocess.run(
        ["keytool", "-list", "-keystore", str(store), "-storetype", "PKCS12"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "platform" in listed.stdout


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_store_already_given_is_not_made_again(tmp_path: Path) -> None:
    # realm-service made it, then runs apply-realm, which keeps it.
    given = "-Djavax.net.ssl.trustStore=/made/before.p12 -Djavax.net.ssl.trustStoreType=PKCS12"
    done = _applied(tmp_path, {"JAVA_TOOL_OPTIONS": given})
    assert done.returncode == 0, done.stderr
    assert done.stdout == given
    assert not (tmp_path / "realm-trust.p12").exists()
