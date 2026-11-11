# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reader and the writer of MS Project, their round trip and the schema.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file; US-1430/L1
writes its tests here ("Les tests du back"). Without MS Project, a database or a browser: bytes in,
a model out, and back. The schema of Microsoft is not in the repository: the variable
``WATERFALL_MSPDI_SCHEMA_PATH`` names it, and the tests that validate against it are skipped
without it (WF-QUA-0080). The order of the schema is held without it too, by the exact file the
writer writes for a small planning.
"""

import os
from datetime import datetime, time, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from lxml import etree

from waterfall.core.exchanges.interface import hardened_parser
from waterfall.core.planning.msproject import (
    Ignored,
    MsCalendar,
    MsProject,
    MsTask,
    PredecessorLink,
    ReadProject,
    UnreadableProjectError,
    WorkingDay,
    read_project,
    write_project,
)
from waterfall.core.planning.msproject.model import CONSTRAINT_TYPES, DATE_CONSTRAINTS

DESIGN = UUID("01960000-0000-7000-8000-000000000001")
BUILD = UUID("01960000-0000-7000-8000-000000000002")


def at(text: str) -> datetime:
    """Give an instant of the wall clock of a project, as MSPDI writes it."""
    return datetime.fromisoformat(text)


# A file as MS Project 2013 saves it: its namespace without a year, the summary of the project
# (UID 0), a blank row, an "unassigned" resource, estimated formats, a lineage in the custom field
# of the export, another in a ``GUID``, and what no import reads.
SAVED = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <SaveVersion>14</SaveVersion>
  <Name>Corpus.xml</Name>
  <StartDate>2026-03-02T08:00:00</StartDate>
  <CurrencyCode>EUR</CurrencyCode>
  <CalendarUID>1</CalendarUID>
  <MinutesPerDay>480</MinutesPerDay>
  <MinutesPerWeek>2400</MinutesPerWeek>
  <DaysPerMonth>20</DaysPerMonth>
  <ExtendedAttributes>
    <ExtendedAttribute>
      <FieldID>188743731</FieldID><FieldName>Text1</FieldName><Alias>Waterfall.lineage</Alias>
    </ExtendedAttribute>
    <ExtendedAttribute>
      <FieldID>188743734</FieldID><FieldName>Text2</FieldName><Alias>Supplier</Alias>
    </ExtendedAttribute>
  </ExtendedAttributes>
  <Calendars>
    <Calendar>
      <UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>
      <BaseCalendarUID>-1</BaseCalendarUID>
      <WeekDays>
        <WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>
        <WeekDay>
          <DayType>2</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
            <WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <WeekDay><DayType>0</DayType><DayWorking>0</DayWorking></WeekDay>
      </WeekDays>
    </Calendar>
    <Calendar>
      <UID>2</UID><Name>Four hours</Name><IsBaseCalendar>0</IsBaseCalendar>
      <BaseCalendarUID>1</BaseCalendarUID>
      <WeekDays>
        <WeekDay>
          <DayType>6</DayType><DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>
          </WorkingTimes>
        </WeekDay>
      </WeekDays>
    </Calendar>
  </Calendars>
  <Tasks>
    <Task><UID>0</UID><ID>0</ID><Name>Corpus</Name><OutlineLevel>0</OutlineLevel></Task>
    <Task>
      <UID>1</UID><ID>1</ID><Name>Lot 1</Name><OutlineLevel>1</OutlineLevel>
      <Start>2026-03-02T08:00:00</Start><Finish>2026-03-06T17:00:00</Finish>
      <Duration>PT40H0M0S</Duration><DurationFormat>53</DurationFormat><Summary>1</Summary>
      <Manual>0</Manual>
    </Task>
    <Task>
      <UID>2</UID><ID>2</ID><Name>Design</Name><OutlineLevel>2</OutlineLevel>
      <Start>2026-03-02T08:00:00</Start><Finish>2026-03-03T17:00:00</Finish>
      <Duration>PT16H0M0S</Duration><DurationFormat>7</DurationFormat><Milestone>0</Milestone>
      <PercentComplete>50</PercentComplete><ConstraintType>0</ConstraintType>
      <CalendarUID>-1</CalendarUID><Notes>The design,
in two days.</Notes>
      <ExtendedAttribute><FieldID>188743731</FieldID><Value>{DESIGN}</Value></ExtendedAttribute>
      <ExtendedAttribute><FieldID>188743734</FieldID><Value>ACME</Value></ExtendedAttribute>
      <Manual>0</Manual>
    </Task>
    <Task>
      <UID>3</UID><ID>3</ID><Name>Build</Name><OutlineLevel>2</OutlineLevel>
      <Start>2026-03-04T08:00:00</Start><Finish>2026-03-06T17:00:00</Finish>
      <Duration>PT72H0M0S</Duration><DurationFormat>40</DurationFormat>
      <FixedCost>1000</FixedCost><ConstraintType>4</ConstraintType><CalendarUID>2</CalendarUID>
      <ConstraintDate>2026-03-04T08:00:00</ConstraintDate>
      <PredecessorLink>
        <PredecessorUID>2</PredecessorUID><Type>1</Type><LinkLag>4800</LinkLag>
        <LagFormat>39</LagFormat>
      </PredecessorLink>
      <GUID>{{{BUILD}}}</GUID>
    </Task>
    <Task><UID>4</UID><ID>4</ID><IsNull>1</IsNull></Task>
    <Task>
      <UID>5</UID><ID>5</ID><Name>Delivered</Name><OutlineLevel>1</OutlineLevel>
      <Start>2026-03-06T17:00:00</Start><Finish>2026-03-06T17:00:00</Finish>
      <Duration>PT0H0M0S</Duration><DurationFormat>7</DurationFormat><Milestone>1</Milestone>
      <PredecessorLink><PredecessorUID>3</PredecessorUID><Type>0</Type>
        <LinkLag>-4800</LinkLag><LagFormat>7</LagFormat></PredecessorLink>
      <PredecessorLink><PredecessorUID>2</PredecessorUID><Type>3</Type>
        <LinkLag>50</LinkLag><LagFormat>19</LagFormat></PredecessorLink>
      <ExtendedAttribute><FieldID>188743731</FieldID><Value>by hand</Value></ExtendedAttribute>
      <Manual>1</Manual>
    </Task>
  </Tasks>
  <Resources>
    <Resource><UID>0</UID><ID>0</ID><IsNull>0</IsNull></Resource>
    <Resource><UID>1</UID><ID>1</ID><Name>Alice</Name></Resource>
    <Resource><UID>2</UID><ID>2</ID><Name>Bob</Name></Resource>
  </Resources>
  <Assignments>
    <Assignment><UID>1</UID><TaskUID>2</TaskUID><ResourceUID>1</ResourceUID></Assignment>
  </Assignments>
</Project>
""".encode()

