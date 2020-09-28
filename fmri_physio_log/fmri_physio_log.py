import datetime
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict
from typing import Dict
from typing import Tuple
from typing import TypeVar
from typing import Union

import numpy as np

from . import constants as c


class PhysioLog:
    def __init__(self, filename: Union[str, Path]):
        self.filename = Path(filename)

        self.ts: np.ndarray
        self.rate: int
        self.params: Tuple[int, int, int, int, int]

        self.ecg: MeasurementSummary
        self.puls: MeasurementSummary
        self.resp: MeasurementSummary
        self.ext: MeasurementSummary

        self.nr: NrSummary

        self.mdh: LogTime
        self.mpcu: LogTime

        # this method sets all of the above values
        self.parse()

    def parse(self):
        content = self.filename.read_text()
        lines = content.splitlines()

        self.parse_data_line(lines.pop(0))

        measurements: DefaultDict[str, Dict[str, int]] = defaultdict(dict)
        nr: DefaultDict[str, Dict[str, int]] = defaultdict(dict)
        timestamps: DefaultDict[str, Dict[str, int]] = defaultdict(dict)
        for line in lines:
            if self.is_measurement_line(line):
                name, params = self.parse_measurement_line(line)
                measurements[name].update(params)
            elif self.is_nr_line(line):
                name, params = self.parse_nr_line(line)
                nr[name].update(params)
            elif self.is_time_line(line):
                name, params = self.parse_time_line(line)
                timestamps[name].update(params)
            else:
                pass

        for attr, kwargs in measurements.items():
            setattr(self, attr, MeasurementSummary(**kwargs))

        for attr, kwargs in nr.items():
            setattr(self, attr, NrSummary(**kwargs))

        for attr, kwargs in timestamps.items():
            setattr(self, attr, LogTime(**kwargs))

    @staticmethod
    def is_measurement_line(line: str) -> bool:
        return any(line.startswith(prefix) for prefix in c.MEASUREMENT_PREFIXES)

    @staticmethod
    def is_nr_line(line: str) -> bool:
        return any(line.startswith(prefix) for prefix in c.NR_PREFIXES)

    @staticmethod
    def is_time_line(line: str) -> bool:
        return any(line.startswith(prefix) for prefix in c.TIME_PREFIXES)

    def parse_data_line(self, line: str) -> None:
        """Parses the data line (first line) of a physio file.

        Args:
            line (str): The line to parse.

        Note:
            This method updates: self.ts, self.rate and self.params
        """
        values = [int(v) for v in line.split(" ")]
        self.params = tuple(values[:5])  # type: ignore
        self.rate = values[2]
        self.ts = np.array([v for v in values[5:] if v < 5000])

    @staticmethod
    def parse_measurement_line(line: str) -> Tuple[str, Dict[str, int]]:
        """Parses lines starting with any of the values in
        constants.MEASUREMENT_PREFIXES

        Args:
            line (str): The line to parse.

        Returns:
            Tuple[str, Dict[str, int]]: The first element is the line name, the second
            element is a dict mapping parameter names to the associated values.

        Examples:
            >>> line = 'PULS Freq Per: 64 926'
            >>> PhysioLog.parse_measurement_line(line)
            ('puls', {'freq': 64, 'per': 926})
            >>> line = 'RESP Min Max Avg StdDiff: 3960 3960 3960 0'
            >>> PhysioLog.parse_measurement_line(line)
            ('resp', {'min': 3960, 'max': 3960, 'avg': 3960, 'std_diff': 0})
        """
        name, param_string = re.sub(r" +", " ", line).split(" ", 1)
        return name.lower(), group_params(param_string)

    @staticmethod
    def parse_nr_line(line: str) -> Tuple[str, Dict[str, int]]:
        """Parses lines starting with any of the values in constants.NR_PREFIXES

        Args:
            line (str): The line to parse.

        Returns:
            Tuple[str, Dict[str, int]]: The first element is the line name, the second
            element is a dict mapping parameter names to the associated values.

        Examples:
            >>> line = 'NrTrig NrMP NrArr AcqWin: 0 0 0 0'
            >>> PhysioLog.parse_nr_line(line)
            ('nr', {'nr_trig': 0, 'nr_m_p': 0, 'nr_arr': 0, 'acq_win': 0})
        """
        return ("nr", group_params(line))

    @staticmethod
    def parse_time_line(line: str) -> Tuple[str, Dict[str, int]]:
        """Parses lines starting with any of the values in constants.TIME_PREFIXES

        Args:
            line (str): The line to parse.

        Returns:
            Tuple[str, Dict[str, int]]: The first element is the line name, the second
            element is a dict mapping start/stop to the associated value.

        Examples:
            >>> line = 'LogStopMDHTime:   51988085'
            >>> PhysioLog.parse_time_line(line)
            ('mdh', {'stop': 51988085})
            >>> line = 'LogStartMPCUTime: 51596615'
            >>> PhysioLog.parse_time_line(line)
            ('mpcu', {'start': 51596615})
        """
        event_type, time_string = re.split(r": +", line)
        result = re.search(r"Log(?P<key>S[a-z]+)(?P<name>[A-Z]+)Time", event_type)
        name = result.group("name").lower()
        key = result.group("key").lower()
        value = int(time_string)
        return name, {key: value}


@dataclass
class MeasurementSummary:
    freq: int
    per: int
    min: int
    max: int
    avg: int
    std_diff: int


@dataclass
class NrSummary:
    nr_trig: int
    nr_m_p: int
    nr_arr: int
    acq_win: int


TLogTime = TypeVar("TLogTime", bound="LogTime")


class LogTime:
    def __init__(self, start: int, stop: int):
        self.start = start
        self.stop = stop
        self.start_time = self.logptime(start)
        self.stop_time = self.logptime(stop)

    def __repr__(self):
        start, stop = self.start, self.stop
        return f"{self.__class__.__name__}(start={start!r}, stop={stop!r})"

    def __eq__(self: TLogTime, o: TLogTime) -> bool:
        return isinstance(o, LogTime) and self.start == o.start and self.stop == o.stop

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


def group_params(s: str):
    """Maps parameter names to paramter values specified in a parameter string.

    Args:
        s (str): The parameter string to parse.

    Returns:
        Dict[str, int]: The mapping of parameter names to parameter values.

    Note:
        Parameter names are converted from PascalCase to snake_case.

    Examples:
        >>> param_string = 'Freq Per: 64 926'
        >>> group_params(param_string)
        {'freq': 64, 'per': 926}
        >>> param_string = 'Min Max Avg StdDiff: 923 931 925 1'
        >>> group_params(param_string)
        {'min': 923, 'max': 931, 'avg': 925, 'std_diff': 1}
    """
    param_names, param_values = re.split(r": +", s)
    return dict(
        zip(
            (to_snake_case(name) for name in param_names.split(" ")),
            (int(value) for value in param_values.split(" ")),
        )
    )


def to_snake_case(s: str) -> str:
    """Converts a string from PascalCase to snake_case.

    Args:
        s (str): The string to convert.

    Returns:
        str: The converted string.

    Examples:
        >>> s1 = 'PascalCase'
        >>> to_snake_case(s1)
        'pascal_case'
        >>> s2 = 'SomeOtherName'
        >>> to_snake_case(s2)
        'some_other_name'
        >>> s3 = 'ThisIsAVariableName'
        >>> to_snake_case(s3)
        'this_is_a_variable_name'
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()
