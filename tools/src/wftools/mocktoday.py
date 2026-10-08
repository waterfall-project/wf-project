# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The examples of the indicators of the witness today, engendered (EP-02/L24, #287).

The witness is read once — the offer and the reference at their marking, the current revision
today, the actual costs (``wftools.mockindicators``) — and each example is one of four kinds,
as the frame of #287 wants: a reading of the state of today (the indicators of the estimate, of
the remaining to commit and of the project, the evolution of the indices, the tracking of the
milestones, the curves, the workload); a reading of an earlier instant (the estimate the offer
kept at its marking, the indicators the reference kept, the rate update its creation proposed);
the sequel of a write made today (the remaining to commit after ``remaining_reestimated``); or a
counterfactual variant declared as such (``*_missing_rates``, ``cost_curve_amendment``). The
portfolio sums the indicators of the project in memory (``project_today``), never read back from
the file the same command writes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mocktext, mockwitness, mockwrites
from wftools.mockcurves import Era, cost_curve, earned_value_curves, workload
from wftools.mockindicators import (
    PROJECT,
    READ_ON,
    Cost,
    Point,
    Reading,
    actual_costs,
    estimate,
    index_history,
    milestone_tracking,
    missing_rates,
    offer,
    project_indicators,
    rate_update,
    reference,
    remaining_indicators,
    today,
)
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CORE,
    ELECTRICAL_ENGINEERING,
    LABOUR,
    OFFER_MARKED,
    ORDER_RECEIVED,
    PAYMENT_DELAY,
    RISKS_IDENTIFIED,
    STUDIES_LINE,
    STUDIES_STARTED,
    fixture,
    universe,
)

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

AMENDMENT_2 = Decimal("15000.00")
AMENDMENT_2_ON = date(2026, 3, 10)
"""The counterfactual amendment of ``cost_curve_amendment``: the rework of the detailed studies,
15,000 more on their line of subcontracting, as if contracted on 10 March 2026."""

WORKSHOP = universe(472)
"""The node of organisation the filtered workload retains: the cabling workshop, under the
electrical design office, which holds the cable fitter alone (``org_nodes``, ``resource_roles``)."""


@dataclass(frozen=True, slots=True)
class Witness:
    """The revisions of the witness read once, and its actual costs."""

    offer: Reading
    reference: Reading
    today: Reading
    costs: list[Cost]

    @property
    def eras(self) -> list[Era]:
        """Return the references in force: the offer from its designation, then the reference.

        The offer was designated reference at the order (WF-REV-0040); the amendment 1 produced
        the reference 101, which stepped the reference budget (WF-REV-0050).
        """
        return [Era(ORDER_RECEIVED.on, self.offer), Era(AMENDMENT_MERGED.on, self.reference)]

    def points(self) -> list[Point]:
        """Return the points of the evolution of the indices: each marking, then today."""
        names = {
            entry["revision_id"]: entry["version_name"] for entry in fixture("revisions")["items"]
        }
        return [
            Point(self.offer, self.offer, names[self.offer.revision]),
            Point(self.reference, self.reference, names[self.reference.revision]),
            Point(self.today, self.reference, None),
        ]


def witness() -> Witness:
    """Read the witness once."""
    return Witness(offer(), reference(), today(), actual_costs())


def project_today(read_once: Witness | None = None) -> JsonObject:
    """Return the indicators of the project today, as the portfolio sums them, in memory."""
    found = read_once or witness()
    return project_indicators(found.today, found.reference, found.costs)


def estimate_today(read_once: Witness | None = None) -> JsonObject:
    """Return the indicators of the estimate today, as the volume reads them, in memory.

    The previous marked revision of the current one is the reference itself.
    """
    found = read_once or witness()
    return estimate(found.today, against=found.reference, previous=found.reference)