STANDARD = MsCalendar(
    uid=1,
    name="Standard",
    is_base=True,
    base_uid=None,
    days=(
        WorkingDay(day_type=1, working=False),
        WorkingDay(
            day_type=2,
            working=True,
            times=((time(8), time(12)), (time(13), time(17))),
        ),
    ),
)

# The planning of the file, as the reader gives it.
PLANNING = MsProject(
    start=at("2026-03-02T08:00:00"),
    name="Corpus.xml",
    currency_code="EUR",
    calendar_uid=1,
    minutes_per_day=480,
    minutes_per_week=2400,
    days_per_month=20,
    calendars=(
        STANDARD,
        MsCalendar(
            uid=2,
            name="Four hours",
            is_base=False,
            base_uid=1,
            days=(WorkingDay(day_type=6, working=True, times=((time(8), time(12)),)),),
        ),
    ),
    tasks=(
        MsTask(
            uid=1,
            name="Lot 1",
            outline_level=1,
            duration=timedelta(hours=40),
            start=at("2026-03-02T08:00:00"),
            finish=at("2026-03-06T17:00:00"),
        ),
        MsTask(
            uid=2,
            name="Design",
            outline_level=2,
            duration=timedelta(hours=16),
            duration_unit="d",
            start=at("2026-03-02T08:00:00"),
            finish=at("2026-03-03T17:00:00"),
            notes="The design,\nin two days.",
            lineage=DESIGN,
        ),
        MsTask(
            uid=3,
            name="Build",
            outline_level=2,
            duration=timedelta(hours=72),
            duration_unit="ed",
            start=at("2026-03-04T08:00:00"),
            finish=at("2026-03-06T17:00:00"),
            constraint="start_no_earlier_than",
            calendar_uid=2,
            constraint_date=at("2026-03-04T08:00:00"),
            lineage=BUILD,
            predecessors=(PredecessorLink(2, "finish_to_start", 4800, "d"),),
        ),
        MsTask(
            uid=5,
            name="Delivered",
            outline_level=1,
            manual=True,
            duration=timedelta(0),
            duration_unit="d",
            start=at("2026-03-06T17:00:00"),
            finish=at("2026-03-06T17:00:00"),
            milestone=True,
            predecessors=(
                PredecessorLink(3, "finish_to_finish", -4800, "d"),
                PredecessorLink(2, "start_to_start", 50, "percent"),
            ),
        ),
    ),
)


