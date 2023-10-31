from __future__ import annotations

import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any
from typing import NamedTuple
from typing import TextIO

from fmri_physio_log._generated import Lark_StandAlone as _Lark_StandAlone
from fmri_physio_log._generated import Tree as _Tree
from fmri_physio_log._generated import Visitor_Recursive as _Visitor_Recursive


# If this line moves files, update .bumpversion.cfg
__version__ = "0.3.1"


class PhysioLog:
    def __init__(self, content: str, *, n_params: int = 4):
        self.content = content
        self.n_params = n_params

        self._parser = _Lark_StandAlone()
        self._visitor = _PhysioLogVisitor()

        self.data: list[int]

        self.params: tuple[int, ...]
        self.ts: list[int]
        self.rate: int
        self.info: list[str]

        self.ecg: MeasurementSummary
        self.puls: MeasurementSummary
        self.resp: MeasurementSummary
        self.ext: MeasurementSummary
        self.ext2: MeasurementSummary | None = None

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
        tree = self._parser.parse(self.content)
        self._visitor.visit(tree)

        # interpret the parsed content
        self._body()
        self._footer()

    def _body(self) -> None:
        """Interpret the physio file body (everything before the '5003' tag)

        The body is composed of the initial physio params
        (which includes the sampling rate), info sections,
        and the data.
        """
        self.params = tuple(self._visitor._data[: self.n_params])
        self.rate = self.params[2] if len(self.params) == 4 else self.params[3]
        self.info = self._visitor._info[:]
        self.ts = self._visitor._data[self.n_params :]

    def _footer(self) -> None:
        """Interpret the physio footer (everything after the '5003' tag)

        The footer is composed of the 'measurement summaries'
        (freq, per, min, max, etc.), the 'nr summary' and 'log times'
        """
        # set the nr summary attributes
        self.nr = NrSummary(*self._visitor._nr)

        # set the measurement summary attributes
        for attr, values in self._visitor._summaries.items():
            setattr(self, attr.lower(), MeasurementSummary(*values))

        # set the log time attributes
        for attr, values in self._visitor._logs.items():
            setattr(self, attr.lower(), LogTime(*values))


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
        """Converts an integer denoting milliseconds past midnight to a
        datetime.time object.

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


class _PhysioLogVisitor(_Visitor_Recursive):
    def __init__(self):
        self._data: list[int] = []
        self._info: list[str] = []
        self._summaries: dict[str, list[int]] = defaultdict(list)
        self._nr: list[int] = []  # only the last one is used
        self._logs: dict[str, list[int]] = defaultdict(list)

    def data(self, tree: _Tree):
        self._data = [i for i in _iter_ints(tree)]

    def info(self, tree: _Tree):
        _info = tree.children[0]
        if isinstance(_info, str):
            self._info.append(_info)

    def rate_line(self, tree: _Tree):
        modality = next(tree.find_pred(lambda t: t.data == "modality")).children[0]
        if isinstance(modality, str):
            # rate lines come before stat lines, so the rate data will get
            # packed in first in the resulting list
            # TODO(andrewrosss): add runtime check to validate this claim
            self._summaries[modality].extend([i for i in _iter_ints(tree)])

    def stat_line(self, tree: _Tree):
        modality = next(tree.find_pred(lambda t: t.data == "modality")).children[0]
        if isinstance(modality, str):
            self._summaries[modality].extend([i for i in _iter_ints(tree)])

    def nr_line(self, tree: _Tree):
        self._nr = [i for i in _iter_ints(tree)]

    def log_line(self, tree: _Tree):
        log_type = tree.children[0]

        if not isinstance(log_type, str):
            raise SyntaxError(f"Unknown log type {log_type!r}")
        elif "MDH" in log_type:
            log_type = "MDH"
        elif "MPCU" in log_type:
            log_type = "MPCU"
        else:
            raise SyntaxError(f"Unknown log type {log_type!r}")

        # start times come before stop times, so they'll get packed in
        # first in the resulting list
        # TODO(andrewrosss): add runtime check to validate this claim
        self._logs[log_type].extend([i for i in _iter_ints(tree)])


def _iter_ints(tree: _Tree):
    if hasattr(tree.data, "type") and tree.data.type == "INT":  # type: ignore
        yield int(tree.data)
    else:
        for c in tree.children:
            if isinstance(c, _Tree):
                yield from _iter_ints(c)
            elif c.type == "INT":
                yield int(c)
