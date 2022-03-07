from __future__ import annotations

import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any
from typing import NamedTuple
from typing import TextIO

from pyparsing import Group
from pyparsing import Literal
from pyparsing import nums
from pyparsing import OneOrMore
from pyparsing import ParseResults
from pyparsing import printables
from pyparsing import Suppress
from pyparsing import Word


__version__ = "0.2.0"


class PhysioLog:
    def __init__(self, content: str):
        self.content = content
        self._grammar = create_grammar()

        self._parse_results: ParseResults

        self.params: tuple[int, ...]
        self.rate: int
        self.info: list[str]
        self.ts: list[int]

        self.ecg: MeasurementSummary
        self.puls: MeasurementSummary
        self.resp: MeasurementSummary
        self.ext: MeasurementSummary

        self.nr: NrSummary

        self.mdh: LogTime
        self.mpcu: LogTime

        # this method sets all of the above values
        self.parse()

    @classmethod
    def from_file(cls, file: TextIO):
        content = file.read()
        return PhysioLog(content)

    @classmethod
    def from_filename(cls, filename: str | Path):
        content = Path(filename).read_text()
        return PhysioLog(content)

    def parse(self):
        # parse the content with the grammer
        self._parse_results = self._grammar.parse_string(self.content)

        # the results are split into two top-level groups: the body and the footer.
        # since ParseResults are iterable we can unpack the sections like this
        body, footer = self._parse_results

        # interpret the results and "populate" this instance
        self._body(body)
        self._footer(footer)

    def _body(self, body: ParseResults) -> None:
        """Interpret the physio file body (everything before the '5003' tag)

        The body is composed of the initial physio params
        (which includes the sampling rate), info sections,
        and the data.
        """
        _params, *_data = body
        self.params = tuple(int(s) for s in _params)
        self.rate = self.params[2] if len(self.params) == 4 else self.params[3]
        self.info = []
        self.ts = []
        for expr in _data:
            if isinstance(expr, ParseResults):
                self.info.append(str(expr[0]))
            elif isinstance(expr, str):
                self.ts.append(int(expr))
            else:
                raise SyntaxError(f"Unknown token in body {expr!r}")

    def _footer(self, footer: ParseResults) -> None:
        """Interpret the physio footer (everything after the '5003' tag)

        The footer si composed of the 'measurement summaries'
        (freq, per, min, max, etc.), the 'nr summary' and 'log times'
        """
        _summaries: dict[str, list[int]] = defaultdict(list)
        _logs: dict[str, list[int]] = defaultdict(list)

        # organize the parsed footer
        for expr in footer:
            if expr.get_name() in ("rate", "stat"):
                # rates come before stats, so they'll get packed in first
                # in the resulting list
                key, *values = expr
                _summaries[key].extend([int(v) for v in values])
            elif expr.get_name() == "nr":
                self.nr = NrSummary(*(int(v) for v in expr))
            elif expr.get_name() == "log":
                # start times come before stop times, so they'll get packed in
                # first in the resulting list
                _, key, value = expr
                _logs[key].append(int(value))
            else:
                raise SyntaxError(f"Unknown token in footer {expr!r}")

        # set the measurement summary attributes
        for attr, values in _summaries.items():
            setattr(self, attr.lower(), MeasurementSummary(*values))

        # set the log time attributes
        for attr, values in _logs.items():
            setattr(self, attr.lower(), LogTime(*values))


def create_grammar():
    _int = Word(nums)

    # footer
    modality = Literal("ECG") | Literal("PULS") | Literal("RESP") | Literal("EXT")
    log_type = Literal("MDH") | Literal("MPCU")
    log_event = Literal("Start") | Literal("Stop")
    rate = (
        Suppress("Freq") + Suppress("Per") + Suppress(":") + _int("freq") + _int("per")
    )
    stat = (
        Suppress("Min")
        + Suppress("Max")
        + Suppress("Avg")
        + Suppress("StdDiff")
        + Suppress(":")
        + _int("min")
        + _int("max")
        + _int("avg")
        + _int("stddiff")
    )
    log_key = Suppress("Log") + log_event("event") + log_type("type") + Suppress("Time")
    log_line = log_key + Suppress(":") + _int("time")
    nr_line = (
        Suppress("NrTrig")
        + Suppress("NrMP")
        + Suppress("NrArr")
        + Suppress("AcqWin")
        + Suppress(":")
        + _int("nrtrig")
        + _int("nrmp")
        + _int("nrarr")
        + _int("acqwin")
    )
    stat_line = modality("modality") + stat
    rate_line = modality("modality") + rate
    footer_line = (
        rate_line("rate") | stat_line("stat") | nr_line("nr") | log_line("log")
    )
    footer = Suppress("5003") + OneOrMore(Group(footer_line)) + Suppress("6003")

    # body
    info = (
        Suppress("5002")
        + OneOrMore(Word(printables), stop_on="6002").set_parse_action(" ".join)
        + Suppress("6002")
    )
    data = OneOrMore(Group(info("info")) | Suppress("5000") | _int, stop_on="5003")
    detailed_params = Group(_int[4, 5]("params")) + Group(info("info"))
    simple_params = Group(_int[4]("params"))
    params = detailed_params | simple_params
    body = params + data

    grammar = Group(body("body")) + Group(footer("footer"))

    return grammar


class MeasurementSummary(NamedTuple):
    freq: int
    per: int
    min: int
    max: int
    avg: int
    std_diff: int


class NrSummary(NamedTuple):
    nr_trig: int
    nr_m_p: int
    nr_arr: int
    acq_win: int


class LogTime:
    def __init__(self, start: int, stop: int):
        self.start = start
        self.stop = stop
        self.start_time = self.logptime(start)
        self.stop_time = self.logptime(stop)

    def __repr__(self):
        start, stop = self.start, self.stop
        return f"{self.__class__.__name__}(start={start!r}, stop={stop!r})"

    def __eq__(self, o: Any) -> bool:
        return (
            isinstance(o, self.__class__)
            and self.start == o.start
            and self.stop == o.stop
        )

    @staticmethod
    def logptime(timestamp: int) -> datetime.time:
        """Converts an integer denoting milliseconds past midnight to a datetime.time object.

        Args:
            timestamp (int): The integer to convert.

        Returns:
            datetime.time: The time object.

        Examples:
            >>> LogTime.logptime(1000)
            datetime.time(0, 0, 1)
            >>> LogTime.logptime(123456)
            datetime.time(0, 2, 3, 456000)
            >>> LogTime.logptime(86_399_999)
            datetime.time(23, 59, 59, 999000)
        """
        hour = int(timestamp / 1000 / 60 / 60)
        min = int(timestamp / 1000 / 60) - hour * 60
        sec = int(timestamp / 1000) - (hour * 60 * 60 + min * 60)
        msec = timestamp - (hour * 1000 * 60 * 60 + min * 1000 * 60 + sec * 1000)
        return datetime.time(hour, min, sec, msec * 1000)  # since midnight
