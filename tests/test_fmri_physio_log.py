import datetime

import numpy as np
from numpy.testing import assert_allclose

import fmri_physio_log as fpl


def test_version():
    assert fpl.__version__ == "0.0.1"


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


def test_physio_log(sample_puls_file):
    log = fpl.PhysioLog(sample_puls_file)

    assert_allclose(
        log.ts,
        np.array(
            [
                508,
                520,
                532,
                638,
                708,
                790,
                814,
                1037,
                1108,
                1072,
                1190,
                1413,
                1495,
                1695,
            ]
        ),
    )
    assert log.rate == 20
    assert log.params == (1, 8, 20, 2, 367)

    assert log.ecg == fpl.MeasurementSummary(
        freq=0, per=0, min=0, max=0, avg=0, std_diff=0
    )
    assert log.puls == fpl.MeasurementSummary(
        freq=72, per=823, min=355, max=1646, avg=795, std_diff=5
    )
    assert log.resp == fpl.MeasurementSummary(
        freq=0, per=0, min=0, max=0, avg=0, std_diff=0
    )
    assert log.ext == fpl.MeasurementSummary(
        freq=0, per=0, min=0, max=0, avg=0, std_diff=0
    )

    assert log.nr == fpl.NrSummary(nr_trig=0, nr_m_p=0, nr_arr=0, acq_win=0)

    assert log.mdh == fpl.LogTime(start=36632877, stop=39805825)
    assert log.mpcu == fpl.LogTime(start=36632400, stop=39804637)

    assert log.mdh.start_time == datetime.time(10, 10, 32, 877000)
    assert log.mdh.stop_time == datetime.time(11, 3, 25, 825000)
    assert log.mpcu.start_time == datetime.time(10, 10, 32, 400000)
    assert log.mpcu.stop_time == datetime.time(11, 3, 24, 637000)
