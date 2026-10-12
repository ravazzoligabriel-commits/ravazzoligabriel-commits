# FireRed no perfil — uma partida compartilhada

Este projeto transforma o perfil do GitHub em uma aventura coletiva de Pokémon
FireRed. Todos controlam o mesmo treinador e continuam o mesmo save. O emulador
mGBA roda na automação do GitHub; o README exibe a última imagem real produzida
pelo jogo. A ROM e o estado completo ficam em um repositório privado. Visitantes
participam enviando comandos, sem instalar nada nem receber a ROM.

**Como participar:** clique em um botão do README, entre no GitHub e confirme em
**Create / Submit new issue**, depois clique em **Close issue**. Volte ao perfil
e atualize a página. A direção move o personagem ou o cursor, **A** confirma e
avança diálogos, **B** cancela, **START** abre o menu e **SELECT** usa o item
registrado quando disponível. **L/R** abrem a ajuda na configuração padrão do
FireRed; as opções do jogo podem alterar esse comportamento.

O clique envia 12 frames de botão pressionado. Para ajustar a duração, edite o
título: `[gba] RIGHT 60`, por exemplo. Aceita-se um comando por conta a cada
30 segundos, com duração de 1 a 120 frames. Espere a nova tela antes de decidir
o próximo movimento: outro visitante pode ter jogado nesse intervalo.

Os controles são imagens clicáveis inspiradas no GBA. Cada botão abre uma Issue;
o GitHub não executa o emulador nem captura o teclado diretamente no README.
O avanço acontece por comandos e pode levar minutos para aparecer. O estado
fica salvo automaticamente entre comandos, inclusive durante diálogos e menus.

