# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The trial of the chart on a cluster of kind, and the tools it pins (US-2800).

The cluster is made, the chart installed and the first administrator signed in by ``make
chart-trial`` in the full tier of the chain; these tests hold what the trial and the installation of
Helm, kind and kubectl decide by themselves, without a cluster nor a download.
"""

import ast
import base64
import hashlib
import io
import re
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from wftools import chart, charttrial, kubetools
from wftools.charttrial import Tools, Trial, TrialError
from wftools.kubetools import Binary, ToolError
from wftools.production import HIDDEN, Answer, Browser, Platform, ProductionError

if TYPE_CHECKING:
    from collections.abc import Callable

PLATFORM = Platform("waterfall.localhost", 41443, 0)


def archive(member: str, content: bytes) -> bytes:
    """Return a gzipped tarball holding one file."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as written:
        info = tarfile.TarInfo(member)
        info.size = len(content)
        written.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_a_tool_is_taken_from_its_archive_at_the_digest_pinned() -> None:
    payload = archive("linux-amd64/helm", b"the binary")
    binary = Binary(
        "helm",
        "1",
        "https://x/helm.tar.gz",
        hashlib.sha256(payload).hexdigest(),
        "linux-amd64/helm",
    )
    assert kubetools.extracted(binary, payload) == b"the binary"


def test_a_tool_that_is_the_release_itself_is_taken_as_it_is() -> None:
    binary = Binary("kind", "1", "https://x/kind", hashlib.sha256(b"kind").hexdigest())
    assert kubetools.extracted(binary, b"kind") == b"kind"


def test_a_download_of_another_digest_is_refused() -> None:
    binary = Binary("kind", "1", "https://x/kind", "0" * 64)
    with pytest.raises(ToolError, match="not the one pinned"):
        kubetools.extracted(binary, b"another")


def test_each_tool_lives_in_a_folder_of_its_version(tmp_path: Path) -> None:
    assert (
        kubetools.location(kubetools.BINARIES["helm"], tmp_path) == tmp_path / "helm-4.3.2" / "helm"
    )
    assert kubetools.cache({"XDG_CACHE_HOME": str(tmp_path)}) == tmp_path / "waterfall" / "bin"
    assert all(re.fullmatch(r"[0-9a-f]{64}", tool.sha256) for tool in kubetools.BINARIES.values())


def test_every_secret_is_drawn_in_the_form_it_is_asked() -> None:
    drawn = charttrial.drawn_secrets()
    assert set(drawn) == set(chart.SECRET_KEYS)
    # A password written in a URL holds letters and digits alone.
    assert drawn["WATERFALL_REDIS_PASSWORD"].isalnum()
    assert len(base64.b64decode(drawn["WATERFALL_SERVER_ACTIONS_KEY"])) == 32
    assert re.fullmatch(r"[0-9a-f]{64}", drawn["WATERFALL_STORAGE_RPC_SECRET"])
    assert charttrial.drawn_secrets() != drawn


def test_the_cluster_publishes_https_on_the_loopback_alone(tmp_path: Path) -> None:
    configuration = charttrial.cluster_configuration(41443, None)
    (node,) = configuration["nodes"]
    assert node["extraPortMappings"] == [
        {"containerPort": charttrial.NODE_PORT, "hostPort": 41443, "listenAddress": "127.0.0.1"}
    ]
    assert "extraMounts" not in node
    (node,) = charttrial.cluster_configuration(41443, tmp_path / "config.json")["nodes"]
    assert node["extraMounts"] == [
        {"hostPath": str(tmp_path / "config.json"), "containerPath": "/var/lib/kubelet/config.json"}
    ]