def values() -> dict[str, JsonValue]:
    """Return the values of the examples of the indicators, by name."""
    found = witness()
    now, base, costs = found.today, found.reference, found.costs
    missing = frozenset({ELECTRICAL_ENGINEERING})
    reestimated = today(
        mockwrites.amended(
            CORE,
            line=mockwrites.on_line(LABOUR, hours=mockwrites.REESTIMATED_HOURS),
        )
    )
    amended = reference(
        mockwrites.amended(
            mockwitness.reference(),
            line=lambda line: (
                replace(line, unit=cast("Decimal", line.unit) + AMENDMENT_2)
                if line.number == STUDIES_LINE
                else line
            ),
        )
    )
    points = found.points()
    return {
        "estimate_indicators": estimate_today(found),
        "estimate_indicators_breakdown": estimate(found.offer),
        "estimate_indicators_missing_rates": estimate(
            now, against=base, previous=base, missing=missing
        ),
        "missing_rates": missing_rates(now, now.lines, missing),
        "rate_update": rate_update(),
        "remaining_indicators": remaining_indicators(now, base, base, costs),
        "remaining_indicators_over_budget": remaining_indicators(reestimated, base, base, costs),
        "project_indicators": project_today(found),
        "project_indicators_marked": project_indicators(base, base, costs),
        "index_history": index_history(points, costs),
        "milestone_tracking": milestone_tracking(points[:-1], points[-1]),
        "cost_curve": cost_curve(now, found.eras, costs),
        "cost_curve_payment_delays": cost_curve(now, found.eras, costs, delays=True),
        "cost_curve_amendment": cost_curve(now, [*found.eras, Era(AMENDMENT_2_ON, amended)], costs),
        "earned_value_curves": earned_value_curves(now, base, costs),
        "workload": workload(now, "current_remaining"),
        "workload_reference_budget": workload(base, "reference_budget"),
        "workload_marked_remaining": workload(base, "marked_remaining"),
        "workload_org_node": workload(now, "current_remaining", WORKSHOP),
    }


# --- What the summaries say ---------------------------------------------------------------------

_day = mocktext.day
_TODAY = _day(READ_ON)
_ZONES = {"nominal": "nominal", "watch": "vigilance", "alert": "alerte"}


def _obj(value: JsonValue) -> JsonObject:
    return cast("JsonObject", value)


def _get(found: dict[str, JsonValue], name: str) -> JsonObject:
    """Return the value of an example of the indicators that is an object."""
    return _obj(found[name])


def _objs(value: JsonValue) -> list[JsonObject]:
    return cast("list[JsonObject]", value)


def _money(value: JsonValue) -> str:
    """Write an amount the contract carries as French does."""
    return mocktext.amount(Decimal(cast("str", value)))


def _of(envelope: JsonValue) -> str:
    """Write an amount under its envelope as French does."""
    return _money(_obj(envelope)["value"])


def _on(value: JsonValue) -> str:
    """Write a day the contract carries as French does."""
    return _day(date.fromisoformat(cast("str", value)))


def _labels(parts: JsonValue, *, computed: bool) -> list[str]:
    """Return the labels of the parts of an estimate whose amount is computed, or is not."""
    return [
        cast("str", part.get("label", "l'ensemble hors sous-projet")).lower()
        for part in _objs(parts)
        if _obj(part["amount"])["is_computable"] is computed
    ]


def _series(curve: JsonObject, name: str) -> list[JsonObject]:
    """Return the points of a series of a curve."""
    return _objs(next(each for each in _objs(curve["series"]) if each["name"] == name)["points"])


