import datetime
from pathlib import Path

import pytest

import fmri_physio_log as fpl


def test_measurement_summary():
    m = fpl.MeasurementSummary(freq=1, per=2, min=3, max=4, avg=5, std_diff=6)
    assert m.freq == 1
    assert m.per == 2
    assert m.min == 3
    assert m.max == 4
    assert m.avg == 5
    assert m.std_diff == 6


def test_nr_summary():
    n = fpl.NrSummary(nr_trig=1, nr_m_p=2, nr_arr=3, acq_win=4)
    assert n.nr_trig == 1
    assert n.nr_m_p == 2
    assert n.nr_arr == 3
    assert n.acq_win == 4


def test_log_time():
    l = fpl.LogTime(3_599_000, 3_600_001)  # noqa: E741
    assert l.start == 3599000
    assert l.stop == 3600001
    assert l.start_time == datetime.time(0, 59, 59)
    assert l.stop_time == datetime.time(1, 0, 0, 1000)


INPUT1_S = """\
1 2 40 280 1236 1251 5000 1679 1871 5003
ECG  Freq Per: 0 0
PULS Freq Per: 75 790
RESP Freq Per: 11 5400
EXT  Freq Per: 0 0
ECG  Min Max Avg StdDiff: 0 0 0 0
PULS Min Max Avg StdDiff: 211 1055 530 47
RESP Min Max Avg StdDiff: 4400 5600 5000 81
EXT  Min Max Avg StdDiff: 0 0 0 0
NrTrig NrMP NrArr AcqWin: 0 0 0 0
LogStartMDHTime:  45927830
LogStopMDHTime:   46462892
LogStartMPCUTime: 45927920
LogStopMPCUTime:  46462615
6003
"""


def test_physio_log_simple_1():
    log = fpl.PhysioLog.from_string(INPUT1_S)

    expected = [1236, 1251, 1679, 1871]
    assert len(log.ts) == len(expected)
    assert all(a == e for a, e in zip(log.ts, expected))

    assert log.rate == 40
    assert log.params == (1, 2, 40, 280)
    assert log.info == []

    assert len(log.data) == log.n_params + len(log.ts)
    assert log.data == [*log.params, *log.ts]

    assert log.ecg == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)
    assert log.puls == fpl.MeasurementSummary(75, 790, 211, 1055, 530, 47)
    assert log.resp == fpl.MeasurementSummary(11, 5400, 4400, 5600, 5000, 81)
    assert log.ext == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)

    assert log.nr == fpl.NrSummary(0, 0, 0, 0)

    assert log.mdh == fpl.LogTime(start=45927830, stop=46462892)
    assert log.mpcu == fpl.LogTime(start=45927920, stop=46462615)


INPUT2_S = """\
1 8 20 2 367 508 520 532 638 708 790 5000 1037 1108 1072 1190 1413 5003
ECG  Freq Per: 0 0
PULS Freq Per: 72 823
RESP Freq Per: 0 0
EXT  Freq Per: 0 0
ECG  Min Max Avg StdDiff: 0 0 0 0
PULS Min Max Avg StdDiff: 355 1646 795 5
RESP Min Max Avg StdDiff: 0 0 0 0
EXT  Min Max Avg StdDiff: 0 0 0 0
NrTrig NrMP NrArr AcqWin: 0 0 0 0
LogStartMDHTime:  36632877
LogStopMDHTime:   39805825
LogStartMPCUTime: 36632400
LogStopMPCUTime:  39804637
6003
"""


def test_physio_log_simple_2():
    log = fpl.PhysioLog.from_string(INPUT2_S)

    expected = [367, 508, 520, 532, 638, 708, 790, 1037, 1108, 1072, 1190, 1413]
    assert len(log.ts) == len(expected)
    assert all(a == e for a, e in zip(log.ts, expected))

    assert log.rate == 20
    assert log.params == (1, 8, 20, 2)
    assert log.info == []

    assert len(log.data) == log.n_params + len(log.ts)
    assert log.data == [*log.params, *log.ts]

    assert log.ecg == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)
    assert log.puls == fpl.MeasurementSummary(72, 823, 355, 1646, 795, 5)
    assert log.resp == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)
    assert log.ext == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)

    assert log.nr == fpl.NrSummary(0, 0, 0, 0)

    assert log.mdh == fpl.LogTime(start=36632877, stop=39805825)
    assert log.mpcu == fpl.LogTime(start=36632400, stop=39804637)


