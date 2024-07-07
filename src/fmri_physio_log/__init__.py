from __future__ import annotations

import contextlib
import datetime
import re
import warnings
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import NamedTuple
from typing import TextIO

from fmri_physio_log._generated import Lark_StandAlone as _PhysioLogParser
from fmri_physio_log._generated import Tree as _Tree
from fmri_physio_log._generated import Visitor_Recursive as _Visitor_Recursive


# If this line moves files, update .bumpversion.cfg
__version__ = "0.3.3"

__all__ = (
    "PhysioLog",
    "MeasurementSummary",
    "NrSummary",
    "LogTime",
)


class PhysioLog:
    N_PARAMS_DEFAULT = 4

    def __init__(self, content: str, *, n_params: int | None = None):
        self.__maybe_emit_init_warning()

        # constructor args
        self.content = content
        self.n_params = (
            self.determine_params_heuristically(content)
            if n_params is None
            else n_params
        )

        # internal attributes
        self._parser = _PhysioLogParser()
        self._visitor = _PhysioLogVisitor()

        # public attributes
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
    def from_string(cls, content: str, *, n_params: int | None = None):
        with _disable_init_warning():
            return cls(content, n_params=n_params)

    @classmethod
    def from_file(cls, file: TextIO, *, n_params: int | None = None):
        content = file.read()
        with _disable_init_warning():
            return cls(content, n_params=n_params)

    @classmethod
    def from_filename(cls, filename: str | Path, *, n_params: int | None = None):
        content = Path(filename).read_text()
        with _disable_init_warning():
            return cls(content, n_params=n_params)

    def parse(self):
        # parse the content with the grammer
        tree = self._parser.parse(self.content)

        # interpret the parsed content
        self._visitor.visit(tree)
        self._body()
        self._footer()

    def _body(self) -> None:
        """Interpret the physio file body (everything before the '5003' tag)

        The body is composed of the initial physio params
        (which includes the sampling rate), info sections,
        and the data.
        """
        self.params = tuple(self._visitor._data[: self.n_params])
        self.rate = self.params[2] if self.n_params == 4 else self.params[3]
        self.info = self._visitor._info[:]
        self.ts = self._visitor._data[self.n_params :]
        self.data = self._visitor._data.copy()

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

    @classmethod
    def determine_params_heuristically(cls, content: str) -> int:
        # if the first 4 or 5 numbers are followed by a 5002 (info/comment
        # section) then we assume that all numbers before that are params
        regex = re.compile(r"^\s*((?:\d+\s+){4,5})5002")
        if (m := regex.match(content)) is not None:
            return len(m.group(1).split())
        return cls.N_PARAMS_DEFAULT

    def __maybe_emit_init_warning(self):
        """Emit a warning if the user uses the constructor directly. Remove in v0.4.x"""
        if _EMIT_INIT_WARNING:
            classname = self.__class__.__name__
            warnings.warn(
                f"Direct use of `{classname}.__init__` (i.e. "
                f"`{classname}(content_str)`) is deprecated. The signature "
                "will change in the 0.4 release. Please use "
                f"`{classname}.from_string(content)` instead (or migrate to "
                f"one of the other `{classname}.from_*` classmethods)",
                FutureWarning,
                stacklevel=2,
            )


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


@dataclass
class LogTime:
    start: int
    stop: int
    start_time: datetime.time = field(init=False, repr=False, compare=False)
    stop_time: datetime.time = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self.start_time = self.logptime(self.start)
        self.stop_time = self.logptime(self.stop)

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
    """Recursively iterate over all integers in a tree (depth-first)"""
    if hasattr(tree.data, "type") and tree.data.type == "INT":  # type: ignore
        yield int(tree.data)
    else:
        for c in tree.children:
            if isinstance(c, _Tree):
                yield from _iter_ints(c)
            elif c.type == "INT":
                yield int(c)


_EMIT_INIT_WARNING = True


@contextlib.contextmanager
def _disable_init_warning():
    """Utility to disable warnings from PhysioLog.__init__ (used by
    PhysioLog classmethods)
    """
    global _EMIT_INIT_WARNING
    _EMIT_INIT_WARNING = False
    try:
        yield
    finally:
        _EMIT_INIT_WARNING = True