@pytest.fixture
def schema() -> etree.XMLSchema:
    """Give the schema of MSPDI the variable names, the test skipped without it (WF-QUA-0080)."""
    path = os.environ.get("WATERFALL_MSPDI_SCHEMA_PATH")
    if not path:
        pytest.skip("WATERFALL_MSPDI_SCHEMA_PATH names no schema of MSPDI")
    return etree.XMLSchema(etree.parse(Path(path)))


def test_reading_a_file_saved_by_ms_project_gives_its_planning() -> None:
    assert read_project(SAVED).project == PLANNING


def test_the_reader_counts_by_kind_what_no_import_reads() -> None:
    assert read_project(SAVED).ignored == (
        Ignored("resources", 2, ("Alice", "Bob")),
        Ignored("calendars", 2, ("Standard", "Four hours")),
        Ignored("progress", 1),
        Ignored("costs", 1),
        Ignored("custom_fields", 1, ("Supplier",)),
        Ignored("date_constraints", 1, ("Build",)),
    )


def test_the_parent_of_a_task_is_the_nearest_one_before_it_of_a_lower_level() -> None:
    assert PLANNING.parents() == {1: None, 2: 1, 3: 1, 5: None}


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_planning_read_then_written_is_read_back_the_same() -> None:
    written = write_project(read_project(SAVED).project)

    again = read_project(written)

    assert again.project == PLANNING
    assert again.ignored == (
        Ignored("calendars", 2, ("Standard", "Four hours")),
        Ignored("date_constraints", 1, ("Build",)),
    )