INPUT3_S = """\
1 1 2 40 280 5002 LOGVERSION 102 6002 5002 TRIGGERMETHOD 10 6002 5002 MSGTYPE 103 6002 5002 MSGTYPE 220 eTriggerMethod: 10, minLimitCh1: 0, maxLimitCh1: 0, minLimitAVF: 0, maxLimitAVF: 0 6002 5002 MSGTYPE 210 6002 2048 10240 2048 10240 2048 5003
ECG  Freq Per: 0 0
PULS Freq Per: 148 405
RESP Freq Per: 12 4660
EXT  Freq Per: 0 0
ECG  Min Max Avg StdDiff: 0 0 0 0
PULS Min Max Avg StdDiff: 180 1142 498 17
RESP Min Max Avg StdDiff: 4400 5740 4973 44
EXT  Min Max Avg StdDiff: 0 0 0 0
NrTrig NrMP NrArr AcqWin: 0 0 0 0
LogStartMDHTime:  45927805
LogStopMDHTime:   46228520
LogStartMPCUTime: 45927897
LogStopMPCUTime:  46227375
6003
"""


def test_physio_log_with_info():
    log = fpl.PhysioLog.from_string(INPUT3_S)

    expected = [2048, 10240, 2048, 10240, 2048]
    assert len(log.ts) == len(expected)
    assert all(a == e for a, e in zip(log.ts, expected))

    assert log.rate == 40
    assert log.params == (1, 1, 2, 40, 280)
    assert len(log.info) == 5

    assert len(log.data) == log.n_params + len(log.ts)
    assert log.data == [*log.params, *log.ts]

    assert log.ecg == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)
    assert log.puls == fpl.MeasurementSummary(148, 405, 180, 1142, 498, 17)
    assert log.resp == fpl.MeasurementSummary(12, 4660, 4400, 5740, 4973, 44)
    assert log.ext == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)

    assert log.nr == fpl.NrSummary(0, 0, 0, 0)

    assert log.mdh == fpl.LogTime(start=45927805, stop=46228520)
    assert log.mpcu == fpl.LogTime(start=45927897, stop=46227375)


INPUT4_S = """\
1 2 40 280 5002 Logging PULSE signal: reduction factor = 1, PULS_SAMPLES_PER_SECOND = 50; PULS_SAMPLE_INTERVAL = 20000 6002 1653 1593 5000 1510 1484 5002
ACQ FINISHED
 6002 3093 3096 3064 5000 3016 2926 5003
ECG  Freq Per: 0 0
PULS Freq Per: 66 906
RESP Freq Per: 18 3260
EXT  Freq Per: 0 0
ECG  Min Max Avg StdDiff: 0 0 0 0
PULS Min Max Avg StdDiff: 731 1113 914 1
RESP Min Max Avg StdDiff: 3080 4540 3779 73
EXT  Min Max Avg StdDiff: 0 0 0 0
NrTrig NrMP NrArr AcqWin: 0 0 0 0
LogStartMDHTime:  47029710
LogStopMDHTime:   47654452
LogStartMPCUTime: 47030087
LogStopMPCUTime:  47652240
6003
"""


def test_physio_log_with_multiline_body():
    log = fpl.PhysioLog.from_string(INPUT4_S)

    expected = [1653, 1593, 1510, 1484, 3093, 3096, 3064, 3016, 2926]
    assert len(log.ts) == len(expected)
    assert all(a == e for a, e in zip(log.ts, expected))

    assert log.rate == 40
    assert log.params == (1, 2, 40, 280)
    assert len(log.info) == 2

    assert len(log.data) == log.n_params + len(log.ts)
    assert log.data == [*log.params, *log.ts]

    assert log.ecg == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)
    assert log.puls == fpl.MeasurementSummary(66, 906, 731, 1113, 914, 1)
    assert log.resp == fpl.MeasurementSummary(18, 3260, 3080, 4540, 3779, 73)
    assert log.ext == fpl.MeasurementSummary(0, 0, 0, 0, 0, 0)

    assert log.nr == fpl.NrSummary(0, 0, 0, 0)

    assert log.mdh == fpl.LogTime(start=47029710, stop=47654452)
    assert log.mpcu == fpl.LogTime(start=47030087, stop=47652240)


