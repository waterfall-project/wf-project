# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Install the chart on a cluster of kind made for it, bootstrap it, and hold it (US-2800).

Usage: ``python -m wftools.charttrial``.

The chart of ``deploy/helm/waterfall`` is installed on an empty cluster, twice (WF-ARC-0050-A): with
its data components, then with those an operator provides — PostgreSQL, Redis and the object storage
posed beside it by ``wftools.chartdata``, at addresses and with a Secret the operator gives —, on
the one cluster, the first installation removed before the second. The images are tagged
``WATERFALL_IMAGE_TAG`` — the commit of the checkout unless it names another —, which the chain
has just built (``make check-chart``) and which are loaded into the cluster. The cluster,
``WATERFALL_CHART_CLUSTER`` (``waterfall-chart``), is made by kind, with Traefik as its controller
of ingresses, the one k3s ships, and is reached on a free port of the loopback; under a local name,
``waterfall.localhost``, whose certificate an authority of the trial signs, which the front and
this tool alone trust. That authority is the platform's too (``transport.authority``, US-2840): it
signs the certificate of each service, which Traefik reaches in HTTPS without checking it — the
check is the controller's configuration, which a cluster of kind has no root for —, and those of the
data components of the operator, whose root the platform is given apart
(``transport.providedAuthority``). Every secret of the platform is drawn for it. Then it holds, as
``wftools.production`` holds the Compose, and by its functions, that, in each case:

- the installation ends, its hooks included: the migrations, the realm applied, and the bootstrap,
  whose Job wrote the link of the first administrator;
- the API answers its liveness probe, ``status`` ``ok``;
- inside the cluster, every server refuses a connection in the clear and serves in TLS, and nothing
  else answers but the metrics of the API, as ``wftools.production`` holds it of the Compose, by the
  probe of ``wftools.transport`` run in the container of the API (WF-SEC-0010-A, US-2840); on the
  components of the chart, whose servers it names by their Services and whose listeners that must
  not be reached by the addresses of their pods;
- the first administrator sets their password by the link, signs in through the front and Keycloak
  under ``/auth``, behind the ingress, and the front names them;

and, once more:

- on the components of the chart, the API goes from one instance to three by one value,
  ``api.replicas``, under requests held for the whole of the upgrade, none of which fails, and no
  pod that was there — PostgreSQL's included — is replaced or restarted (``wftools.chartload``);
- then, on three instances of the API and two of the worker, the services keep no state
  (WF-ARC-0080-A, US-2820): each instance of the API answers the same to the same token, and a
  worker killed in the middle of a marking leaves the database as it was, the other taking the
  task again (``wftools.chartstateless``);
- then the test of a restoration, as the platform plans it, on a scheduled backup: its environment
  is reachable by no one while it runs, and is gone once it has ended (WF-EXP-0060-A, US-2930,
  ``wftools.chartrestoretest``);
- on the components of the operator's, the chart makes none of its own, and the migrations ended
  before the installation began.