@pytest.mark.requirement("WF-QUA-0080-A")
def test_the_writer_writes_the_elements_in_the_order_of_the_schema() -> None:
    planning = MsProject(
        start=at("2026-03-02T08:00:00"),
        name="Order",
        calendar_uid=1,
        minutes_per_day=480,
        minutes_per_week=2400,
        days_per_month=20,
        calendars=(STANDARD,),
        tasks=(
            MsTask(uid=1, name="A", outline_level=1),
            MsTask(
                uid=2,
                name="B",
                outline_level=1,
                manual=True,
                duration=timedelta(minutes=90, seconds=30),
                duration_unit="min",
                start=at("2026-03-02T08:00:00"),
                finish=at("2026-03-02T09:30:30"),
                calendar_uid=1,
                notes="N",
                lineage=DESIGN,
                predecessors=(PredecessorLink(1, "start_to_finish", 600, "eh"),),
            ),
        ),
    )

    assert write_project(planning).decode() == (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n"
        '<Project xmlns="http://schemas.microsoft.com/project/2007">'
        "<SaveVersion>14</SaveVersion><Name>Order</Name><StartDate>2026-03-02T08:00:00</StartDate>"
        "<CurrencyCode></CurrencyCode><CalendarUID>1</CalendarUID><MinutesPerDay>480</MinutesPerDay>"
        "<MinutesPerWeek>2400</MinutesPerWeek><DaysPerMonth>20</DaysPerMonth>"
        "<ExtendedAttributes><ExtendedAttribute><FieldID>188743731</FieldID>"
        "<FieldName>Text1</FieldName><Alias>Waterfall.lineage</Alias></ExtendedAttribute>"
        "</ExtendedAttributes>"
        "<Calendars><Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>"
        "<WeekDays><WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>"
        "<WeekDay><DayType>2</DayType><DayWorking>1</DayWorking><WorkingTimes>"
        "<WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>"
        "<WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>"
        "</WorkingTimes></WeekDay></WeekDays></Calendar></Calendars>"
        "<Tasks><Task><UID>1</UID><ID>1</ID><Name>A</Name><OutlineLevel>1</OutlineLevel>"
        "<Milestone>0</Milestone><ConstraintType>0</ConstraintType><Manual>0</Manual></Task>"
        "<Task><UID>2</UID><ID>2</ID><Name>B</Name><OutlineLevel>1</OutlineLevel>"
        "<Start>2026-03-02T08:00:00</Start><Finish>2026-03-02T09:30:30</Finish>"
        "<Duration>PT1H30M30S</Duration><DurationFormat>3</DurationFormat>"
        "<Milestone>0</Milestone><ConstraintType>0</ConstraintType><CalendarUID>1</CalendarUID>"
        "<Notes>N</Notes><PredecessorLink><PredecessorUID>1</PredecessorUID><Type>2</Type>"
        "<LinkLag>600</LinkLag><LagFormat>6</LagFormat></PredecessorLink>"
        f"<ExtendedAttribute><FieldID>188743731</FieldID><Value>{DESIGN}</Value>"
        "</ExtendedAttribute><Manual>1</Manual></Task></Tasks></Project>"
    )


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_planning_written_is_valid_against_the_schema(schema: etree.XMLSchema) -> None:
    written = write_project(read_project(SAVED).project)

    assert schema.validate(etree.fromstring(written, hardened_parser())), schema.error_log


FULL = MsProject(
    start=at("2026-03-02T08:00:00"),
    name="Full",
    calendar_uid=1,
    minutes_per_day=480,
    minutes_per_week=2400,
    days_per_month=20,
    calendars=(STANDARD,),
    tasks=(
        MsTask(uid=1, name="Root", outline_level=1),
        *(
            MsTask(
                uid=10 + index,
                name=f"Constraint {constraint}",
                outline_level=2,
                duration=timedelta(hours=8),
                duration_unit="d",
                start=at("2026-03-02T08:00:00"),
                finish=at("2026-03-02T17:00:00"),
                constraint=constraint,
                constraint_date=(
                    at("2026-03-02T08:00:00") if constraint in DATE_CONSTRAINTS else None
                ),
            )
            for index, constraint in enumerate(CONSTRAINT_TYPES)
        ),
        MsTask(
            uid=30,
            name="Links",
            outline_level=2,
            duration=timedelta(hours=8),
            duration_unit="d",
            predecessors=(
                PredecessorLink(10, "finish_to_finish", 480, "d"),
                PredecessorLink(11, "finish_to_start", 0, "h"),
                PredecessorLink(12, "start_to_finish", -60, "min"),
                PredecessorLink(13, "start_to_start", 25, "percent"),
            ),
        ),
        MsTask(
            uid=31,
            name="Done",
            outline_level=2,
            duration=timedelta(0),
            duration_unit="d",
            milestone=True,
            start=at("2026-03-02T17:00:00"),
            finish=at("2026-03-02T17:00:00"),
        ),
    ),
)


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_planning_with_every_constraint_link_lag_format_and_a_milestone_is_valid(
    schema: etree.XMLSchema,
) -> None:
    written = write_project(FULL)

    assert schema.validate(etree.fromstring(written, hardened_parser())), schema.error_log
    assert read_project(written).project == FULL


