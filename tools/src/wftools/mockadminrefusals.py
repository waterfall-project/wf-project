# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of the administration and of the platform the contract described without an example.

Each is a refusal an operation already says, with its code and its field, that no example gave:
a weekday given to a daily read of the accounts, a time of the backups that is not one, an origin
the accounts do not have, a date of the tasks that is not one, a preference beyond its bound, an
avatar that is no image (`putMyAvatar`); and the platform waiting on a component — the identity
provider for an invitation or an anonymisation, the database before the bootstrap of the
installation (WF-EXP-0020, WF-EXP-0040).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from typing import TYPE_CHECKING

from wftools import mocktext
from wftools.mockids import universe
from wftools.mockrefusals import field_refused

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

(
    WEEKDAY_CORRELATION,
    TIME_CORRELATION,
    ORIGINS_CORRELATION,
    FINISHED_CORRELATION,
    GRIDS_CORRELATION,
    IMAGE_CORRELATION,
    PROVIDER_CORRELATION,
    DATABASE_CORRELATION,
) = (universe(number) for number in range(1900, 1908))
"""The correlations of these refusals, each its own."""

GRIDS_BOUND = 100
"""The number of grids the preferences keep at most (`DisplayPreferences`, #874, #1235)."""


def unavailable(component: str, correlation: str) -> JsonObject:
    """Return the refusal of an operation a component it waits on prevents (WF-EXP-0040)."""
    return {
        "code": "COMPONENT_UNAVAILABLE",
        "status": 503,
        "params": {"component": component},
        "correlation_id": correlation,
    }


def examples() -> dict[str, JsonObject]:
    """Return these refusals, by file name."""
    too_many: JsonObject = {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {"pointer": "/grids", "code": "VALUE_TOO_LONG", "params": {"max_length": GRIDS_BOUND}}
        ],
        "correlation_id": GRIDS_CORRELATION,
    }
    return {
        "identity_sync_schedule_weekday_daily.json": mocktext.example(
            "La lecture des comptes passée aujourd'hui à une périodicité quotidienne avec un jour, "
            "le 1, le lundi : refusée, une quotidienne n'en ayant pas, le champ désigné ; rien "
            "n'est écrit (WF-ADM-0070).",
            field_refused("/weekday", "VALIDATION_FAILED", WEEKDAY_CORRELATION),
        ),
        "backup_schedule_time_invalid.json": mocktext.example(
            "La planification des sauvegardes réglée aujourd'hui à « 25:00 », qui n'est pas une "
            "heure HH:MM : refusée, le champ désigné ; rien n'est écrit, la planification reste "
            "celle que getBackupSchedule lit (WF-ADM-0170).",
            field_refused("/at_time", "VALIDATION_FAILED", TIME_CORRELATION),
        ),
        "users_origins_invalid.json": mocktext.example(
            "Les comptes demandés avec origins=ldap, une origine que les comptes n'ont pas : "
            "refusé, le paramètre désigné ; rien n'est lu (WF-IHM-0130).",
            field_refused("/query/origins", "VALIDATION_FAILED", ORIGINS_CORRELATION),
        ),
        "tasks_finished_since_invalid.json": mocktext.example(
            "Les tâches de l'appelant demandées avec finished_since=hier, qui n'est pas une "
            "date : refusé, le paramètre désigné ; rien n'est lu (WF-ARC-0090).",
            field_refused("/query/finished_since", "DATE_INVALID", FINISHED_CORRELATION),
        ),
        "preferences_too_many_grids.json": mocktext.example(
            f"Les préférences d'affichage modifiées par une grille nouvelle, alors qu'elles en "
            f"gardent déjà {GRIDS_BOUND} : refusé sur les grilles, la borne nommée ; rien n'est "
            f"enregistré (WF-ADM-0040, WF-IHM-0060).",
            too_many,
        ),
        "avatar_not_image.json": mocktext.example(
            "Un avatar déposé comme image/png dont le contenu n'est ni un PNG ni un JPEG : refusé "
            "sur le corps entier, l'avatar du compte reste celui qu'il était (WF-ADM-0080).",
            field_refused("", "VALIDATION_FAILED", IMAGE_CORRELATION),
        ),
        "invitation_provider_unavailable.json": mocktext.example(
            "L'invitation d'un compte local renvoyée pendant que le fournisseur d'identité ne "
            "l'envoie pas — installation sans messagerie, serveur de courriel défaillant, "
            "fournisseur injoignable — : refusé, le composant nommé ; l'invitation n'est jamais "
            "présentée comme partie, et l'écran offre le lien à remettre par un autre canal. La "
            "même réponse refuse l'anonymisation d'un compte local que le fournisseur ne retire "
            "pas, rien n'étant écrit (WF-EXP-0040, WF-ADM-0140, WF-ADM-0060).",
            unavailable("identity_provider", PROVIDER_CORRELATION),
        ),
        "installation_not_bootstrapped.json": mocktext.example(
            "Les réglages de l'installation lus, ou un avatar déposé, avant l'amorçage de "
            "l'installation, qui crée la ligne de ses réglages : refusé, la base de données "
            "nommée (WF-EXP-0020, WF-EXP-0040).",
            unavailable("database", DATABASE_CORRELATION),
        ),
    }
