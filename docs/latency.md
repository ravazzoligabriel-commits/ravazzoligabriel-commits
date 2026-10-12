# Command update delay

Allow approximately **15–30 seconds**, then refresh the profile. This is an
estimate for a warm emulator cache and an available GitHub runner. Busy queues,
a cold build or delayed image caching can take longer. The README is a snapshot
and does not refresh automatically. A button the game ignores may leave the
image unchanged even after successful processing.

## Measurements

Measured on October 12, 2026 (UTC), using GitHub's server timestamps:

| Measurement | Result | Scope |
| --- | ---: | --- |
| Before optimization, six successful Issue-triggered runs | 20–29 seconds; median 22 seconds | Workflow creation to the end of the processing/publication step |
| After optimization, one successful timing check | 14 seconds | Same workflow timing boundary |
| After optimization, Issue event to the end of processing | 16 seconds | Includes 2 seconds before workflow creation |

The timing check reopened already processed Issue #32. Its durable ledger entry
prevented replay, so the check did not move the character or increment the
leaderboard. It exercised setup, private state loading, rendering, publication
checks and automatic Issue closure. It did not measure a new gameplay input or
the browser's image cache. One optimized sample is not a long-term average or a
guarantee for every command.

Source: [optimized run](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/actions/runs/38188123269)
and [Issue #32 event timeline](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/issues/32).
Baseline runs: 38187971577, 38187816503, 38187762273, 38187475118,
38187450169 and 38185109436.

## What changed

Full emulator regression tests and the private cartridge integration test run
on code pushes, scheduled checks and manual runs. Visitor Issue events skip
those repeated suites, removing roughly 5–7 seconds from the measured path.
Runtime validation still checks the cartridge digest, private storage,
authenticated session, emulator compatibility and command validity.
The [code-change verification run](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/actions/runs/38188075621)
passed with both test suites enabled.

Commands remain serialized to protect the shared save. Both submitting and
closing an Issue can trigger processing, but each Issue executes at most once.
The **30-second per-player cooldown** is separate from processing latency.

If the result is slow, check [Actions](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/actions/workflows/community-gba.yml)
before sending another command. If event delivery fails, the scheduled sweep
can recover queued commands; it runs every 15 minutes and can also be delayed.