def _estimate_summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    now, missing = (
        _get(found, "estimate_indicators"),
        _get(found, "estimate_indicators_missing_rates"),
    )
    offered = _get(found, "estimate_indicators_breakdown")
    [item] = _objs(now["by_order_item"])
    coverage = _obj(_get(found, "remaining_indicators")["coverage"])
    natures = ", ".join(
        f"{_of(part['amount'])} de {cast('str', part['label']).lower()}"
        for part in _objs(now["by_cost_type"])
    )
    touched = [
        *_labels(missing["by_cost_type"], computed=False),
        *_labels(missing["by_subproject"], computed=False),
        *_labels(missing["by_order_item"], computed=False),
    ]
    untouched = [
        *_labels(missing["by_cost_type"], computed=True),
        *_labels(missing["by_subproject"], computed=True),
    ]
    variant = (
        "si l'ingénierie électrique, la catégorie de ses lignes de câblage, n'avait pas de taux "
        "horaire pour 2026, l'année de référence de sa révision"
    )
    rates = ", ".join(
        f"{cast('str', rate['label']).lower()} de {_money(rate['previous_amount'])} à "
        f"{_money(rate['proposed_amount'])}"
        for rate in _objs(_get(found, "rate_update")["categories"])
    )
    return {
        "estimate_indicators": (
            f"Les indicateurs du devis de la révision courante au {_TODAY} : {_of(now['total'])} "
            f"au total, dont {natures} — la provision du risque encore identifié —, ventilés par "
            f"nature, par sous-projet et par le poste « {item['label']} » du lotissement, que "
            f"porte le lot « Poste de commande », {_of(item['amount'])}. L'écart avec la "
            f"référence, {_of(now['delta_to_reference'])}, est aussi celui avec la révision "
            f"marquée précédente, la référence elle-même : les "
            f"{_money(coverage['remaining_provisions'])} de provision et les "
            f"{_money(coverage['occurred_cost'])} des lignes fusionnées par la survenance, face "
            f"aux {_money(coverage['reserve'])} de provisions qu'elle portait (WF-DEV-0060, "
            f"WF-RIS-0050)."
        ),
        "estimate_indicators_breakdown": (
            f"Les indicateurs du devis de l'offre v1.0, tels que son marquage du "
            f"{_day(OFFER_MARKED.on)} les a calculés et conservés, pendant le chiffrage "
            f"(WF-DAT-0040) : {_of(offered['total'])} au total, "
            f"aux taux de 2025, sans provision — aucun risque n'était identifié —, par nature en "
            f"montant et en part du total, dont la somme vaut cent pour cent ; tout dans "
            f"l'ensemble hors sous-projet, aucun n'étant encore déclaré (WF-PRJ-0050) ; le poste "
            f"du lotissement que "
            f"porte le lot « Poste de commande ». Ni révision de référence ni révision marquée "
            f"avant elle : aucun écart (WF-DEV-0060)."
        ),
        "estimate_indicators_missing_rates": (
            f"Le devis de la révision courante au {_TODAY} {variant} : le total, les écarts et ce "
            f"que touchent ses lignes — {', '.join(touched)} — ne se calculent pas, et nomment la "
            f"catégorie et l'année qui manquent ; {', '.join(untouched)} se calculent, mais leur "
            f"part du total non ; le calcul est refusé plutôt que fait avec un taux à zéro "
            f"(WF-DEV-0010, WF-DEV-0060)."
        ),
        "missing_rates": (
            f"Les taux horaires qui manqueraient au devis de la révision courante au {_TODAY} "
            f"{variant} : le calcul est refusé tant qu'elle n'en a pas (WF-DEV-0010)."
        ),
        "rate_update": (
            f"La mise à jour des taux présentée à la création de la révision 101, le "
            f"{_day(RISKS_IDENTIFIED.on)} — sa première saisie, l'identification des risques —, "
            f"dont l'année de référence est 2026 quand celle de l'offre copiée était 2025 : "
            f"catégorie par catégorie, chaque catégorie de main-d'œuvre de l'offre à son taux de "
            f"2026 de la grille des taux, celui de 2025 en regard — {rates} —, que l'utilisateur "
            f"accepte ou refuse une à une (WF-REV-0060). La révision courante, ouverte la même "
            f"année que la référence qu'elle copie, n'en a aucune."
        ),
    }


def _scopes_said(answer: JsonObject) -> str:
    """Say the zone of each subproject from ``by_subproject``: those in alert by their overrun.

    A scope in alert is named with what it overruns its budget by; only the others are said
    nominal (WF-RAE-0020, WF-IHM-0070).
    """

    def name(entry: JsonObject) -> str:
        label = entry.get("label")
        return "l'ensemble hors sous-projet" if label is None else f"« {label} »"

    entries = _objs(answer["by_subproject"])
    alerts = [entry for entry in entries if entry["zone"] == "alert"]
    others = [entry for entry in entries if entry["zone"] != "alert"]
    said = [
        f"{name(entry)}, en alerte, dépasse son budget de {_money(entry['variance']).lstrip('-')}"
        for entry in alerts
    ]
    text = " ; ".join(said)
    if others:
        nominal = ", ".join(
            f"{name(entry)} {_ZONES[cast('str', entry['zone'])]}" for entry in others
        )
        text = f"{text} ; {nominal}" if alerts else nominal
    return text


def _margins(answer: JsonObject) -> str:
    """Say the margin on the reference budget and the deviation from the previous review.

    The margin is the budget less what is foreseen, the actual cost and the remaining to commit,
    as ``delta_to_reference`` carries it, in the sense of each subproject (#466); the deviation,
    the remaining to commit less that of the previous review.
    """
    return (
        f"la marge sur le budget de référence, {_money(answer['delta_to_reference'])} — le budget "
        f"moins le coût réel et le reste à engager, dans le sens des sous-projets — ; l'écart à "
        f"la revue précédente, {_money(answer['delta_to_previous_revision'])} — le reste à "
        f"engager courant moins celui de la référence à son marquage"
    )


