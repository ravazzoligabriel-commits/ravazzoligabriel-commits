# Feasibility report — 11 October 2026

## Supported and demonstrated

A profile README can embed the latest real mGBA PNG. Ordinary Markdown links open
prefilled GitHub Issues; authenticated visitors confirm submission there. A trusted
Actions job reads the durable Issue queue, executes a bounded GBA turn, persists
the same adventure and commits a new screenshot. Visitors stay on GitHub.

The implemented adapter uses mGBA's **libretro ABI**, rather than GUI automation.
It exposes cartridge loading, SRAM import/export, input, exact frame stepping,
video callbacks and binary savestates. mGBA's Lua scripting API is another viable
route, but libretro supplies the headless boundary without a display server.
VBA-M also implements libretro; changing emulators would require state migration
and rerunning all compatibility tests. Browser emulators cannot run in a README.

Commands share one session; this is asynchronous collective play, not concurrent
independent multiplayer. Issues are a durable queue. The workflow concurrency
group serializes consumers, while a ledger prevents replay. Sweeps read queued
Issues even if GitHub replaces a pending workflow run. The implementation does
not rely on Actions concurrency slots as a durable queue.

## Experimentally supported / requires installation

The supplied FireRed USA cartridge is installed privately and has been tested
with actual mGBA boot, bounded input, snapshot continuation in a new core and
battery export/import. Browser-submitted Issues update the live profile; see
[validation](validation.md) for hosted evidence. We do not
claim that Pallet Town or any particular game location has been reached. Location
decoding would require a ROM-revision-specific memory adapter and is intentionally
absent rather than inferred from a screenshot.

Exact frame counts are validated. Deterministic replay is demonstrated for the
homebrew ROM on the same core/version; universal determinism across emulator
versions, ROM revisions and RTC-dependent games is not promised. Session loading
checks the ROM digest and core version. Keep the pinned build and take backups
before migrations. For FireRed, both cartridge and state must live in a private
repository, accessed only by trusted workflow code on GitHub-hosted runners.

Publishing private state and a public README uses two repositories and cannot be
one atomic Git transaction. The private state is committed first. An interrupted
public publication is rebuilt from that saved state on the next sweep. Issue IDs
are acknowledged only after successful publication. The homebrew demo commits
encrypted state, ledger and image together in one public-repository transaction.

## Impossible in a README / operational limits

- JavaScript, an iframe emulator, keyboard listeners and inline CSS cannot create
  a live game inside GitHub's sanitized README rendering.
- A link cannot silently submit a command. Signing in and submitting an Issue is
  required; an anonymous visitor may view the screen but cannot play.
- An already open profile page does not update its DOM automatically. Refresh
  after processing; caching can also delay visibility.
- Sub-second input latency is not achievable through Issues and hosted Actions.
  Scheduling, runner startup, API limits and queues add delay. A scheduled sweep
  can be delayed or skipped, and GitHub can disable schedules after inactivity.
- Moderation, account-based cooldowns and bounded turns reduce abuse but do not
  prevent coordinated Sybil accounts or public Issue spam. Owners can disable
  the workflow, close Issues or use GitHub interaction limits.
- Persistent self-hosted runners on public Issue events are unnecessary and expose
  a larger attack surface. This implementation uses disposable hosted runners.

The changing screenshot filename creates a new image URL, reducing stale-image
reuse. GitHub Camo/CDN behavior and profile-page caching still mean that instant
freshness is not guaranteed. The raw PNG and screen SHA provide inspectable evidence.

## Primary references

- [GitHub markup pipeline and sanitizer](https://github.com/github/markup)
- [GitHub anonymized image URLs / Camo](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-anonymized-urls)
- [Workflow events: Issues, dispatch and schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Workflow concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency)
- [Expanded concurrency queues, May 2026](https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/)
- [Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [mGBA scripting support](https://mgba.io/2022/05/29/scripting/)
- [Pinned mGBA libretro implementation](https://github.com/mgba-emu/mgba/blob/26b7884bc25a5933960f3cdcd98bac1ae14d42e2/src/platform/libretro/libretro.c)
