# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Slack bot ("りんな" and friends — りんな/うな/うか/うの/たたも, five personas) that listens for
messages on Google Cloud Pub/Sub, generates in-character dialogue with a locally-hosted LLM
(via `llama-server`), moderates it, and posts it to Slack. The Pub/Sub messages are relayed from a
separate Slack-event-listening service (`hakatabot-firebase-functions`, not part of this repo);
this repo only contains the "signal → generate → moderate → post" worker.

This is a TypeScript rewrite of a prior Python implementation. It is built as a hexagonal
(ports & adapters) application: `domain/` holds pure, dependency-free logic; `ports/` declares the
interfaces the app needs; `adapters/` implement those interfaces against real I/O; `app/` wires
handlers to ports; `composeRoot.ts` and `main.ts` are the only places that construct concrete
adapters and touch the outside world.

## Commands

- Install deps: `npm install`
- Typecheck: `npm run typecheck`
- Run tests: `npm test` (Vitest)
- Lint / format: `npm run lint`, `npm run lint:fix`, `npm run format`
- Run the worker: `npm start` (or `npm run dev` for `tsx watch`)
- Check persona intro token lengths against the prompt budget: `npm run check:intro` (reads
  `data/personas.yaml`; uses a running `llama-server`'s `/tokenize` if reachable at
  `LLAMA_SERVER_HOST:LLAMA_SERVER_PORT`, otherwise falls back to a char-count estimate)

## System overview

```
Slack → hakatabot-firebase-functions (Cloud Function)
             ↓ Pub/Sub (rinna-signal / rinna-meaning / rinna-temperature / rinna-ping)
        src/main.ts (this repo)
             ↓ LLM generation (llama-server) + moderation
        Slack (post response) + Firestore (log rinna-responses)
             ↓
        hakatabot-firebase-functions (info command reads rinna-responses)
```

### Signal emission (`hakatabot-firebase-functions/functions/src/slack.ts`)

This repo does **not** contain the signal-emission code — see `src/contracts/README.md` for the
full correspondence table and manual-sync procedure with that sibling repo. In short:

