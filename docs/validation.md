# Engineering evidence — 11 October 2026

## Actual emulator execution

The initial proof ran mGBA's Windows libretro core, not a simulated engine.
It booted the original ARM homebrew, held RIGHT for 30 frames and produced
different 240×160 PNGs. It exported a 430,144-byte savestate and 32,768-byte SRAM
save. Twelve integration tests passed locally; two queue tests also passed.

Deployment uses pinned mGBA **0.10.5**, compiled on Ubuntu 24.04 at commit
`26b7884bc25a5933960f3cdcd98bac1ae14d42e2`. The verified Linux library SHA-256 is
`93ada796a83e00994d57682b304033c5c122a74ac60ebe35ef18cfe53d4e2247`.

[Final hosted verification and publication run](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/actions/runs/38181287872)
executed **15 passing tests** in 46.951 seconds before publishing. Tests cover
actual pixel/SRAM changes, deterministic replay, a new core continuing a session,
battery import/export, all ten buttons, bounds, lifecycle errors, conflicts,
duplicate Issues, invalid input, persistent cooldowns, injected failure rollback,
authenticated snapshot corruption, README preservation, queue pagination and
development/production queue isolation.

## GitHub-native end-to-end turns

These Issues were submitted through the actual rendered GitHub README controls,
using the browser, and processed by separate hosted runners. The development
queue is triggered by trusted engine pushes before the workflows reach `main`.

| Issue | Input | Persisted frame counter | Total accepted turns |
| --- | --- | ---: | ---: |
| [#28](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/issues/28) | RIGHT 24 | 146 | 1 |
| [#29](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/issues/29) | A 12 | 160 | 2 |
| [#30](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/issues/30) | B 120 | 282 | 3 |

The first publication run is
[38180909076](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/actions/runs/38180909076).
The second is
[38181072261](https://github.com/ravazzoligabriel-commits/ravazzoligabriel-commits/actions/runs/38181072261).
The third is the final run linked above. The screen SHA changed from
`0b3615430428b8a64ff1b5ac2836008612fc8488c35e66a01315290e953cc0cb`
after RIGHT to
`01ef8e01d30f3f9f31210c577df509d873efc7b94df62f1f5e5cc577153ea1f9`
after B. The short A turn advanced the emulator state without a changed display;
we do not claim every valid input necessarily changes visible pixels.

GitHub's Markdown API rendered ten command links and the real image. Browser
inspection confirmed the bezel, controls, attribution, counter and preserved
profile content. A versioned image filename changed with the actual screen hash.

## Problems found and corrected

Initial hosted tests failed on continuation after restore. mGBA's libretro SRAM
pointer can expose the old frontend buffer while the restored game writes to a
savedata mask. The engine now reads the authoritative SAVEDATA extension from a
fresh mGBA serialization and verifies it against the separately persisted battery
export. A test creates a new core and checks a subsequent conflicting input.
Deferred save attachment is completed before restoring the state as well.

The simple homebrew renderer can miss very short holds while drawing. Homebrew
README links now hold for 60 frames; FireRed links retain 12 frames. Both remain
bounded to 120 and capture only actual emulator output.

## Explicitly untested

No legally usable FireRed cartridge was supplied. No FireRed gameplay, Pallet
Town location, cartridge-specific battery behavior or private production
installation is claimed as tested. Private storage checks and deployment
instructions are implemented; installing the cartridge is a later user step.
