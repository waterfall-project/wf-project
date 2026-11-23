# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The alerts of the platform, as Prometheus evaluates them (US-2880, WF-OBS-0030).

The rules are one model, deploy/compose/prometheus-alerts.yml, whose three thresholds the Compose
writes at the start of Prometheus (prometheus.sh) and the chart at its rendering
(templates/_prometheus.tpl). These tests write them both ways, then play each alert on series by
promtool, the rules engine of the release of Prometheus the platform runs: it appears with its
cause, at the threshold, and ends with it. Selected by the marker ``chart`` (``make test-chart``):
they need Helm and promtool, which ``make kube-tools`` installs and the tools leave out.
"""

import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, chart, kubetools

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.chart]

COMPOSE = REPOSITORY / "deploy" / "compose"
START = COMPOSE / "prometheus.sh"
QUEUE = "WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS"
STORAGE = "WATERFALL_STORAGE_USAGE_THRESHOLD"
ERRORS = "WATERFALL_ERROR_RATE_THRESHOLD"
WINDOW = "WATERFALL_ERROR_RATE_WINDOW_SECONDS"
# The thresholds WF-OBS-0030 ships: fifteen minutes, 85 %, 5 % over five minutes.
SHIPPED = {QUEUE: "900", STORAGE: "0.85", ERRORS: "0.05", WINDOW: "300"}
# The values of the chart that hold each one.
VALUES = {
    QUEUE: "taskQueueAgeSeconds",
    STORAGE: "storageUsage",
    ERRORS: "errorRate",
    WINDOW: "errorRateWindowSeconds",
}
ALERT = {"severity": "alert"}

# An alert expected at a minute: its name, and the labels of each instance of it that fires.
Expected = list[tuple[int, str, list[dict[str, str]]]]


def by_compose(folder: Path, **thresholds: str) -> Path:
    """Write the configuration and the rules as Prometheus starts under Compose; give the rules."""
    environment = {
        "PATH": os.environ["PATH"],
        "MODELS": str(COMPOSE),
        "RENDERED": str(folder),
        "PROMETHEUS": shutil.which("true") or "/bin/true",
        "WATERFALL_METRICS_PORT": "9100",
        **SHIPPED,
        **thresholds,
    }
    subprocess.run(["sh", str(START)], env=environment, check=True, capture_output=True)
    return folder / "alerts.yml"


def prometheus_of(values: dict[str, Any] | None = None) -> dict[str, str]:
    """Give the ConfigMap of Prometheus the chart renders with the values given."""
    (configuration,) = [
        item["data"]
        for item in yaml.safe_load_all(chart.render(values))
        if item and item["kind"] == "ConfigMap" and item["metadata"]["name"].endswith("-prometheus")
    ]
    return configuration


def by_chart(folder: Path, **thresholds: str) -> Path:
    """Write the rules the chart renders with the thresholds given; give their file."""
    given = {VALUES[name]: value for name, value in thresholds.items()}
    rules = folder / "chart" / "alerts.yml"
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_text(prometheus_of({"prometheus": {"thresholds": given}})["alerts.yml"])
    return rules


def promtool(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the promtool of the release of Prometheus the platform runs."""
    return subprocess.run(
        [str(kubetools.installed("promtool")), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def play(rules: Path, series: dict[str, str], expected: Expected) -> None:
    """Evaluate the rules on series, a sample a minute, and hold the alerts firing at each minute.

    A series is written as promtool reads it: ``1x3`` four samples of 1, ``0+60x2`` 0, 60 and 120,
    ``stale`` the end of a series whose target has gone.
    """
    test = {
        "rule_files": [str(rules)],
        "evaluation_interval": "1m",
        "tests": [
            {
                "interval": "1m",
                "input_series": [{"series": name, "values": v} for name, v in series.items()],
                "alert_rule_test": [
                    {
                        "eval_time": f"{minute}m",
                        "alertname": alert,
                        "exp_alerts": [{"exp_labels": labels} for labels in firing],
                    }
                    for minute, alert, firing in expected
                ],
            }
        ],
    }
    path = rules.parent / "test.yml"
    path.write_text(yaml.safe_dump(test), encoding="utf-8")
    done = promtool("test", "rules", str(path))
    assert done.returncode == 0, done.stdout + done.stderr


# --- The seven alerts, at the shipped thresholds -------------------------------------------------


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_stop_of_a_component_produces_an_alert_that_ends_when_it_answers_again(
    tmp_path: Path,
) -> None:
    # « L'arrêt d'un composant […] produi[t] […] une alerte » ; « Une alerte disparaît […] dès que
    # sa cause a cessé. » The API down at minute 4, back at 10; the worker gone for good; PostgreSQL
    # found down by both replicas of the API; Redis by one of them alone, which is no stop.
    play(
        by_compose(tmp_path),
        {
            'up{job="api",instance="a"}': "1x3 0x5 1x3",
            'up{job="worker",instance="a"}': "1x3 stale _x7",
            'waterfall_component_up{component="database",instance="a"}': "1x3 0x5 1x3",
            'waterfall_component_up{component="database",instance="b"}': "1x3 0x5 1x3",
            'waterfall_component_up{component="cache",instance="a"}': "1 0x11",
            'waterfall_component_up{component="cache",instance="b"}': "1x12",
        },
        [
            (3, "component_unavailable", []),
            # Down for a minute: one collection missed raises nothing.
            (4, "component_unavailable", []),
            (
                5,
                "component_unavailable",
                [
                    {"component": "api", **ALERT},
                    {"component": "worker", **ALERT},
                    {"component": "database", **ALERT},
                ],
            ),
            (10, "component_unavailable", [{"component": "worker", **ALERT}]),
        ],
    )


def outcome_played(tmp_path: Path, run: str, alert: str) -> None:
    """Play the latest outcome of a scheduled run, the others succeeding throughout.

    Failed, unread while PostgreSQL is down, failed again, then succeeded.
    """
    others = {"scheduled_backup", "scheduled_backup_copy", "identity_sync"} - {run}
    play(
        by_compose(tmp_path),
        {
            f'waterfall_last_run_success{{run="{run}",instance="a"}}': "1x1 0x1 stale _x5 0x1 1x3",
            f'waterfall_last_run_success{{run="{run}",instance="b"}}': "1x1 0x1 stale _x5 0x1 1x3",
            **{
                f'waterfall_last_run_success{{run="{other}",instance="a"}}': "1x12"
                for other in others
            },
        },
        [
            (1, alert, []),
            (2, alert, [ALERT]),
            # PostgreSQL down: no replica reads the outcome, and the alert stays.
            (6, alert, [ALERT]),
            (11, alert, [ALERT]),
            # The next run succeeded: the alert ends.
            (12, alert, []),
        ],
    )


@pytest.mark.requirement("WF-OBS-0030-A")
def test_a_scheduled_backup_that_failed_produces_an_alert_until_the_next_succeeds(
    tmp_path: Path,
) -> None:
    # « […] l'échec d'une sauvegarde planifiée […] produi[t] […] une alerte » ; it disappears as
    # soon as its cause has ceased: at the next backup that succeeds.
    outcome_played(tmp_path, "scheduled_backup", "scheduled_backup_failed")


@pytest.mark.story("US-2880")
def test_the_external_copy_of_a_scheduled_backup_that_failed_produces_an_alert(
    tmp_path: Path,
) -> None:
    # Proper to US-2880: the failure of the external copy of a scheduled backup produces an alert,
    # scheduled_backup_copy_failed, which ends at the next copy that succeeds.
    outcome_played(tmp_path, "scheduled_backup_copy", "scheduled_backup_copy_failed")


@pytest.mark.story("US-2880")
def test_a_reading_of_the_accounts_that_failed_produces_an_alert(tmp_path: Path) -> None:
    # Proper to US-2880: the failure of a reading of the accounts produces an alert,
    # identity_sync_failed, which ends at the next reading that succeeds.
    outcome_played(tmp_path, "identity_sync", "identity_sync_failed")


@pytest.mark.story("US-2940")
def test_a_restoration_abandoned_that_keeps_the_maintenance_produces_an_alert_until_lifted(
    tmp_path: Path,
) -> None:
    # Proper to US-2940 (#1016, decision of the author of 2026-11-22): a restoration given up once
    # its databases may have changed keeps the maintenance, and is seen: an alert, from the first
    # replica that reads it, which ends when the operator lifts the maintenance.
    play(
        by_compose(tmp_path),
        {
            'waterfall_restoration_abandoned{instance="a"}': "0x2 1x5 0x3",
            'waterfall_restoration_abandoned{instance="b"}': "0x3 1x4 0x3",
        },
        [
            (2, "restoration_abandoned", []),
            (3, "restoration_abandoned", [ALERT]),
            (8, "restoration_abandoned", [ALERT]),
            (9, "restoration_abandoned", []),
        ],
    )


@pytest.mark.requirement("WF-OBS-0030-A")
def test_a_failure_unread_for_over_an_hour_ends_its_alert_and_a_live_replica_that_succeeded_holds(
    tmp_path: Path,
) -> None:
    # The outcome last read holds for an hour while no replica reads it (PostgreSQL down), no more:
    # the alert ends then. And the highest outcome of the replicas holds: one that reads a success
    # is enough, whatever the other read.
    rules = by_compose(tmp_path)
    failed = 'waterfall_last_run_success{run="scheduled_backup",instance="a"}'
    other = 'waterfall_last_run_success{run="scheduled_backup",instance="b"}'
    play(
        rules,
        {failed: "0x1 stale _x80"},
        [
            (1, "scheduled_backup_failed", [ALERT]),
            # The last sample read is at 1: the window of an hour, (0, 60], holds it at 60, and
            # (1, 61] no more at 61: [59m] ends it at 60, [61m] and [62m] hold it at 61.
            (60, "scheduled_backup_failed", [ALERT]),
            (61, "scheduled_backup_failed", []),
            (62, "scheduled_backup_failed", []),
        ],
    )
    play(rules, {failed: "0x5", other: "1x5"}, [(3, "scheduled_backup_failed", [])])
    play(rules, {failed: "0x2 stale _x3", other: "1x5"}, [(4, "scheduled_backup_failed", [])])


def queue_played(rules: Path, threshold: int) -> None:
    """Play a task that waits past the threshold, then is taken; and one taken a minute before it.

    Each waits a minute more at each minute.
    """
    minutes = threshold // 60
    stalled = f"0+60x{minutes + 1} 0x3"
    taken = f"0+60x{minutes - 1} 0x5"
    for ages in (stalled, taken):
        play(
            rules,
            {
                'waterfall_oldest_queued_task_age_seconds{instance="a"}': ages,
                'waterfall_oldest_queued_task_age_seconds{instance="b"}': ages,
            },
            [
                (minutes - 1, "task_queue_stalled", []),
                # At the threshold, the task has not waited more than it.
                (minutes, "task_queue_stalled", []),
                (minutes + 1, "task_queue_stalled", [ALERT] if ages == stalled else []),
                (minutes + 2, "task_queue_stalled", []),
            ],
        )


@pytest.mark.requirement("WF-OBS-0030-A")
def test_a_task_queued_more_than_fifteen_minutes_produces_an_alert_and_one_taken_before_none(
    tmp_path: Path,
) -> None:
    # « Une tâche laissée en file plus de quinze minutes produit une alerte, et une tâche prise
    # avant n'en produit pas. »
    queue_played(by_compose(tmp_path), 900)


def storage_played(rules: Path, threshold: float) -> None:
    """Play the database used up to just below the threshold, at it, below, then above."""
    capacity = 1000
    below = round(threshold * capacity) - 1
    at = round(threshold * capacity)
    used = [below, at, below, min(at + 50, capacity)]
    play(
        rules,
        {
            'waterfall_storage_used_bytes{component="database",instance="a"}': " ".join(
                str(size) for size in used
            ),
            'waterfall_storage_available_bytes{component="database",instance="a"}': " ".join(
                str(capacity - size) for size in used
            ),
            'waterfall_storage_used_bytes{component="object_storage",instance="a"}': "500x4",
            'waterfall_storage_available_bytes{component="object_storage",instance="a"}': "500x4",
        },
        [
            (0, "storage_nearly_full", []),
            (1, "storage_nearly_full", [{"component": "database", "severity": "watch"}]),
            (2, "storage_nearly_full", []),
            (3, "storage_nearly_full", [{"component": "database", "severity": "watch"}]),
        ],
    )


@pytest.mark.requirement("WF-OBS-0030-A")
def test_a_storage_brought_to_85_percent_of_occupancy_produces_an_alert(tmp_path: Path) -> None:
    # « Un stockage porté à 85 % d'occupation produit une alerte. »
    storage_played(by_compose(tmp_path), 0.85)


# A hundred requests a minute to the API: 4 % in error for ten minutes, 6 % for ten, then none; the
# probes and the collections, which fail a thousandfold more, are no request of a user. The front
# stays at 1 %, its probes failing apart.
REQUESTS = {
    'waterfall_api_requests_total{operation="getProject",status="200"}': (
        "0+96x10 1054+94x9 2000+100x10"
    ),
    'waterfall_api_requests_total{operation="getProject",status="500"}': "0+4x10 46+6x9 100x10",
    'waterfall_api_requests_total{operation="getLiveness",status="200"}': "0+10000x30",
    'waterfall_api_requests_total{operation="getMetrics",status="200"}': "0+10000x30",
    'waterfall_front_requests_total{kind="page",status="200"}': "0+99x30",
    'waterfall_front_requests_total{kind="page",status="500"}': "0+1x30",
    'waterfall_front_requests_total{kind="probe",status="503"}': "0+1000x30",
}
API = {"component": "api", **ALERT}


@pytest.mark.requirement("WF-OBS-0030-A")
def test_an_error_rate_above_the_threshold_for_five_minutes_produces_an_alert(
    tmp_path: Path,
) -> None:
    # « Un taux d'erreur porté au-dessus du seuil pendant cinq minutes produit une alerte. » : 4 %,
    # under the 5 % shipped, none; 6 % over the five minutes, one, for the API alone; none once the
    # errors have stopped for five minutes.
    play(
        by_compose(tmp_path),
        REQUESTS,
        [
            (9, "error_rate_abnormal", []),
            (16, "error_rate_abnormal", [API]),
            (27, "error_rate_abnormal", []),
        ],
    )


@pytest.mark.requirement("WF-OBS-0030-A")
def test_an_error_rate_of_the_front_above_the_threshold_produces_an_alert_that_ends_with_it(
    tmp_path: Path,
) -> None:
    # The same rule for the front: 6 % of its pages in error over the five minutes, one alert, for
    # the front alone; none once the errors have stopped for five minutes. Its probes, failing
    # apart, are no request of a user.
    series = {
        'waterfall_front_requests_total{kind="page",status="200"}': "0+94x10 940+100x20",
        'waterfall_front_requests_total{kind="page",status="500"}': "0+6x10 60x20",
        'waterfall_front_requests_total{kind="probe",status="503"}': "0+1000x30",
    }
    play(
        by_compose(tmp_path),
        series,
        [
            (9, "error_rate_abnormal", [{"component": "front", **ALERT}]),
            (20, "error_rate_abnormal", []),
        ],
    )


# --- Each threshold changed, under both packagings ----------------------------------------------

PACKAGINGS = [pytest.param(by_compose, id="compose"), pytest.param(by_chart, id="chart")]


@pytest.mark.requirement("WF-OBS-0030-A")
@pytest.mark.parametrize("written", PACKAGINGS)
def test_each_threshold_changed_changes_the_value_at_which_its_alert_appears(
    tmp_path: Path, written: Any
) -> None:
    # « Chaque seuil modifié change la valeur à laquelle l'alerte apparaît. » : ten minutes instead
    # of fifteen, 90 % instead of 85 %, 3 % instead of 5 %, and ten minutes of window for five.
    queue_played(written(tmp_path / "queue", **{QUEUE: "600"}), 600)
    storage_played(written(tmp_path / "storage", **{STORAGE: "0.9"}), 0.9)
    rules = written(tmp_path / "errors", **{ERRORS: "0.03"})
    # 4 % is over 3 %.
    play(rules, REQUESTS, [(9, "error_rate_abnormal", [API])])
    # Over ten minutes instead of five, the minutes of 4 % weigh in: 4.6 %, under 5 %.
    wide = written(tmp_path / "window", **{WINDOW: "600"})
    play(wide, REQUESTS, [(13, "error_rate_abnormal", [])])
    play(by_compose(tmp_path / "shipped"), REQUESTS, [(13, "error_rate_abnormal", [API])])


@pytest.mark.requirement("WF-OBS-0030-A")
@pytest.mark.parametrize(
    "thresholds", [{}, {QUEUE: "600", STORAGE: "0.9", ERRORS: "0.03", WINDOW: "600"}]
)
def test_the_chart_writes_the_rules_the_compose_writes(
    tmp_path: Path, thresholds: dict[str, str]
) -> None:
    # One model, the same rules under both packagings, at the shipped thresholds as at others.
    compose = by_compose(tmp_path / "compose", **thresholds).read_text(encoding="utf-8")
    assert by_chart(tmp_path, **thresholds).read_text() == compose.rstrip("\n")
    assert "${" not in compose