def _remaining_summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    left, over = (
        _get(found, "remaining_indicators"),
        _get(found, "remaining_indicators_over_budget"),
    )
    return {
        "remaining_indicators": (
            f"Le reste à engager de la révision courante au {_TODAY} : {_money(left['total'])} — "
            f"les tâches non démarrées à leur montant budgété, le câblage des armoires démarré à "
            f"son montant réestimé, les études terminées pour rien, les lignes fusionnées par la "
            f"survenance, budgétées à zéro, à leur montant réestimé et la provision du risque "
            f"identifié (WF-RAE-0010). Par sous-projet, le coût réel et le reste à engager face "
            f"au budget : {_scopes_said(left)} ; {_margins(left)} ; la couverture des risques "
            f"(WF-RAE-0020, WF-RIS-0050)."
        ),
        "remaining_indicators_over_budget": (
            f"Le reste à engager juste après la réestimation du raccordement des borniers à "
            f"{mockwrites.REESTIMATED_HOURS} h, faite aujourd'hui (remaining_reestimated) : "
            f"{_money(over['total'])} ; {_scopes_said(over)} ; {_margins(over)} (WF-RAE-0020, "
            f"WF-IHM-0070)."
        ),
    }


def _indices(scope: JsonObject) -> str:
    """Say the indices of a scope today, and their zones."""
    point = _objs(scope["points"])[-1]
    cost, schedule = _obj(point["cost_index"]), _obj(point["schedule_index"])
    name = scope["label"] or ("le projet" if scope["scope"] == PROJECT else "hors sous-projet")
    if not _obj(cost["value"])["is_computable"]:
        return f"{name}, sans coût réel ni valeur planifiée, non calculables"
    return (
        f"{name}, indice de coût {cast('str', _obj(cost['value'])['value']).replace('.', ',')} "
        f"({_ZONES[cast('str', cost['zone'])]}), indice de délai "
        f"{cast('str', _obj(schedule['value'])['value']).replace('.', ',')} "
        f"({_ZONES[cast('str', schedule['zone'])]})"
    )


def _project_summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    project, marked = _get(found, "project_indicators"), _get(found, "project_indicators_marked")
    studies, acceptance = _objs(_get(found, "milestone_tracking")["milestones"])
    history = _get(found, "index_history")
    indices = " ; ".join(_indices(scope) for scope in _objs(history["scopes"]))
    thresholds = _obj(history["thresholds"])
    marked_names = ", ".join(
        f"« {point['version_name']} »"
        for point in _objs(_objs(history["scopes"])[0]["points"])
        if point["version_name"] is not None
    )
    return {
        "project_indicators": (
            f"Les indicateurs du projet en cours au {_TODAY}, sur sa révision courante : le "
            f"budget de référence de {_money(project['reference_budget'])}, hors provisions ; la "
            f"valeur planifiée de {_money(project['planned_value'])} sur les dates de la "
            f"référence ; la valeur acquise de {_money(project['earned_value'])}, celle des "
            f"études de détail terminées, les tâches de la survenance n'en acquérant pas ; le "
            f"coût réel de {_money(project['actual_cost'])}, les pièces du périmètre suivi ; le "
            f"reste à engager de {_money(project['remaining'])}, provisions comprises ; d'où les "
            f"avancements, les deux indices et leur zone, leurs écarts et les trois projections "
            f"à terminaison (WF-IND-0010 à WF-IND-0080)."
        ),
        "project_indicators_marked": (
            f"Les indicateurs du projet sur sa révision « Référence », tels que son marquage du "
            f"{_day(AMENDMENT_MERGED.on)} les a calculés et conservés : rien n'était encore "
            f"planifié ni dépensé — les études de détail commencent le "
            f"{_day(STUDIES_STARTED.on)} —, donc ni indice de coût ni indice de délai, faute de "
            f"coût réel et de valeur planifiée ; le budget de référence de "
            f"{_money(marked['reference_budget'])} et le reste à engager de "
            f"{_money(marked['remaining'])}, qui compte les provisions des risques identifiés "
            f"(WF-IND-0010, WF-DAT-0040, WF-RAE-0010)."
        ),
        "index_history": (
            f"L'évolution des indices du projet et de ses mailles : un point par révision "
            f"marquée à partir de l'état En cours — {marked_names}, sans indice calculable, rien "
            f"n'étant dépensé ni planifié à son marquage ; l'offre, marquée pendant le chiffrage, "
            f"n'a conservé que son devis (WF-DAT-0040, #468) — et le dernier au {_TODAY} pour la "
            f"révision en cours : {indices} ; les seuils du référentiel, "
            f"{_value(thresholds['cost_watch'])} et {_value(thresholds['cost_alert'])} "
            f"(WF-IND-0130, WF-REF-0170)."
        ),
        "milestone_tracking": (
            f"Le diagramme temps/temps du projet au {_TODAY} : la réception des études, prévue au "
            f"{_on(studies['completed_on'])} par l'offre et par la référence, terminée ce jour-là, "
            f"son dernier point sur la diagonale et aucun après ; la réception usine, ajoutée par "
            f"l'avenant 1 — l'offre ne la porte pas —, prévue au "
            f"{_on(_objs(acceptance['points'])[0]['forecast_date'])} par la référence et toujours "
            f"par la révision en cours : une horizontale. Aucune révision ne déplace un jalon "
            f"(WF-IND-0090)."
        ),
    }


