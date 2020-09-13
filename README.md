# Parse MRI PMU (Physio-Log) Files

This small library parses Siemens PMU files. These are `*.puls`, `*.resp`, `*.ecg` and `*.ext` files produced by the Siemens Physiological Monitoring Unit (PMU) which look something like:

```text
1 8 20 2 367 508 520 532 638 708 790 814 1037 1108 1072 1190 1413 1495 1695 ...
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
```

## Installation

```bash
pip install fmri-physio-log
```

## Usage

Assuming the above sample log file (with truncated first line) is called `sample.puls`, then we have:

```python
import fmri_physio_log as fpl

log = fpl.PhysioLog('sample.puls')

log.ts  # array([ 508,  520,  532,  638,  708,  790,  814, 1037, 1108, 1072, 1190, 1413, 1495, 1695])
log.rate  # 20
log.params  # (1, 8, 20, 2, 367)

log.ecg  # MeasurementSummary(freq=0, per=0, min=0, max=0, avg=0, std_diff=0)
log.puls  # MeasurementSummary(freq=72, per=823, min=355, max=1646, avg=795, std_diff=5)
log.resp  # MeasurementSummary(freq=0, per=0, min=0, max=0, avg=0, std_diff=0)
log.ext  # MeasurementSummary(freq=0, per=0, min=0, max=0, avg=0, std_diff=0)

log.nr  # NrSummary(nr_trig=0, nr_m_p=0, nr_arr=0, acq_win=0)

log.mdh  # LogTime(start=36632877, stop=39805825)
log.mpcu  # LogTime(start=36632400, stop=39804637)

# For convenience the start and stop times are available
# as python datetime.time objects as well
log.mdh.start_time  # datetime.time(10, 10, 32, 877000)
log.mdh.stop_time  # datetime.time(11, 3, 25, 825000)
log.mpcu.start_time  # datetime.time(10, 10, 32, 400000)
log.mpcu.stop_time  # datetime.time(11, 3, 24, 637000)
```