The cluster is deleted at the end, whatever the outcome; what the pods said is printed first when it
fails. The third-party images are read from the mirror when ``WATERFALL_MIRROR`` gives it, with the
credentials of Docker, as the chain logs in.
"""

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
from base64 import b64encode
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from wftools import (
    REPOSITORY,
    chart,
    chartdata,
    chartload,
    chartrestoretest,
    chartstateless,
    kubetools,
)
from wftools.images import DIGEST, REGISTRY
from wftools.production import (
    HIDDEN,
    LIVENESS,
    METRICS,
    NOT_FOUND,
    OK,
    Browser,
    Platform,
    ProductionError,
    Send,
    check_liveness,
    check_metrics_hidden,
    check_signed_in,
    installation_link,
    sender,
    set_password,
    sign_in,
)
from wftools.restoration_trial import access_token
from wftools.transport import Plan, TransportError, check_clear_refused

TOOL = "wftools.charttrial"
NOINDEX = re.compile(
    r'<meta(?=[^>]*\bname="robots")(?=[^>]*\bcontent="[^"]*noindex)[^>]*>', re.IGNORECASE
)
"""The mark Next puts on a page whose status it could not turn into 404, whatever the order of the
attributes of the tag."""

CLUSTER = "waterfall-chart"
DOMAIN = "waterfall.localhost"
NAMESPACE = "waterfall"
ADMIN = "administrateur@waterfall.test"
NODE = (
    "kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5"
)
"""The node of kind 0.33.0 for Kubernetes 1.37, by the digest its release names."""
TRAEFIK = (
    "oci://ghcr.io/traefik/helm/traefik@"
    "sha256:50098cedd13beccdaae2bda8f17091b3eebede130ce73a7b2fc97bb72955e59f"
)
"""The chart of Traefik 42.4.1, the controller of ingresses of the trial, by the digest of its
artifact: a tag moves, the digest does not (as each binary of ``kubetools`` is pinned)."""
NODE_PORT = 30443
"""The port of the node HTTPS is served on, which kind publishes on the loopback."""
CERTIFICATE = "waterfall-tls"
AUTHORITY = "waterfall-authority"
IMAGES = ("front", "waterfall", "keycloak")
INSTALLATION = "20m"
"""How long Helm waits for the hooks: the first start of Keycloak and its realm are the longest."""
ROLLOUT = "10m"
SCALED_TO = 3
"""The instances of the API the trial takes it to, from one: the most the chart is sized for."""
WORKERS = 2
"""The instances of the worker the trial of the services without state holds."""

Run = Callable[[list[str]], int]
Read = Callable[[list[str]], tuple[int, str]]
Ask = Callable[[list[str], str], tuple[int, str]]


def check_console_not_served(browser: Browser, platform: Platform) -> None:
    """Hold that the console of Keycloak and its realm master are not served behind the front.

    Not ``wftools.production.check_console_answers_not_found``, which holds the 404 of Caddy at the
    first request: the ingress sends these paths to the front, which answers as follows.

    The ingress sends these paths to the front, which answers 308 to the address without its
    slash, then shows its screen "not found" with the status 200 and `noindex` (a soft 404, as its
    pages stream), where Caddy answers 404. Either is accepted, if the redirections end on the path
    asked for, the slash apart, on the same host: a redirection to the console or to the sign-in
    page of Keycloak, itself a 200, is the console served. The front renders no stable marker of
    its screen (its texts are translated), so the path reached and `noindex` are what is held.
    """
    for path in HIDDEN:
        url = f"{platform.address}{path}"
        answer, final = browser.follow(browser.request("GET", url), url)
        reached, asked = urlsplit(final), urlsplit(url)
        same = reached.netloc == asked.netloc and reached.path.rstrip("/") == path.rstrip("/")
        soft = answer.status == OK and NOINDEX.search(answer.body) is not None
        if not same or (answer.status != NOT_FOUND and not soft):
            message = (
                f"{path} ends on {answer.status} at {final}, "
                f"not {NOT_FOUND} nor the screen of the front: it is served"
            )
            raise ProductionError(message)


class TrialError(Exception):
    """What the cluster or the chart does not do as it must."""


@dataclass(frozen=True, slots=True)
class Tools:
    """The commands of the trial, each with what it needs: kind, kubectl and Helm."""

    kind: list[str]
    kubectl: list[str]
    helm: list[str]


def tools_of(kubeconfig: Path) -> Tools:
    """Return the pinned commands, kubectl and Helm on the cluster of the trial alone."""
    config = ["--kubeconfig", str(kubeconfig)]
    return Tools(
        [str(kubetools.installed("kind"))],
        [str(kubetools.installed("kubectl")), *config],
        [str(kubetools.installed("helm")), *config],
    )


def drawn_secrets() -> dict[str, str]:
    """Draw every secret of the platform, in the form each asks."""
    drawn = {key: secrets.token_hex(16) for key in chart.SECRET_KEYS}
    # 32 bytes in base64, as the server of Next asks; 64 hexadecimal digits, as Garage does.
    drawn["WATERFALL_SERVER_ACTIONS_KEY"] = b64encode(secrets.token_bytes(32)).decode()
    drawn["WATERFALL_STORAGE_RPC_SECRET"] = secrets.token_hex(32)
    return drawn


def cluster_configuration(port: int, docker_config: Path | None) -> dict[str, Any]:
    """Return the configuration of kind: HTTPS on the loopback, the credentials of Docker given."""
    node: dict[str, Any] = {
        "role": "control-plane",
        "extraPortMappings": [
            {"containerPort": NODE_PORT, "hostPort": port, "listenAddress": "127.0.0.1"}
        ],
    }
    if docker_config is not None:
        node["extraMounts"] = [
            {"hostPath": str(docker_config), "containerPath": "/var/lib/kubelet/config.json"}
        ]
    return {"kind": "Cluster", "apiVersion": "kind.x-k8s.io/v1alpha4", "nodes": [node]}


def chart_values(
    digests: Mapping[str, str],
    platform: Platform,
    ingress_address: str,
    given: Mapping[str, str],
    drawn: Mapping[str, str],
) -> dict[str, Any]:
    """Return the values the chart is installed with on the cluster of the trial, its own data."""
    return {
        "platform": {"domain": platform.domain, "httpsPort": str(platform.https_port)},
        "images": {"digests": dict(digests), "mirror": given.get("WATERFALL_MIRROR", "")},
        "secrets": {"values": dict(drawn)},
        "bootstrap": {"adminEmail": ADMIN, "currency": "EUR", "companyName": "Delmas Automatismes"},
        "ingress": {"className": "traefik", "tlsSecret": CERTIFICATE},
        "transport": {"authority": AUTHORITY},
        # The server of Next reaches Keycloak at the published name, which the cluster does not
        # resolve: to Traefik, inside the cluster, on 443.
        "front": {"hostAliases": [{"ip": ingress_address, "hostnames": [platform.domain]}]},
    }


INSTANCE = f"app.kubernetes.io/instance={chart.RELEASE}"
PODS = ("api", "keycloak", "storage", "front")
"""The components whose pods hold a listener that must not be reached, or the metrics of the API."""


def chart_plan(pods: Mapping[str, str]) -> Plan:
    """Return where the probe of the transport reaches each listener of the chart.

    The servers by the names of their Services, which their certificates name; what must not be
    reached at all by the addresses of the pods, as a pod of the cluster reaches another — the
    Services do not route these ports, the addresses do. ``pods`` gives the address of a pod of
    each of ``PODS``. The management of Keycloak, closed under Compose, answers the probes of the
    kubelet here: it serves in TLS.
    """

    def service(component: str) -> str:
        return f"{chart.RELEASE}-{component}"

    return Plan(
        postgres=(service("postgres"), 5432),
        redis=(service("redis"), 6379),
        served={
            "api": (service("api"), 8443),
            "keycloak": (service("keycloak"), 8443),
            "keycloak-management": (service("keycloak"), 9000),
            "storage": (service("storage"), 3900),
            "prometheus": (service("prometheus"), 9090),
            "alertmanager": (service("alertmanager"), 9093),
            "grafana": (service("grafana"), 3000),
            "front": (service("front"), 3443),
        },
        closed={
            "keycloak-http": (pods["keycloak"], 8080),
            "keycloak-cluster": (pods["keycloak"], 7800),
            "keycloak-cluster-detection": (pods["keycloak"], 57800),
            "garage": (pods["storage"], 3902),
            "garage-rpc": (pods["storage"], 3901),
            "front-http": (pods["front"], 3000),
        },
        metrics=(pods["api"], 8000),
    )


def free_port() -> int:
    """Return a port of the loopback no one listens on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def _must(run: Run, command: list[str], what: str) -> None:
    """Run a command that must succeed; fail naming what it was for — its words say not."""
    if code := run(command):
        message = f"{what} failed ({code})"
        raise TrialError(message)