def test_physio_log_from_filename_basic(sample_basic_puls_file: Path):
    log = fpl.PhysioLog.from_filename(sample_basic_puls_file)

    _e = [367, 508, 520, 532, 638, 708, 790, 1037, 1108, 1072, 1190, 1413]
    assert len(log.ts) == len(_e)
    assert all(a == e for a, e in zip(log.ts, _e))

    assert log.rate == 20
    assert log.params == (1, 8, 20, 2)

    assert len(log.data) == log.n_params + len(log.ts)
    assert log.data == [*log.params, *log.ts]

    assert log.ecg == fpl.MeasurementSummary(
        freq=0,
        per=0,
        min=0,
        max=0,
        avg=0,
        std_diff=0,
    )
    assert log.puls == fpl.MeasurementSummary(
        freq=72,
        per=823,
        min=355,
        max=1646,
        avg=795,
        std_diff=5,
    )
    assert log.resp == fpl.MeasurementSummary(
        freq=0,
        per=0,
        min=0,
        max=0,
        avg=0,
        std_diff=0,
    )
    assert log.ext == fpl.MeasurementSummary(
        freq=0,
        per=0,
        min=0,
        max=0,
        avg=0,
        std_diff=0,
    )
    assert log.ext2 is None

    assert log.nr == fpl.NrSummary(nr_trig=0, nr_m_p=0, nr_arr=0, acq_win=0)

    assert log.mdh == fpl.LogTime(start=36632877, stop=39805825)
    assert log.mpcu == fpl.LogTime(start=36632400, stop=39804637)

    assert log.mdh.start_time == datetime.time(10, 10, 32, 877000)
    assert log.mdh.stop_time == datetime.time(11, 3, 25, 825000)
    assert log.mpcu.start_time == datetime.time(10, 10, 32, 400000)
    assert log.mpcu.stop_time == datetime.time(11, 3, 24, 637000)


def test_physio_log_from_filename_with_ext2(sample_with_ext2_file: Path):
    log = fpl.PhysioLog.from_filename(sample_with_ext2_file)

    _e = [
        2594,
        2642,
        2690,
        2732,
        2774,
        2816,
        2852,
        2888,
        2924,
        2960,
        3062,
        3044,
        3020,
        2996,
        2978,
        2954,
    ]
    assert len(log.ts) == len(_e)
    assert all(a == e for a, e in zip(log.ts, _e))

    assert log.rate == 40
    assert log.params == (1, 2, 40, 280)

    assert len(log.data) == log.n_params + len(log.ts)
    assert log.data == [*log.params, *log.ts]

    assert log.ecg == fpl.MeasurementSummary(
        freq=0,
        per=0,
        min=65,
        max=1142,
        avg=532,
        std_diff=238,
    )
    assert log.puls == fpl.MeasurementSummary(
        freq=91,
        per=657,
        min=153,
        max=4642,
        avg=659,
        std_diff=7,
    )
    assert log.resp == fpl.MeasurementSummary(
        freq=19,
        per=3020,
        min=1780,
        max=8880,
        avg=3025,
        std_diff=873,
    )
    assert log.ext == fpl.MeasurementSummary(
        freq=0,
        per=0,
        min=0,
        max=0,
        avg=0,
        std_diff=0,
    )
    assert log.ext2 == fpl.MeasurementSummary(
        freq=0,
        per=0,
        min=0,
        max=0,
        avg=0,
        std_diff=0,
    )

    assert log.nr == fpl.NrSummary(nr_trig=0, nr_m_p=0, nr_arr=0, acq_win=0)

    assert log.mdh == fpl.LogTime(start=71409847, stop=71774492)
    assert log.mpcu == fpl.LogTime(start=71412077, stop=71776222)

    assert log.mdh.start_time == datetime.time(19, 50, 9, 847000)
    assert log.mdh.stop_time == datetime.time(19, 56, 14, 492000)
    assert log.mpcu.start_time == datetime.time(19, 50, 12, 77000)
    assert log.mpcu.stop_time == datetime.time(19, 56, 16, 222000)


sample_dir = Path(__file__).parent.parent / "samples"
sample_files = [p for p in sample_dir.rglob("*") if p.is_file()]


@pytest.mark.parametrize(
    "filename",
    sample_files,
    ids=lambda p: str(p.relative_to(sample_dir)),
)
def test_samples_files_are_parsable(filename: Path):
    log = fpl.PhysioLog.from_filename(filename)
    assert log is not None


def test_warning_emitted_from_direct_constructor_call():
    """Test that we emit a warning when calling the constructor directly.

    Remove in v0.4.x
    """
    with pytest.warns(FutureWarning):
        fpl.PhysioLog(INPUT1_S)