@pytest.mark.requirement("WF-QUA-0080-A")
def test_an_element_out_of_the_order_of_the_schema_makes_the_file_invalid(
    schema: etree.XMLSchema,
) -> None:
    root = etree.fromstring(write_project(PLANNING), hardened_parser())
    task = root.find("{*}Tasks/{*}Task")
    assert task is not None
    manual = task.find("{*}Manual")
    assert manual is not None
    task.insert(0, manual)

    assert not schema.validate(root)


def test_a_planning_without_tasks_nor_calendars_is_read_back_the_same() -> None:
    planning = MsProject(start=None)

    assert read_project(write_project(planning)) == ReadProject(planning)


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_character_xml_forbids_is_dropped_from_a_text_when_written() -> None:
    planning = MsProject(start=None, tasks=(MsTask(uid=1, name="a\x0bb", outline_level=1),))

    assert read_project(write_project(planning)).project.tasks[0].name == "ab"


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_negative_duration_is_refused_when_written() -> None:
    planning = MsProject(
        start=None,
        tasks=(MsTask(uid=1, name="A", outline_level=1, duration=timedelta(hours=-1)),),
    )

    with pytest.raises(ValueError, match="-1 day, 23:00:00"):
        write_project(planning)


def _tasks_file(*tasks: str) -> bytes:
    return (
        '<Project xmlns="http://schemas.microsoft.com/project"><Tasks>'
        + "".join(tasks)
        + "</Tasks></Project>"
    ).encode()


@pytest.mark.requirement("WF-QUA-0080-A")
def test_progress_and_costs_count_the_tasks_without_children_only() -> None:
    content = _tasks_file(
        "<Task><UID>1</UID><OutlineLevel>1</OutlineLevel><PercentComplete>40</PercentComplete>"
        "<Cost>500</Cost></Task>",
        "<Task><UID>2</UID><OutlineLevel>2</OutlineLevel><PercentComplete>40</PercentComplete>"
        "<Cost>500</Cost></Task>",
    )

    assert read_project(content).ignored == (Ignored("progress", 1), Ignored("costs", 1))


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_lineage_is_found_by_the_field_when_its_alias_was_renamed() -> None:
    content = (
        '<Project xmlns="http://schemas.microsoft.com/project"><ExtendedAttributes>'
        "<ExtendedAttribute><FieldID>188743731</FieldID><Alias>Mine</Alias></ExtendedAttribute>"
        "</ExtendedAttributes><Tasks>"
        "<Task><UID>1</UID><OutlineLevel>1</OutlineLevel><ExtendedAttribute>"
        f"<FieldID>188743731</FieldID><Value>{DESIGN}</Value></ExtendedAttribute></Task>"
        "<Task><UID>2</UID><OutlineLevel>1</OutlineLevel><ExtendedAttribute>"
        "<FieldID>188743731</FieldID><Value>by hand</Value></ExtendedAttribute></Task>"
        "</Tasks></Project>"
    ).encode()

    tasks = read_project(content).project.tasks

    assert [task.lineage for task in tasks] == [DESIGN, None]


@pytest.mark.requirement("WF-QUA-0080-A")
def test_an_attribute_without_a_field_is_not_a_lineage() -> None:
    content = _tasks_file(
        "<Task><UID>1</UID><OutlineLevel>1</OutlineLevel><ExtendedAttribute>"
        f"<Value>{DESIGN}</Value></ExtendedAttribute></Task>"
    )

    assert read_project(content).project.tasks[0].lineage is None


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_lineage_field_with_a_renamed_alias_is_not_a_custom_field() -> None:
    content = (
        b'<Project xmlns="http://schemas.microsoft.com/project"><ExtendedAttributes>'
        b"<ExtendedAttribute><FieldID>188743731</FieldID><Alias>Mine</Alias></ExtendedAttribute>"
        b"</ExtendedAttributes></Project>"
    )

    assert read_project(content).ignored == ()


