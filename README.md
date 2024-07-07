# fmri-physio-log

Parse Siemens PMU files

[![PyPI Version](https://img.shields.io/pypi/v/fmri-physio-log.svg)](https://pypi.org/project/fmri-physio-log/)

## Installation

```bash
pip install fmri-physio-log
```

## Overview

This small library parses and loads Siemens PMU files into python. These are `*.puls`, `*.resp`, `*.ecg` and `*.ext` files produced by the Siemens Physiological Monitoring Unit (PMU) which look something like:

```text
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
```

## Usage

By default, `PhysioLog` takes a string as the only parameter:

```python
import fmri_physio_log as fpl

CONTENT = """\
1 8 20 2 5002 LOGVERSION 102 6002 5002 TRIGGERMETHOD 10 6002 367 508 520 532 638 708 790 5000 1037 1108 5002
 data that spans multiple lines ...
6002 1072 1190 1413 5003
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

log = fpl.PhysioLog.from_string(CONTENT)

log.ts  # [367, 508, 520, 532, 638, 708, 790, 1037, 1108, 1072, 1190, 1413]
log.rate  # 20
log.params  # (1, 8, 20, 2)
log.info  # ['LOGVERSION 102', 'TRIGGERMETHOD 10', 'data that spans multiple lines ...']

log.ecg  # MeasurementSummary(freq=0, per=0, min=0, max=0, avg=0, std_diff=0)
log.puls  # MeasurementSummary(freq=72, per=823, min=355, max=1646, avg=795, std_diff=5)
log.resp  # MeasurementSummary(freq=0, per=0, min=0, max=0, avg=0, std_diff=0)
log.ext  # MeasurementSummary(freq=0, per=0, min=0, max=0, avg=0, std_diff=0)
log.ext2 # None - since no EXT2 data in this file; otherwise MeasurementSummary

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

### From an open file

A `PhysioLog` object can also be instantiated from an open file

```python
import fmri_physio_log as fpl

with open("sample.puls", "r") as f:
    log = fpl.PhysioLog.from_file(f)
```

### From a path

A `PhysioLog` object can also be instantiated from a file path (either as a string or a `pathlib.Path` object)

```python
from pathlib import Path

import fmri_physio_log as fpl

# path as string
path_s = "/path/to/my/file.resp"
log = fpl.PhysioLog.from_filename(path_s)

# path as pathlib.Path object
path = Path(path_s)
log = fpl.PhysioLog.from_filename(path)
```

## Implementation References

The following sources were referenced in constructing the grammar:

- [https://cfn.upenn.edu/aguirre/wiki/doku.php?id=public:pulse-oximetry_during_fmri_scanning#pulse-ox_data](https://cfn.upenn.edu/aguirre/wiki/doku.php?id=public:pulse-oximetry_during_fmri_scanning#pulse-ox_data)
- [https://wiki.humanconnectome.org/display/PublicData/Understanding+Timing+Information+in+HCP+Physiological+Monitoring+Files](https://wiki.humanconnectome.org/display/PublicData/Understanding+Timing+Information+in+HCP+Physiological+Monitoring+Files)
- [https://gitlab.ethz.ch/physio/physio-doc/-/wikis/MANUAL_PART_READIN#manual-recording](https://gitlab.ethz.ch/physio/physio-doc/-/wikis/MANUAL_PART_READIN#manual-recording)
- [https://gist.github.com/rtrhd/6172344](https://gist.github.com/rtrhd/6172344)

## Contributing

1. Have or install a recent version of `poetry` (version >= 1.8)
1. Fork the repo
1. Setup a virtual environment (however you prefer)
1. Run `poetry install`
1. Run `pre-commit install`
1. Add your changes (adding/updating tests is always nice too)
1. Commit your changes + push to your fork
1. Open a PR

> [!IMPORTANT]
> If you are marking changes to the grammar (`src/grammar.lark`), you will need to regenerate the parser (`src/fmri_physio_log/_generated.py`) which can be done by running `lark`, for example:
>
> ```bash
> python -m lark.tools.standalone src/grammar.lark > src/fmri_physio_log/_generated.py
> ```