def _curve_summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    curve, amended = _get(found, "cost_curve"), _get(found, "cost_curve_amendment")
    project = _get(found, "project_indicators")
    budget = _series(curve, "reference_budget")
    projection = _series(curve, "project_manager_projection")
    [step] = _objs(curve["steps"])
    second = _objs(amended["steps"])[1]
    before, after = (
        point["amount"]
        for point in _series(amended, "reference_budget")
        if point["date"] == second["date"]
    )
    cash = _objs(_get(found, "cost_curve_payment_delays")["cash_out_by_month"])
    to_come = sum((Decimal(cast("str", month["forecast"])) for month in cash), Decimal(0))
    planned_end = _series(_get(found, "earned_value_curves"), "planned_value")[-1]
    return {
        "cost_curve": (
            f"La courbe de coûts cumulés du projet au {_TODAY} : le budget de référence cumulé sur "
            f"les dates de la référence, {_money(project['planned_value'])} à la date de calcul, "
            f"qui atteint ses {_money(budget[-1]['amount'])} à sa fin, le "
            f"{_on(budget[-1]['date'])} ; la marche de l'avenant 1, {_money(step['amount'])}, le "
            f"{_on(step['date'])}, où le budget de l'offre désignée référence devient celui de la "
            f"révision « Référence », deux points à cette date, avant et après, nuls tous deux — "
            f"rien n'était encore prévu de dépenser — ; le coût réel par date de pièce jusqu'à la "
            f"date de calcul, {_money(project['actual_cost'])} ; la projection du chef de projet, "
            f"qui en part et étale le reste à engager sur les dates de la révision courante "
            f"jusqu'au {_on(projection[-1]['date'])}, {_money(projection[-1]['amount'])} "
            f"(WF-IND-0100)."
        ),
        "cost_curve_payment_delays": (
            f"La même courbe décalée des délais de paiement — {PAYMENT_DELAY} jours sur "
            f"l'ingénierie de détail et sur les borniers, aucun sur la main-d'œuvre — : ce sont "
            f"les décaissements. Le budget de référence et la projection sont décalés ligne par "
            f"ligne, la provision du risque identifié ajoutée à la fin de la tâche qui la porte ; "
            f"le coût réel ne l'est pas. Les décaissements passés, par mois de date de pièce, et "
            f"ceux à venir, dont la somme, {mocktext.amount(to_come)}, égale le reste à engager "
            f"(WF-IND-0100)."
        ),
        "cost_curve_amendment": (
            f"La même courbe si un avenant 2 — reprise des études de détail, "
            f"{_money(second['amount'])} de plus sur leur ligne de sous-traitance — avait été "
            f"contractualisé le {_day(AMENDMENT_2_ON)} : une seconde marche, le budget de "
            f"référence portant deux points à cette date, avant et après — {_money(before)} puis "
            f"{_money(after)} —, puis cumulé sur la nouvelle référence, jusqu'à "
            f"{_money(_series(amended, 'reference_budget')[-1]['amount'])} ; les études étant "
            f"terminées, le reste à engager et la projection ne changent pas (WF-IND-0100)."
        ),
        "earned_value_curves": (
            f"Les courbes de valeur acquise du projet au {_TODAY} : la valeur planifiée, "
            f"{_money(project['planned_value'])} à la date de calcul, sur les dates de la "
            f"référence, qui atteint le budget de référence à sa fin, le "
            f"{_on(planned_end['date'])} ; la valeur acquise, une marche de "
            f"{_money(project['earned_value'])} à la terminaison des études de détail ; le coût "
            f"réel par date de pièce, {_money(project['actual_cost'])}, jusqu'à la date de calcul "
            f"(WF-IND-0110)."
        ),
    }