def test_the_node_pulls_with_the_credentials_of_docker_only_from_the_mirror(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    mirror = {
        "WATERFALL_MIRROR": "ghcr.io/waterfall-project/mirror/",
        "DOCKER_CONFIG": str(tmp_path),
    }
    assert charttrial.docker_config_of(mirror) == tmp_path / "config.json"
    assert charttrial.docker_config_of({"DOCKER_CONFIG": str(tmp_path)}) is None
    assert charttrial.docker_config_of({**mirror, "DOCKER_CONFIG": str(tmp_path / "none")}) is None


def test_the_front_reaches_the_published_name_at_the_ingress_inside_the_cluster() -> None:
    drawn = charttrial.drawn_secrets()
    values = charttrial.chart_values(
        "abc", PLATFORM, "10.96.0.7", {"WATERFALL_MIRROR": "m/"}, drawn
    )
    assert values["secrets"] == {"values": drawn}
    assert values["platform"] == {"domain": "waterfall.localhost", "httpsPort": "41443"}
    assert values["images"] == {"tag": "abc", "mirror": "m/"}
    assert values["front"]["hostAliases"] == [
        {"ip": "10.96.0.7", "hostnames": ["waterfall.localhost"]}
    ]
    assert values["ingress"] == {"className": "traefik", "tlsSecret": charttrial.CERTIFICATE}
    assert values["transport"] == {"authority": charttrial.AUTHORITY}


def test_an_image_not_built_here_stops_the_trial_before_the_cluster_loads_any(
    tmp_path: Path,
) -> None:
    ran: list[list[str]] = []

    def run(command: list[str]) -> int:
        ran.append(command)
        return 1 if command[-1].endswith("/keycloak:abc") else 0

    trial = Trial(
        Tools(["kind"], ["kubectl"], ["helm"]), run, lambda _: (0, ""), tmp_path, PLATFORM
    )
    with pytest.raises(TrialError, match="keycloak:abc is not built here"):
        trial.load("cluster", "abc")
    assert not any(command[0] == "kind" for command in ran)


@pytest.mark.parametrize(
    ("tool", "method", "what"),
    [
        ("kubectl", "prepare", "create the namespace"),
        ("helm", "install", "install the chart"),
        ("kind", "create", "create the cluster"),
        ("helm", "ingress", "install Traefik"),
        ("kubectl", "provide", "pose the data components of the operator"),
        ("kubectl", "pods", "list the pods of the platform"),
        ("kind", "load", "load the images into the cluster"),
    ],
    ids=["namespace", "helm install", "kind create", "traefik", "operator data", "pods", "load"],
)
def test_a_failed_command_is_named_by_what_it_was_for_not_by_its_words(
    tmp_path: Path, tool: str, method: str, what: str
) -> None:
    arguments: dict[str, tuple[object, ...]] = {
        "install": ({},),
        "create": ("cluster", None),
        "provide": (charttrial.drawn_secrets(), ""),
        "load": ("cluster", "abc"),
    }

    def run(command: list[str]) -> int:
        return 1 if command[0] == tool else 0

    def read(command: list[str]) -> tuple[int, str]:
        return (1, "") if command[0] == tool else (0, "")

    trial = Trial(
        Tools(["kind"], ["kubectl", "--kubeconfig", "k"], ["helm", "--kubeconfig", "k"]),
        run,
        read,
        tmp_path,
        PLATFORM,
    )
    # The last words of a command are its flags and its values: the message says what it was for.
    with pytest.raises(TrialError, match=rf"^{what} failed \(1\)$"):
        getattr(trial, method)(*arguments.get(method, ()))


def test_traefik_is_pulled_by_the_digest_of_its_artifact() -> None:
    assert re.search(r"@sha256:[0-9a-f]{64}$", charttrial.TRAEFIK)


def test_the_trial_holds_that_the_console_and_the_master_realm_are_not_served(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []
    metrics: list[str] = []

    def nothing(*_: object, **__: object) -> None:
        return None

    def link(*_: object) -> str:
        return "link"

    def sender(_: Platform) -> Callable[[Path], object]:
        return lambda _ca: object()

    def browser(sent: object) -> object:
        return sent

    def hidden(_browser: object, platform: Platform) -> None:
        seen.append(platform.domain)

    def metrics_hidden(_browser: object, platform: Platform) -> None:
        metrics.append(platform.domain)

    for name in (
        "check_liveness",
        "set_password",
        "sign_in",
        "check_signed_in",
    ):
        monkeypatch.setattr(charttrial, name, nothing)
    monkeypatch.setattr(charttrial, "installation_link", link)
    monkeypatch.setattr(charttrial, "sender", sender)
    monkeypatch.setattr(charttrial, "Browser", browser)
    monkeypatch.setattr(charttrial, "check_console_not_served", hidden)
    monkeypatch.setattr(charttrial, "check_metrics_hidden", metrics_hidden)
    trial = Trial(
        Tools(["kind"], ["kubectl"], ["helm"]), lambda _: 0, lambda _: (0, "x"), tmp_path, PLATFORM
    )
    trial.hold("a@b.test")
    assert seen == ["waterfall.localhost"]
    assert metrics == ["waterfall.localhost"]


def _console_browser(answers: dict[str, Answer]) -> Browser:
    def send(_method: str, url: str, _body: object, _headers: object) -> Answer:
        return answers[url]

    return Browser(send)


SOFT = '<meta name="robots" content="noindex"/>'
LOGIN = "/auth/realms/master/protocol/openid-connect/auth"
CONSOLE = "/auth/admin/master/console/"


def _answers(path: str, *steps: tuple[str, Answer]) -> dict[str, Answer]:
    base = PLATFORM.address
    return {f"{base}{where}": answer for where, answer in steps} | {
        f"{base}{other}": Answer(404, (), "") for other in HIDDEN if other != path
    }


def _moved(to: str) -> Answer:
    return Answer(308, (("Location", to),), "")


@pytest.mark.parametrize("path", HIDDEN)
@pytest.mark.parametrize(
    "steps",
    [
        [("", Answer(404, (), ""))],
        [("", _moved("{bare}")), ("{bare}", Answer(404, (), ""))],
        [("", _moved("{bare}")), ("{bare}", Answer(200, (), SOFT))],
        [
            ("", _moved("{bare}")),
            ("{bare}", Answer(200, (), '<meta content="noindex" name="robots">')),
        ],
    ],
    ids=["404", "308 then 404", "308 then soft 404", "attributes in any order"],
)
def test_the_console_behind_the_front_is_hidden_once_its_redirection_is_followed(
    path: str, steps: list[tuple[str, Answer]]
) -> None:
    bare = path.rstrip("/")
    filled = [
        (where.replace("{bare}", bare) or path, _fill(answer, bare)) for where, answer in steps
    ]
    answers = _answers(path, *filled)
    charttrial.check_console_not_served(_console_browser(answers), PLATFORM)


def _fill(answer: Answer, bare: str) -> Answer:
    return Answer(
        answer.status, tuple((k, v.replace("{bare}", bare)) for k, v in answer.headers), answer.body
    )


@pytest.mark.parametrize("path", HIDDEN)
@pytest.mark.parametrize(
    ("steps", "ends"),
    [
        (
            [
                ("", _moved(LOGIN)),
                (LOGIN, Answer(200, (), '<meta name="robots" content="noindex, nofollow">')),
            ],
            f"ends on 200 at {PLATFORM.address}{LOGIN}",
        ),
        (
            [("", _moved(CONSOLE)), (CONSOLE, Answer(200, (), SOFT))],
            f"ends on 200 at {PLATFORM.address}{CONSOLE}",
        ),
        (
            [("", _moved(LOGIN)), (LOGIN, Answer(404, (), ""))],
            f"ends on 404 at {PLATFORM.address}{LOGIN}",
        ),
        ([("", Answer(200, (), "console"))], "ends on 200 at"),
        ([("", Answer(200, (), "<p>noindex</p>"))], "ends on 200 at"),
        (
            [("", Answer(200, (), '<meta name="description" content="noindex">'))],
            "ends on 200 at",
        ),
        ([("", Answer(200, (), '<meta name="robots" content="index, follow">'))], "ends on 200 at"),
        ([("", Answer(401, (), ""))], "ends on 401 at"),
        ([("", Answer(403, (), SOFT))], "ends on 403 at"),
        ([("", Answer(500, (), ""))], "ends on 500 at"),
    ],
    ids=[
        "redirected to the login of master",
        "redirected to the console",
        "redirected elsewhere then 404",
        "200 without noindex",
        "noindex in the text",
        "noindex of another meta",
        "robots that index",
        "401",
        "403 with noindex",
        "500",
    ],
)
def test_the_console_served_or_the_redirection_elsewhere_is_refused(
    path: str, steps: list[tuple[str, Answer]], ends: str
) -> None:
    filled = [(where or path, answer) for where, answer in steps]
    answers = _answers(path, *filled)
    with pytest.raises(ProductionError, match=rf"^{re.escape(path)} {ends}.*it is served$"):
        charttrial.check_console_not_served(_console_browser(answers), PLATFORM)


@pytest.mark.parametrize("path", HIDDEN)
@pytest.mark.parametrize(
    "ending", [Answer(404, (), ""), Answer(200, (), SOFT)], ids=["404", "soft"]
)
def test_a_redirection_to_another_host_is_refused_whatever_it_ends_on(
    path: str, ending: Answer
) -> None:
    # The same path on another host: only the host tells it from the platform.
    other = f"https://elsewhere.example:41443{path}"
    answers = _answers(path, (path, _moved(other)))
    answers[other] = ending
    with pytest.raises(ProductionError, match=r"at https://elsewhere\.example.*it is served$"):
        charttrial.check_console_not_served(_console_browser(answers), PLATFORM)


@pytest.mark.parametrize("path", HIDDEN)
def test_a_soft_404_at_the_path_asked_is_accepted_without_any_redirection(path: str) -> None:
    answers = _answers(path, (path, Answer(200, (), SOFT)))
    charttrial.check_console_not_served(_console_browser(answers), PLATFORM)


LABEL_AT = 2
LEAST_COMMANDS = 20
LEAST_WORDS = 2


def _labelled_calls() -> list[tuple[int, ast.expr | None]]:
    """List every call of `_must` and `_output` of the module, with the label it passes."""
    tree = ast.parse(Path(charttrial.__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"_must", "_output"}
    ]
    return [
        (call.lineno, call.args[LABEL_AT] if len(call.args) > LABEL_AT else None)
        for call in sorted(calls, key=lambda each: each.lineno)
    ]


def test_every_command_of_the_trial_is_named_by_what_it_is_for() -> None:
    calls = _labelled_calls()
    # A guard against the walk finding nothing: the module runs more than twenty such commands.
    assert len(calls) >= LEAST_COMMANDS
    for line, label in calls:
        assert label is not None, f"line {line}: the command has no label"
        # A literal, or an f-string whose literal parts are the words of the label.
        if isinstance(label, ast.Constant):
            words = str(label.value).split()
        else:
            assert isinstance(label, ast.JoinedStr), f"line {line}: the label is computed"
            words = " ".join(
                str(part.value) for part in label.values if isinstance(part, ast.Constant)
            ).split()
        assert len(words) >= LEAST_WORDS, f"line {line}: {words} does not say what it is for"
        assert words[0] not in {"kubectl", "helm", "kind", "openssl", "docker"}, f"line {line}"
