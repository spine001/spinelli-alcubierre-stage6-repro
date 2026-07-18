# Stage 4 N101 Resource-Sampler Correction

**Date:** 2026-07-17

The N101 scientific calculation and its `/usr/bin/time -v` accounting are
valid. The original sampling loop selected the `/usr/bin/time` parent
because its command line contained the Python command. Consequently, the
sampled process VmRSS was approximately 1.6 MiB and did not represent the
Python worker.

The corrected N111 sampler selects only a process whose `comm` begins with
`python` and whose command line contains both the N111 runner filename and
the unique output directory.

The corrected sampler records:

- actual Python PID and process name;
- VmRSS, VmSwap, VmSize, VmHWM, and VmPeak;
- process major faults;
- system MemAvailable and swap occupancy;
- cumulative `pswpin` and `pswpout` page counters.

The raw N101 resource-sample CSV remains published for provenance. Its
process-memory columns must not be used. Its system MemAvailable and
system swap columns remain valid because they were read from `/proc/meminfo`.