def _month(value: JsonValue) -> str:
    """Write a month of the contract as French does: juin 2026."""
    year, month = cast("str", value).split("-")
    return _day(date(int(year), int(month), 1)).removeprefix("1er ")


def _value(value: JsonValue) -> str:
    """Write a decimal of the contract as French does: 0,9."""
    return cast("str", value).replace(".", ",")


def _the(label: JsonValue) -> str:
    """Name a role with its article, elided before a vowel: l'ingénieur, le technicien."""
    named = cast("str", label).lower()
    return f"l'{named}" if named[0] in "aeéèiouh" else f"le {named}"


def _loads(plan: JsonObject) -> str:
    """Say the load of each role of a workload: its hours, its months, or its capacity alone."""
    said: list[str] = []
    for role in _objs(plan["roles"]):
        months = _objs(role["months"])
        label = _the(role["label"])
        if not months:
            said.append(f"{label}, sans charge, avec sa capacité seule")
            continue
        hours = sum((Decimal(cast("str", month["hours"])) for month in months), Decimal(0))
        said.append(
            f"{label}, {mocktext.amount(hours)} h de {_month(months[0]['month'])} à "
            f"{_month(months[-1]['month'])}, en regard de sa capacité de "
            f"{mocktext.amount(Decimal(cast('str', role['capacity_monthly_hours'])))} h par mois"
        )
    return " ; ".join(said)


def _workload_summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    now, filtered = _get(found, "workload"), _get(found, "workload_org_node")
    kept = {cast("str", role["resource_role_id"]) for role in _objs(filtered["roles"])}
    others = [
        _the(role["label"]) for role in _objs(now["roles"]) if role["resource_role_id"] not in kept
    ]
    left_out = " et ".join(others) + (
        ", d'un autre nœud, n'y figure pas"
        if len(others) == 1
        else ", d'autres nœuds, n'y figurent pas"
    )
    reference = _loads(_get(found, "workload_reference_budget"))
    return {
        "workload": (
            f"Le plan de charge du projet sur le reste à engager de la révision en cours, au "
            f"{_TODAY} : par rôle et par mois, les heures des lignes de main-d'œuvre des tâches "
            f"non terminées, chacune étalée sur les heures ouvrées de sa tâche après la date de "
            f"calcul — aucun mois passé — : {_loads(now)} (WF-DEV-0070)."
        ),
        "workload_reference_budget": (
            f"Le même plan de charge sur les montants budgétés de la révision de référence, chaque "
            f"ligne étalée sur toute la durée de sa tâche : {reference} (WF-DEV-0070)."
        ),
        "workload_marked_remaining": (
            f"Le même plan de charge sur les montants réestimés de la révision marquée "
            f"« Référence », nommée par revision_id, à son marquage, aucune tâche n'étant "
            f"terminée : {_loads(_get(found, 'workload_marked_remaining'))} (WF-DEV-0070)."
        ),
        "workload_org_node": (
            f"Le même plan de charge sur le reste à engager de la révision en cours, restreint au "
            f"nœud « {filtered['org_node_label']} » (`org_node_id`) et à ses descendants : "
            f"{_loads(filtered)} ; {left_out} ; le plan nomme le "
            f"nœud retenu, que l'en-tête affiche sans lire l'arbre d'organisation (WF-DEV-0070, "
            f"WF-REF-0070, WF-ARC-0020)."
        ),
    }


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the indicators of the witness, by file name."""
    found = values()
    summaries = {
        **_estimate_summaries(found),
        **_remaining_summaries(found),
        **_project_summaries(found),
        **_curve_summaries(found),
        **_workload_summaries(found),
    }
    return {
        f"{name}.json": mocktext.example(summaries[name], value) for name, value in found.items()
    }