Referência do comportamento de ajuda: [código do sistema de ajuda do FireRed](https://github.com/pret/pokefirered/blob/master/src/help_system.c).

## Technical operation and deployment

This repository runs an actual mGBA core and shows its video output in the README.
The live profile runs the user-supplied **Pokémon FireRed USA** cartridge from
private storage. The public repository also ships the source of **Pixel Adventure**,
original MIT-licensed ARM homebrew for reproducible tests.
Move the explorer using direction buttons; A/B change its color and START resets
its position. This deliberately small cartridge tests real GBA MMIO, video, input
and SRAM. The demo is separate from the privately installed FireRed session.
See [feasibility](feasibility.md) and [validation](validation.md).

## Play

Click a README control, sign in and submit the prefilled Issue. Titles use exactly
`[gba] RIGHT 12`, with one of UP, DOWN, LEFT, RIGHT, A, B, L, R, START, SELECT and
an optional duration of 1–120 frames (default 12). Bodies, comments, labels and
attachments are never executable input. Homebrew turns release the key for two
frames; FireRed turns release it for 60 frames so animations can progress after
the input. FireRed's first boot runs 3,600 frames to complete the opening sequence.
A frame is approximately 1/60 second; menus may need several turns.
The homebrew README links use a 60-frame hold to accommodate its simple ARM
software renderer; FireRed links use 12. An input may leave pixels unchanged if
the game ignores it or has not completed a redraw; the actual state still advances.

The worker handles up to 50 new Issues in ascending Issue-number order and closes
them after successfully publishing. Accepted and rejected turns appear in
`assets/community/history.json`; the README reports the latest accepted turn.
One command per account per 30 seconds is accepted, based on creation timestamps.
Other visitors continue the same session. Reopening an already processed Issue
does not repeat the turn. Closing an unprocessed Issue also triggers processing;
both open and closed commands remain eligible until recorded in the durable ledger.

## Activate the homebrew adventure

1. Review and merge the implementation PR into `main`. The actual profile loads
   the default-branch README; a development branch only provides a preview.
2. Enable Issues and Actions. Allow the workflow's declared `contents: write` and
   `issues: write`. Branch protection must permit the bot's image/state commits,
   or publication will fail visibly and queued commands remain retryable.
3. Configure repository Actions secret `GBA_STATE_KEY` to a base64 encoding of 32
   cryptographically random bytes. A key was installed during initial engineering
   validation; do not overwrite it while using an existing encrypted session.
   Back up the key privately; a lost key makes snapshots unreadable.
4. Set repository variable `GBA_GAME_MODE=homebrew` (the default). Run **Community
   GBA turns** on `main` once to boot; subsequent Issues and scheduled sweeps keep
   it running. Do not copy the development canary session into production.

The build pins mGBA 0.10.5 source commit
`26b7884bc25a5933960f3cdcd98bac1ae14d42e2`, Python 3.12 and dependency versions.
Only the emulator shared library is cached. ROMs, SRAM and savestates are never
uploaded as artifacts or dependency caches. Raw local files are ignored by Git.

## Install your legally obtained FireRed ROM privately

1. Create a **private** storage repository. On its `main` branch place your
   cartridge at `cartridge.gba` using a private transfer. Do not create a public
   release, artifact, Issue attachment or fork containing the cartridge.
2. Install a read/write SSH deploy key restricted to that private repository,
   and save its private key as profile Actions secret `GBA_PRIVATE_SSH_KEY`.
   This installation uses that repository-scoped key. Alternatively, create a
   fine-grained token restricted to that repository with Contents
   read/write. Store it as Actions secret `GBA_PRIVATE_TOKEN` on this profile repo.
   A dedicated GitHub App installation token is preferable for a production setup.
3. Set `GBA_PRIVATE_REPOSITORY=owner/private-storage`, `GBA_GAME_MODE=firered`, and
   `GBA_ROM_SHA256` to the SHA-256 of your cartridge. The workflow verifies that
   the remote repository is actually private and that the ROM digest matches.
4. Run the workflow on `main`. A new session is created in the private repository
   under `.community/session.enc`; the public demo state remains separate. Only
   the approved display pixels and public command metadata are published.
5. Play through boot/menu dialogs with Issues. See `validation.md` for the
   cartridge-specific results from this installation.

The public screenshot necessarily contains displayed game artwork. The cartridge,
BIOS, extracted assets, SRAM and savestate stay private. No proprietary BIOS is
needed; mGBA uses its built-in implementation. Do not add cartridge paths to logs
or broaden the core cache. If private storage isn't configured, FireRed mode
refuses to publish state to the public repo.

## Recovery and maintenance

Snapshots include mGBA state, raw battery save, last real video callback, frame
counter and full deduplication ledger, authenticated with AES-256-GCM and a fresh
nonce. The homebrew snapshot is encrypted in the public repository; FireRed's
snapshot is encrypted in private storage. Encryption does not hide public player
attribution or command history.

A turn failure restores RAM, SRAM, input state and counter; no ledger entry is
added, so the queued Issue can retry. A failed public Git push leaves Issues open.
Homebrew state and pixels commit together. For private FireRed storage, the next
run rebuilds the public view from saved private state after a failed publication.
Never force-push automatically or fall back to a new game on decryption failure.

Back up the session repository and key. To roll back, disable the turns workflow,
restore a selected snapshot commit **and its matching image/ledger**, then enable
it. Reopen only commands deliberately excluded by that rollback. To change ROM,
begin a separate session; to upgrade mGBA, test a copy privately before migrating.
Version/ROM mismatch halts rather than silently restarting. Development canary
state is isolated in the feature branch and consumes real `[gba-test]` Issues.
Before merge, a maintainer pushes an engine change to run this development queue;
default-branch Issue-triggered processing becomes available after merge.

Full ledger grows over time; public history is capped at 200 records. Review
repository size and runtime before very large campaigns. Scheduled jobs incur
compute/API costs even when idle; disable the workflow when retiring the project.

## Security boundary

Only trusted repository workflow code accesses write credentials. No PR-triggered
job has write permissions or game secrets. Issue text is parsed with a strict
full-match regular expression, never placed in shell commands. API inputs are
JSON encoded; git operations use argument arrays. Core/actions are pinned. The
workflow never checks out a player-supplied branch or installs player code.
Existing unrelated profile workflows are preserved and are outside this engine's
security boundary. Anyone can submit Issues; maintainers remain responsible for
moderation, runner usage and reviewing changes to trusted default-branch code.

## Reproduce locally

Install Python 3.12 and `python -m pip install -r requirements.txt`. Build the
same mGBA source with the commands in `.github/actions/setup-mgba/action.yml`,
or use an mGBA libretro DLL on Windows for local experiments. Core versions must
match when sharing savestates. Then:

```sh
python homebrew/build.py runtime/demo.gba
MGBA_CORE=runtime/core/mgba_libretro.so python -m unittest discover -s tests -v
```

The suite executes the actual emulator: changing pixels/SRAM, all ten buttons,
bounded commands, deterministic replay, new-core restoration, conflicts,
duplicate events, invalid input, cooldown, injected failure, tamper detection,
battery export/import and README preservation. No fake emulator is used.

## Interface and platform constraints

The graphite bezel is original presentation around unmodified emulator pixels
scaled with nearest-neighbor interpolation. `screen.png` exposes the 240×160 raw
frame. README image filenames depend on screen SHA-256 to change the URL when
pixels change. GitHub may delay images and requires page refresh. No keyboard
controls, JavaScript execution, automatic submission or live video is promised.
Neither a separate game-hosting website nor an external account is required.