- **`rinna-signal`** fires on an explicit persona mention or an autonomous heuristic (recent
  activity, cooldown, random chance — all decided on the sibling repo's side). Payload:
  `{type: 'rinna-signal', humanMessages, botMessages, lastSignal}`, where `humanMessages` is a
  15-minute sliding window of Slack messages.
- **`rinna-meaning`** fires when TSG slackbot posts a message ending in `わからん`. Payload:
  `{type: 'rinna-meaning', word, ts}`.
- **`rinna-temperature`** fires on any message with text `うなの体温`.
- **`rinna-ping`** is a health-check round trip (not emitted by the sibling repo's `slack.ts`);
  this worker replies with `{type: 'rinna-pong', mode}` published to the topic id embedded in the
  ping payload.

### Firestore `rinna-responses` — the `info` command

Every posted chunk is logged to the `rinna-responses` Firestore collection. The sibling repo's
Cloud Function exposes an **info command**: replying `info` to a persona message in a Slack thread
looks up that message's `ts` in `rinna-responses` and posts back the input dialog, generated
speech, and moderation results.

## Architecture

### Entry points

- `src/main.ts` — the only place with top-level side effects: loads env, calls `composeApp`,
  subscribes to Pub/Sub, and wires `SIGINT`/`SIGTERM` to stop the `llama-server` subprocess
  gracefully.
- `src/composeRoot.ts` — the only place that constructs concrete adapters (Slack, Firestore,
  Pub/Sub, Google/Azure moderation, llama-server process + client) and assembles the
  `AppDependencies` bag used by handlers.

### Domain (`src/domain/`) — pure, no I/O, heavily unit-tested

- `personas.ts` — the five persona ids and their static Slack display metadata.
- `prompt/buildPrompt.ts` — builds the "intro + dialogue so far" prompt for a persona, growing the
  included history one message at a time (newest-first) until the token budget
  (`MAX_PROMPT_TOKENS=11500`, `MAX_HISTORY_TOKENS=2000`) would be exceeded, then keeping the last
  window that fit. Takes an injected `tokenize` function so it never touches the network.
- `speech/streamParser.ts` — consumes raw LLM text pieces and yields complete sentences as their
  delimiter is confirmed (not mid-run of `！？`, not inside a bracket/quote).
- `speech/splitChunks.ts` — the non-streaming counterpart, used by the `@うな先生` meaning flow.
- `dispatch/detectPersonas.ts` — which personas a trigger message mentions (in fixed order,
  possibly more than one), and the random fallback pool when none are mentioned (excludes たたも).
- `dispatch/trimHistory.ts` — `/clear` and `/no_clear` handling.
- `dispatch/moderationRules.ts` — the allowlist-aware offensive-term check.

### Ports (`src/ports/`) and adapters (`src/adapters/`)

`LlmClient`, `ChatPoster`, `Moderator`, `ResponseLog`, `MessageSource`/`Publisher`, `Thermometer`,
`Clock`, `Random` are the interfaces `app/` handlers depend on. Concrete implementations:

- `LlamaServerClient` + `llamaServerProcess.ts` — spawns and health-checks the `llama-server`
  binary (path from `LLAMA_SERVER_BINARY`, default `~/Documents/GitHub/llama.cpp/build/bin/llama-server`),
  then talks to it over HTTP. `streamGenerate` tracks `「`/`」` nesting depth itself to stop
  generation exactly at the outer speech's closing bracket, without cutting off a quoted word
  inside the speech.
- `modelDownloader.ts` — pulls the GGUF from Hugging Face Hub via `@huggingface/hub`.
- `SlackChatPoster`, `GoogleLanguageModerator`, `AzureContentModerator` (+ `ParallelModerator` to
  run both concurrently), `FirestoreResponseLog`, `PubSubClient`, `RocmSmiThermometer`.

### App (`src/app/`)

- `handlers/signalHandler.ts` — the core chat flow: thread-reply logic for stale triggers,
  `/clear`/`/no_clear`, then either the `@うな先生` meaning flow or firing each mentioned persona
  in turn (each one's reply is appended to the running history before the next persona generates,
  so multiple personas mentioned in one message "see" each other's replies).
- `handlers/meaningHandler.ts` — the `@うな先生` / `rinna-meaning` flow. Always sleeps 1s before
  posting every chunk, including the first (unlike the persona-response flow, which skips the
  sleep before its first chunk).
- `handlers/pingHandler.ts`, `handlers/temperatureHandler.ts`.
- `router.ts` — dispatches on the parsed Pub/Sub payload's `type` (exhaustiveness-checked). Ack and
  error-handling semantics intentionally differ per branch — see the comment in `router.ts`.
- `mutex.ts` — serializes `rinna-signal`/`rinna-meaning` generation so only one LLM request runs
  at a time.

### Data (`data/`, gitignored)

- `data/personas.yaml`, `data/usernames.yaml` — persona intros and Slack user id → display name
  mapping. Not checked in; copy `data/personas.example.yaml` / `data/usernames.example.yaml` (which
  *are* checked in, showing the schema) and fill in real content. Loaded and validated at startup
  by `src/config/loadPersonaData.ts`.

### Tests

Domain logic is tested with plain input/output assertions (no mocks). Adapters that talk HTTP are
tested against an in-process fake server. App handlers are tested with fake ports
(`tests/app/fakeDeps.ts`) — no real Slack/Firestore/Google/Azure credentials are ever needed to run
`npm test`.

## Explicitly out of scope for this rewrite

- Non-`llama-server` model backends (in-process `llama.cpp`, `transformers`) — the old worker
  supported three interchangeable backends; only the `llama-server` one is kept.
- `llm-benchmark-submission` handling — was already mostly dead/commented-out code.
- A local SOCKS5 proxy for outbound traffic.
- The Windows tray launcher (CPU/GPU toggle, crash-restart supervision) — process supervision is
  now expected to live in an external service manager; `LLAMA_GPU` is a plain env var.