def test_an_entity_of_the_file_is_never_resolved() -> None:
    content = (
        b'<?xml version="1.0"?>\n<!DOCTYPE Project [<!ENTITY name SYSTEM "file:///etc/hostname">]>'
        b'<Project xmlns="http://schemas.microsoft.com/project"><Name>&name;</Name></Project>'
    )

    assert read_project(content).project.name is None


TASK = "<Tasks><Task><UID>1</UID><OutlineLevel>1</OutlineLevel>{}</Task></Tasks>"
LINK = "<PredecessorLink>{}</PredecessorLink>"


@pytest.mark.parametrize(
    ("content", "element"),
    [
        ("not xml", "xml"),
        ('<Plan xmlns="http://schemas.microsoft.com/project"/>', "Project"),
        ('<Project xmlns="urn:other"/>', "Project"),
        ("<MinutesPerDay>eight</MinutesPerDay>", "MinutesPerDay"),
        ("<StartDate>2 March</StartDate>", "StartDate"),
        ("<Tasks><Task><Name>A</Name><OutlineLevel>1</OutlineLevel></Task></Tasks>", "UID"),
        ("<Tasks><Task><UID>1</UID></Task></Tasks>", "OutlineLevel"),
        ("<Tasks><Task><UID>1</UID><OutlineLevel>2</OutlineLevel></Task></Tasks>", "OutlineLevel"),
        (
            (
                "<Tasks><Task><UID>1</UID><OutlineLevel>1</OutlineLevel></Task>"
                "<Task><UID>1</UID><OutlineLevel>1</OutlineLevel></Task></Tasks>"
            ),
            "UID",
        ),
        (TASK.format(LINK.format("<PredecessorUID>9</PredecessorUID>")), "PredecessorUID"),
        (TASK.format(LINK.format("<Type>1</Type>")), "PredecessorUID"),
        (TASK.format(LINK.format("<PredecessorUID>1</PredecessorUID><Type>4</Type>")), "Type"),
        (TASK.format("<Milestone>yes</Milestone>"), "Milestone"),
        (TASK.format("<Duration>P1M</Duration>"), "Duration"),
        (TASK.format("<Duration>PT</Duration>"), "Duration"),
        (TASK.format("<DurationFormat>19</DurationFormat>"), "DurationFormat"),
        (TASK.format("<DurationFormat>13</DurationFormat>"), "DurationFormat"),
        (TASK.format("<FixedCost>much</FixedCost>"), "FixedCost"),
        (TASK.format("<FixedCost>NaN</FixedCost>"), "FixedCost"),
        (TASK.format("<FixedCost>Infinity</FixedCost>"), "FixedCost"),
        (TASK.format("<PercentComplete>sNaN</PercentComplete>"), "PercentComplete"),
        (TASK.format("<PercentComplete>NaN</PercentComplete>"), "PercentComplete"),
        ("<StartDate>2026-03-02T08:00:00Z</StartDate>", "StartDate"),
        (TASK.format("<Start>2026-03-02T08:00:00+02:00</Start>"), "Start"),
        ("<MinutesPerDay>1_0</MinutesPerDay>", "MinutesPerDay"),
        ("<MinutesPerDay>\u0661\u0662</MinutesPerDay>", "MinutesPerDay"),
        (
            (
                "<Calendars><Calendar><UID>1</UID><WeekDays><WeekDay><DayType>2</DayType>"
                "<WorkingTimes><WorkingTime><FromTime>8h</FromTime></WorkingTime></WorkingTimes>"
                "</WeekDay></WeekDays></Calendar></Calendars>"
            ),
            "FromTime",
        ),
    ],
)
def test_a_file_the_reader_cannot_read_is_refused_naming_what_is_wrong(
    content: str, element: str
) -> None:
    if not content.startswith(("not", "<Plan", "<Project")):
        content = f'<Project xmlns="http://schemas.microsoft.com/project">{content}</Project>'

    with pytest.raises(UnreadableProjectError) as refusal:
        read_project(content.encode())

    assert refusal.value.element == element