def _output(read: Read, command: list[str], what: str) -> str:
    """Run a command that must succeed and return what it wrote; fail naming what it was for."""
    code, output = read(command)
    if code != 0:
        message = f"{what} failed ({code})"
        raise TrialError(message)
    return output


KEY = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-noenc"]
"""A key of the trial, made with its request: P-256, unencrypted."""


def make_authority(read: Read, folder: Path, domain: str) -> None:
    """Make an authority of the trial, and the certificate of the domain it signs, by OpenSSL."""
    authority = folder / "ca"
    _output(
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
    _output(
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
    _output(
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


@dataclass(frozen=True, slots=True)
class Trial:
    """The cluster of the trial: its commands, its files, and where the platform is published."""

    tools: Tools
    run: Run
    read: Read
    folder: Path
    platform: Platform
    ask: Ask | None = None

    @property
    def kubeconfig(self) -> str:
        """Return the file kind writes the access to the cluster to: never the user's own."""
        return str(self.folder / "kubeconfig")

    @property
    def kubectl(self) -> list[str]:
        """Return kubectl on the namespace of the platform."""
        return [*self.tools.kubectl, "--namespace", NAMESPACE]

    def create(self, name: str, docker_config: Path | None) -> None:
        """Make the cluster, publishing HTTPS on the loopback."""
        configuration = self.folder / "kind.json"
        configuration.write_text(
            json.dumps(cluster_configuration(self.platform.https_port, docker_config)),
            encoding="utf-8",
        )
        _must(
            self.run,
            [
                *self.tools.kind,
                "create",
                "cluster",
                "--name",
                name,
                "--image",
                NODE,
                "--config",
                str(configuration),
                "--kubeconfig",
                self.kubeconfig,
                "--wait",
                "5m",
            ],
            "create the cluster",
        )

    def load(self, name: str, tag: str) -> dict[str, str]:
        """Load the images of the tag, built on the workstation, into the cluster.

        Return the digest of each, as the runtime of the node holds it: the chart designates them
        so (#3726), and the kubelet finds them by it.
        """
        references = {image: f"{REGISTRY}/{image}:{tag}" for image in IMAGES}
        for reference in references.values():
            if self.run(["docker", "image", "inspect", "--format", "{{.Id}}", reference]):
                message = f"{reference} is not built here: make images first"
                raise TrialError(message)
        _must(
            self.run,
            [*self.tools.kind, "load", "docker-image", "--name", name, *references.values()],
            "load the images into the cluster",
        )
        return {
            image: self.digest(f"{name}-control-plane", reference)
            for image, reference in references.items()
        }

    def digest(self, node: str, reference: str) -> str:
        """Make the node hold an image by its digest too, and return it.

        ``kind load`` leaves an image under its tag, and ``crictl`` names no digest of it but the
        import's: the kubelet would not find ``name@sha256:…``. ``ctr`` lists the digest of the
        image under the tag, the node is told to name it so, and the runtime to find it.
        """
        containerd = ["docker", "exec", node, "ctr", "--namespace=k8s.io", "images"]
        listing = [*containerd, "ls", f"name=={reference}"]
        listed = _output(self.read, listing, f"read the digest of {reference}")
        if not (found := DIGEST.search(listed)):
            message = f"the cluster holds {reference} by no digest"
            raise TrialError(message)
        named = f"{reference.rsplit(':', 1)[0]}@{found.group(0)}"
        tag = [*containerd, "tag", "--force", reference, named]
        _must(self.run, tag, f"name {named} by its digest")
        find = ["docker", "exec", node, "crictl", "inspecti", named]
        _output(self.read, find, f"find {named} in the cluster")
        return found.group(0)

    def ingress(self) -> str:
        """Install Traefik, serving HTTPS on the port of the node; return its address inside.

        It reaches the front, Keycloak and Grafana in HTTPS, by the name https of the port of their
        Services, without checking their certificates: Traefik checks a server by the address it
        dials, an address of a pod, which no certificate names, unless a resource of its own says
        another name, which the chart does not write (WF-CMP-0020, docs/exploitation/
        chiffrement-chart.md).
        """
        settings = [
            "service.spec.type=NodePort",
            f"ports.websecure.nodePort={NODE_PORT}",
            "additionalArguments[0]=--serversTransport.insecureSkipVerify=true",
        ]
        _must(
            self.run,
            [
                *self.tools.helm,
                "install",
                "traefik",
                TRAEFIK,
                "--namespace",
                "traefik",
                "--create-namespace",
                "--set",
                ",".join(settings),
                "--wait",
                "--timeout",
                "5m",
            ],
            "install Traefik",
        )
        command = [*self.tools.kubectl, "--namespace", "traefik", "get", "service", "traefik"]
        found = _output(
            self.read,
            [*command, "--output", "jsonpath={.spec.clusterIP}"],
            "read the address of Traefik",
        )
        return found.strip()

    def prepare(self) -> None:
        """Make the namespace of the platform, with its certificate and the authority.

        The authority is the platform's: its certificate and its key, which sign the certificates of
        the services (US-2840).
        """
        _must(
            self.run,
            [*self.tools.kubectl, "create", "namespace", NAMESPACE],
            "create the namespace",
        )
        certificate = self.folder / "tls"
        _must(
            self.run,
            [
                *self.kubectl,
                "create",
                "secret",
                "tls",
                CERTIFICATE,
                "--cert",
                f"{certificate}.crt",
                "--key",
                f"{certificate}.key",
            ],
            "make the secret of the certificate",
        )
        _must(
            self.run,
            [
                *self.kubectl,
                "create",
                "secret",
                "generic",
                AUTHORITY,
                f"--from-file=ca.crt={self.folder / 'ca.crt'}",
                f"--from-file=ca.key={self.folder / 'ca.key'}",
            ],
            "make the secret of the authority",
        )

    def provide(self, drawn: Mapping[str, str], mirror: str) -> None:
        """Pose the data components of an operator, and the Secret of the platform it gives.

        The Secret holds the keys of the platform, as the operator makes it before the installation:
        from a file, never the command line, which the processes of the workstation list. Each
        component serves in TLS, with the certificate the authority of the trial issues for its
        name; the operator gives the root of them to the platform apart (``chartdata.ROOTS``).
        """
        for component in chartdata.COMPONENTS:
            issue(self.read, self.folder, component, chartdata.host(component))
        manifests = self.folder / "data.json"
        manifests.write_text(
            json.dumps(
                {"apiVersion": "v1", "kind": "List", "items": chartdata.manifests(drawn, mirror)}
            ),
            encoding="utf-8",
        )
        _must(
            self.run,
            [*self.tools.kubectl, "apply", "--filename", str(manifests)],
            "pose the data components of the operator",
        )
        data = [*self.tools.kubectl, "--namespace", chartdata.NAMESPACE]
        for component in chartdata.COMPONENTS:
            _must(
                self.run,
                [
                    *data,
                    "create",
                    "secret",
                    "generic",
                    chartdata.certificates(component),
                    f"--from-file=tls.crt={self.folder / f'{component}.crt'}",
                    f"--from-file=tls.key={self.folder / f'{component}.key'}",
                    f"--from-file=ca.crt={self.folder / 'ca.crt'}",
                ],
                f"make the secret of the certificate of {component}",
            )
        _must(
            self.run,
            [
                *self.kubectl,
                "create",
                "secret",
                "generic",
                chartdata.ROOTS,
                f"--from-file=ca.crt={self.folder / 'ca.crt'}",
            ],
            "make the secret of the roots of the data components",
        )
        _must(
            self.run,
            [*data, "rollout", "status", "deployment", "--timeout", ROLLOUT],
            "wait for the data components of the operator",
        )
        environment = self.folder / "secret.env"
        environment.write_text(
            "".join(f"{key}={value}\n" for key, value in drawn.items()), encoding="utf-8"
        )
        _must(
            self.run,
            [
                *self.kubectl,
                "create",
                "secret",
                "generic",
                chartdata.KEYS,
                f"--from-env-file={environment}",
            ],
            "make the secret of the operator",
        )
        print("  PostgreSQL, Redis and the object storage are posed beside the chart", flush=True)

    def install(self, values: Mapping[str, Any]) -> None:
        """Install the chart, with its hooks, and wait for what it deploys."""
        given = self.folder / "values.json"
        given.write_text(json.dumps(values), encoding="utf-8")
        _must(
            self.run,
            [
                *self.tools.helm,
                "install",
                chart.RELEASE,
                str(chart.CHART),
                "--namespace",
                NAMESPACE,
                "--values",
                str(given),
                "--timeout",
                INSTALLATION,
            ],
            "install the chart",
        )
        print("  the chart is installed, its hooks done: migrations, realm, bootstrap", flush=True)
        self.rolled_out()

    def rolled_out(self) -> None:
        """Wait until every deployment and statefulset of the platform is rolled out."""
        for kind in ("deployment", "statefulset"):
            _must(
                self.run,
                [*self.kubectl, "rollout", "status", kind, "--timeout", ROLLOUT],
                f"wait for the rollout of the {kind}s",
            )
        print("  every deployment and statefulset is rolled out", flush=True)

    def hold(self, email: str) -> Browser:
        """Hold the bootstrap, the liveness of the API, the sign-in of the first administrator.

        Return the browser, signed in, which holds the session the requests of an upgrade reuse.
        """
        logs = _output(
            self.read,
            [*self.kubectl, "logs", f"job/{chart.RELEASE}-install"],
            "read the log of the bootstrap",
        )
        link = installation_link(logs, self.platform)
        print("  the bootstrap wrote the link of the first administrator", flush=True)
        api = f"deployment/{chart.RELEASE}-api"
        alive = _output(
            self.read,
            [*self.kubectl, "exec", api, "--", "python", "-c", LIVENESS],
            "ask the API for its liveness",
        )
        check_liveness(alive)
        print("  the API answers its liveness probe: ok", flush=True)
        browser = Browser(self.sender())
        check_console_not_served(browser, self.platform)
        print("  the console of Keycloak and its realm master are not served: ok", flush=True)
        check_metrics_hidden(browser, self.platform)
        print(f"  {' and '.join(METRICS)} answer {NOT_FOUND} at the ingress: ok", flush=True)
        password = f"Trial-{secrets.token_urlsafe(18)}"
        set_password(browser, link, password)
        print("  the first administrator sets their password by the link", flush=True)
        sign_in(browser, self.platform, email, password)
        check_signed_in(browser, self.platform, email)
        print(
            f"  the first administrator signs in at {self.platform.address}; the front names them",
            flush=True,
        )
        return browser

    def hold_transport(self) -> None:
        """Hold that every server refuses the clear and serves in TLS, inside the cluster.

        The probe runs in the container of the API, which trusts the root of the platform, on the
        plan of the chart (``chart_plan``).
        """
        pods: dict[str, str] = {}
        for component in PODS:
            selector = f"{INSTANCE},app.kubernetes.io/component={component}"
            pods[component] = _output(
                self.read,
                [
                    *self.kubectl,
                    "get",
                    "pods",
                    "--selector",
                    selector,
                    "--field-selector",
                    "status.phase=Running",
                    "--output",
                    "jsonpath={.items[0].status.podIP}",
                ],
                f"read the address of a pod of {component}",
            ).strip()
        plan = chart_plan(pods)
        said = _output(
            self.read,
            [*self.kubectl, "exec", f"deployment/{chart.RELEASE}-api", "--", *plan.command()],
            "try every server in the clear",
        )
        try:
            check_clear_refused(said, plan)
        except TransportError as error:
            raise TrialError(str(error)) from error
        print(
            f"  {', '.join(plan.servers())} refuse a connection in the clear, and serve in TLS; "
            f"{', '.join(plan.closed)} are not reached",
            flush=True,
        )

    def sender(self) -> Send:
        """Return the sender of the requests: it trusts the authority of the trial alone."""
        return sender(self.platform)(self.folder / "ca.crt")

    def pods(self) -> dict[str, tuple[str, int]]:
        """Return the pods of the platform that run, by name: their identifier and restarts."""
        selector = f"app.kubernetes.io/instance={chart.RELEASE}"
        listing = _output(
            self.read,
            [*self.kubectl, "get", "pods", "--selector", selector, "--output", "json"],
            "list the pods of the platform",
        )
        return chartload.pods_of(json.loads(listing))

    def upgrade(self, values: Mapping[str, Any]) -> None:
        """Upgrade the installed chart to ``values``, and wait for Helm to see it through."""
        given = self.folder / "values.json"
        given.write_text(json.dumps(values), encoding="utf-8")
        command = [
            *self.tools.helm,
            "upgrade",
            chart.RELEASE,
            str(chart.CHART),
            "--namespace",
            NAMESPACE,
            "--values",
            str(given),
            "--wait",
            "--timeout",
            INSTALLATION,
        ]
        _must(self.run, command, "upgrade the chart to the values given")

    def scale(self, values: Mapping[str, Any], browser: Browser, email: str, replicas: int) -> None:
        """Take the API to ``replicas`` instances by its one value, under requests none may fail.

        The chart is upgraded with the same values but that one. Requests of the first
        administrator, signed in, are held from before the upgrade until every instance is ready;
        none may fail, and no pod there was before may be replaced or restarted.
        """
        before = self.pods()
        scaled = {**values, "api": {**values.get("api", {}), "replicas": replicas}}
        with chartload.requests_held(self.sender(), browser, self.platform, email) as held:
            self.upgrade(scaled)
            self.rolled_out()
        chartload.check_uninterrupted(held)
        print(f"  {held.sent} requests were held through the upgrade, none failed", flush=True)
        chartload.check_untouched(before, self.pods())
        ready = _output(
            self.read,
            [
                *self.kubectl,
                "get",
                f"deployment/{chart.RELEASE}-api",
                "--output",
                "jsonpath={.status.readyReplicas}",
            ],
            "count the instances of the API that are ready",
        )
        if ready.strip() != str(replicas):
            message = f"{ready.strip() or 'none'} instances of the API are ready, not {replicas}"
            raise TrialError(message)
        print(
            f"  the API goes from one instance to {replicas} by api.replicas; "
            f"the {len(before)} pods there were are the same, none restarted",
            flush=True,
        )

    def hold_stateless(self, values: Mapping[str, Any], browser: Browser) -> None:
        """Hold the services stateless, on three instances of the API and two of the worker.

        The worker goes to two instances by its one value, ``worker.replicas``; the first
        administrator, signed in, gives a token of their own as the front takes one
        (``wftools.chartstateless``).
        """
        grown = {
            **values,
            "api": {**values.get("api", {}), "replicas": SCALED_TO},
            "worker": {**values.get("worker", {}), "replicas": WORKERS},
        }
        self.upgrade(grown)
        self.rolled_out()
        secret = values["secrets"]["values"]["WATERFALL_FRONT_CLIENT_SECRET"]
        token = access_token(browser, self.sender(), self.platform.address, secret)
        ask = self.ask or _ask
        chartstateless.Stateless(self.kubectl, self.read, ask, chartstateless.started).hold(token)

    def hold_restore_test(self, tag: str) -> None:
        """Play the test of a restoration as the platform plans it: closed while it runs, then gone.

        The probe of its ports runs the image of the tag, which the cluster holds.
        """
        image = f"{REGISTRY}/waterfall:{tag}"
        chartrestoretest.RestoreTestTrial(self.kubectl, self.read, image).hold()

    def hold_provided(self) -> None:
        """Hold that the chart made no data component, and that it migrated before it installed."""
        found = _output(
            self.read,
            [
                *self.kubectl,
                "get",
                "pods",
                "--selector",
                f"app.kubernetes.io/component in ({','.join(chartdata.COMPONENTS)})",
                "--output",
                "name",
            ],
            "list the data components of the chart",
        ).split()
        if found:
            message = f"the chart made its own {', '.join(found)}, the operator providing them"
            raise TrialError(message)
        print("  the chart made no PostgreSQL, Redis or storage of its own: ok", flush=True)
        migrate = f"job/{chart.RELEASE}-migrate"
        api = f"deployment/{chart.RELEASE}-api"
        done = _output(
            self.read,
            [*self.kubectl, "get", migrate, "--output", "jsonpath={.status.completionTime}"],
            "read when the migrations ended",
        ).strip()
        began = _output(
            self.read,
            [*self.kubectl, "get", api, "--output", "jsonpath={.metadata.creationTimestamp}"],
            "read when the installation began",
        ).strip()
        chartload.check_before(done, began)
        print(
            f"  the migrations ended at {done}, before the installation began at {began}",
            flush=True,
        )

    def remove(self) -> None:
        """Remove the installation and its namespaces, to make the next one on the cluster."""
        _must(
            self.run,
            [*self.tools.helm, "uninstall", chart.RELEASE, "--namespace", NAMESPACE],
            "uninstall the chart",
        )
        for namespace in (NAMESPACE, chartdata.NAMESPACE):
            _must(
                self.run,
                [
                    *self.tools.kubectl,
                    "delete",
                    "namespace",
                    namespace,
                    "--ignore-not-found",
                    "--timeout",
                    ROLLOUT,
                ],
                f"delete the namespace {namespace}",
            )

    def report(self) -> None:
        """Print what the pods of the platform are and said, when the trial fails."""
        self.run([*self.tools.kubectl, "get", "pods", "--all-namespaces", "--output", "wide"])
        self.run([*self.kubectl, "get", "events", "--sort-by", ".lastTimestamp"])
        selectors = (
            (NAMESPACE, f"app.kubernetes.io/instance={chart.RELEASE}"),
            (chartdata.NAMESPACE, f"app.kubernetes.io/managed-by={chartdata.MANAGER}"),
        )
        for namespace, selector in selectors:
            self.run(
                [
                    *self.tools.kubectl,
                    "--namespace",
                    namespace,
                    "logs",
                    "--all-containers",
                    "--prefix",
                    "--tail",
                    "100",
                    "--selector",
                    selector,
                ]
            )


def docker_config_of(environment: Mapping[str, str]) -> Path | None:
    """Return the credentials of Docker the node pulls with, when the mirror is to be read."""
    if not environment.get("WATERFALL_MIRROR"):
        return None
    folder = environment.get("DOCKER_CONFIG") or str(Path.home() / ".docker")
    path = Path(folder) / "config.json"
    return path if path.exists() else None


def main(environment: Mapping[str, str] | None = None) -> int:
    """Make the cluster, install the chart on both footings and hold it, then delete the cluster."""
    given = dict(os.environ if environment is None else environment)
    name = given.get("WATERFALL_CHART_CLUSTER") or CLUSTER
    platform = Platform(DOMAIN, free_port(), 0)
    with tempfile.TemporaryDirectory(prefix="waterfall-chart-trial-") as folder:
        try:
            tag = given.get("WATERFALL_IMAGE_TAG") or _head()
            trial = Trial(
                tools_of(Path(folder) / "kubeconfig"), _run, _read, Path(folder), platform
            )
        except (kubetools.ToolError, OSError, subprocess.CalledProcessError) as error:
            print(f"{TOOL}: {error}", file=sys.stderr)
            return 1
        print(f"  the images {tag}, on the cluster {name}, at {platform.address}", flush=True)
        failed = True
        try:
            make_authority(_read, Path(folder), DOMAIN)
            trial.create(name, docker_config_of(given))
            digests = trial.load(name, tag)
            address = trial.ingress()
            drawn = drawn_secrets()
            values = chart_values(digests, platform, address, given, drawn)
            print("the chart, on the data components it makes:", flush=True)
            trial.prepare()
            trial.install(values)
            browser = trial.hold(ADMIN)
            trial.hold_transport()
            trial.scale(values, browser, ADMIN, SCALED_TO)
            trial.hold_stateless(values, browser)
            trial.hold_restore_test(tag)
            trial.remove()
            print("the chart, on the data components of an operator:", flush=True)
            trial.prepare()
            trial.provide(drawn, given.get("WATERFALL_MIRROR", ""))
            trial.install(chartdata.provided_values(values))
            trial.hold(ADMIN)
            trial.hold_provided()
            failed = False
        except (TrialError, ProductionError, OSError) as error:
            print(f"{TOOL}: {error}", file=sys.stderr)
            return 1
        finally:
            if failed:
                trial.report()
            _run([*trial.tools.kind, "delete", "cluster", "--name", name])
    return 0


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, capture_output=True, text=True, check=True
    ).stdout.strip()


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPOSITORY, check=False).returncode


def _ask(command: list[str], given: str) -> tuple[int, str]:
    done = subprocess.run(
        command, cwd=REPOSITORY, input=given, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        print(done.stderr, file=sys.stderr)
    return done.returncode, done.stdout


def _read(command: list[str]) -> tuple[int, str]:
    done = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        print(done.stderr, file=sys.stderr)
    return done.returncode, done.stdout


if __name__ == "__main__":
    sys.exit(main())
