# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Slack bot ("りんな" and friends — りんな/うな/うか/うの/たたも, five personas) that listens for
messages on Google Cloud Pub/Sub, generates in-character dialogue with an LLM, moderates it, and
posts it to Slack. The Pub/Sub messages are relayed from a separate Slack-event-listening service
(not part of this repo); this repo only contains the "signal → generate → moderate → post" worker
and its supporting model-serving code.

## Commands

- Install deps: `poetry install`
- Run tests: `poetry run pytest` (also runs in CI via `.github/workflows/test.yml` on Python 3.10)
- Run a single test file/case: `poetry run pytest tests/rinna/test_generation.py::test_generate_rinna_response`
- Run the worker directly: `poetry run python worker.py <CPU|GPU> <Llama|--llama-server|--llama>`
  (see "Model backends" below for what the second argument controls)
- Windows tray launcher (production deployment): `python app.py` — spawns `worker.py` as a
  subprocess via a hardcoded Poetry path, restarts it on crash, and exposes a CPU/GPU toggle in
  the system tray.
- Regenerate `data/intro.json` / `data/users.json` after editing the Python source files: run
  `data/intro.py` / `data/users.py` respectively (each writes its own JSON file as a side effect).

## System overview

```
Slack → hakatabot-firebase-functions (Cloud Function)
             ↓ Pub/Sub (rinna-signal / rinna-meaning / rinna-temperature)
        worker.py (this repo)
             ↓ LLM generation + moderation
        Slack (post response) + Firestore (log rinna-responses)
             ↓
        hakatabot-firebase-functions (info command reads rinna-responses)
```

### Signal emission (`hakatabot-firebase-functions/functions/src/slack.ts`)

This repo does **not** contain the signal-emission code. That lives in the separate
`hakatabot-firebase-functions` Cloud Functions project. The function `slackEvent` listens to the
Slack Events API (HTTP webhook) and publishes to Pub/Sub topic `hakatabot`. Key behaviours:

**`rinna-signal`** — published when a new message arrives in the sandbox channel (`SANDBOX_ID`):
- Maintains a sliding 15-minute window of `recentHumanMessages` and `recentBotMessages` in
  Firestore state document `slack-rinna-signal`. Persona messages (りんな/うな/うか/うの/たたも)
  posted by `TSG_SLACKBOT_ID` are treated as human messages so they count toward the conversation
  history sent to the worker.
- The signal fires under **two** conditions:
  1. **Explicit mention** — the message matches `りんな、`, `@うな`, `皿洗うか` (full Slack
     username), `@たたも`, etc. (any form that names one of the five personas). Fires immediately.
  2. **Autonomous** — all of: ≥5 recent human messages, bot-message count ≤ half of human-message
     count, ≥3 distinct human users, last signal was ≥60 min ago, and 30% random chance.
- A block list prevents signals from being triggered during bot-hosted games and quizzes
  (e.g., messages matching `ハイパーロボット`, `ソートなぞなぞ`, ending with `ロボット`/`占い`/`将棋`, etc.).
- Users can opt out/in with `@りんな optout` / `@りんな optin`; opted-out users are excluded from
  triggering and their messages are not forwarded.
- The Pub/Sub payload is `{type: 'rinna-signal', botMessages, humanMessages, lastSignal}`.
  `humanMessages` is the 15-minute window slice and is what `worker.py` receives as `data['humanMessages']`.

**`rinna-meaning`** — published when TSG slackbot (`TSG_SLACKBOT_ID`) posts a message whose text
ends with `わからん` (context-free bot explanation flow). Payload: `{type: 'rinna-meaning', word, ts}`.

**`rinna-temperature`** — published when any message with text `うなの体温` is posted.

### Firestore `rinna-responses` — the `info` command

After the worker posts a response and logs it to the `rinna-responses` Firestore collection,
the Cloud Function exposes an **info command**: replying to any persona message in a Slack thread
with the single word `info` triggers a lookup of that message's `ts` in `rinna-responses` and
posts a summary back into the thread, including:
- The formatted input dialog that was fed to the LLM
- The character name and full generated speech
- Google Language Service moderation result (OK/NG + category list)
- Azure Content Moderator result (OK/NG + matched terms)
- `thinking_text` from the config, if present

## Architecture

### Entry points

- `worker.py` — the main long-running process. Loads Slack/Firebase/Azure/Google credentials from
  env, subscribes to Pub/Sub topic `rinna-signal` (project `hakatabot-firebase-functions`), and
  dispatches on `data['type']`:
  - `rinna-signal`: the core chat flow — pulls `humanMessages`, honors inline `/clear` and
    `/no_clear` directives to trim history, detects a persona by substring match on the trigger
    message (`りんな`/`うな`/`うか`/`うの`/`たたも`, falling back to a random persona), and calls
    `rinna_response`/`rinna_meaning`.
  - `rinna-meaning`, `rinna-ping` (pubsub round-trip health check), `rinna-temperature` (reports
    GPU temp via `rocm-smi`), `llm-benchmark-submission` (mostly dead code, commented out).
  - A global `mutex` serializes generation so only one response is produced at a time.
- `app.py` — Windows-only system tray wrapper around `worker.py` for the production host machine.
  Not used in CI/tests.
- `proxy_server.py` — optional local SOCKS5 proxy (`pproxy`), started as a background thread from
  `worker.py` when `ENABLE_PROXY=true`, used to route outbound model-download or API traffic.

### Generation pipeline (`rinna/`)

- `rinna/configs.py` — `character_configs`: per-persona prompt intros (loaded from
  `data/intro.json`, generated by `data/intro.py`), Slack display name/icon, etc. Also loads
  `username_mapping` from `data/users.json` (Slack user ID → display name, generated by
  `data/users.py`) and `una-instruct-prompt.txt`.
- `rinna/generation.py` — turns a list of Slack-style messages into a prompt and back into speech:
  - `_prepare_generation` formats the message history into the persona's "intro + dialogue so far"
    prompt, substituting `[MONTH]`/`[DATE]`/`[WEEKDAY]`/`[HOUR]`/`[MINUTE]`/`[WEATHER]` and
    `{user1}`/`{user2}` (resolved via `get_top2_human_usernames`), then grows the included history
    one message at a time until the tokenized prompt would exceed ~2900 tokens.
  - `generate_rinna_response` (batch) vs. `generate_rinna_response_streaming` (only available when
    `rinna.transformer_models` exposes `stream_text`, i.e. llama-server mode) — the streaming path
    yields one Slack message per detected sentence as tokens arrive, tracking `「」` nesting depth
    itself (`_stream_speech_chunks`) so nested quotes don't prematurely end the persona's speech.
  - `generate_rinna_meaning` — separate "ask うな先生 what a word means" flow, triggered by
    `@うな先生` in the trigger message.
  - Output text is split into `。！？♪｡♡`-delimited chunks (`split_speech_to_chunks` /
    `normalize_speech_chunk` in `rinna/utils.py`) and posted to Slack as separate messages with a
    1s delay between them, then optionally rejoined (`join_chunks_to_speech`) to log as one string.
- `rinna/transformer_models.py` — selects one of three interchangeable text-generation backends at
  import time based on `sys.argv`, each exposing the same `generate_text(token_ids)` /
  `get_token_ids(text)` functions (llama-server mode also exposes `stream_text`):
  - `--llama-server`: spawns a local `llama-server` binary (path hardcoded to
    `~/Documents/GitHub/llama.cpp/build/bin/llama-server`) as a subprocess and talks to it over
    HTTP (`/completion`, `/tokenize`). This is the streaming-capable path and the one used in
    current production. Model weights are pulled via `hf_hub_download` at import time.
  - `--llama`: in-process `llama_cpp.Llama` (GGUF), no subprocess.
  - (no flag): `transformers` `AutoModelForCausalLM`, CPU or CUDA depending on `--gpu`.
  - All three currently point at the same GGUF/HF model id
    (`mradermacher/Qwen3.5-35B-A3B-Base-GGUF` / `Qwen/Qwen3.5-35B-A3B-Base`); swapping models means
    editing all the relevant branches, since there's no shared config for the model id.
- Moderation runs Google `language_v1.classify_text` (adult-content category) and Azure
  `ContentModeratorClient.text_moderation.screen_text` **in parallel** via a `ThreadPoolExecutor`;
  a message is censored (replaced with `##### CENSORED #####`) if either flags it. This happens
  per Slack-chunk, after generation, right before posting — moderation results and full generation
  metadata are logged to Firestore (`rinna-responses` collection) alongside the posted message.

### Tests

- `tests/conftest.py` mocks out all heavy/native dependencies (`transformers`, `torch`, `gstop`,
  `huggingface_hub`, `llama_cpp`, `dotenv`) at the `sys.modules` level before any test imports
  happen, and sets `LLAMA_USE_GPU=0`, so `poetry run pytest` never touches real models or GPUs.
  `tests/rinna/test_generation.py` additionally sets `os.environ["LLAMA_USE_GPU"] = "0"` at import
  time (before importing `rinna.generation`) for the same reason.
- Tests mock `rinna.generation.get_token_ids`/`generate_text` directly rather than going through
  `rinna.transformer_models`, so they're independent of which backend branch would otherwise be
  selected.

### Data files

- `data/intro.json`, `data/users.json` are generated artifacts — the source of truth is
  `data/intro.py` / `data/users.py` (plain Python files with template strings / dicts that get
  dumped to JSON via a top-level side effect on import/run). Edit the `.py` files, then re-run them
  to regenerate the `.json`.
- `data/una-instruct-prompt.txt` — instruction-style prompt for the `@うな先生` "explain a word"
  flow, currently unused (`use_instruction_prompt` is hardcoded `False` in `rinna/generation.py`).

### Misc / auxiliary scripts (`bin/`)

One-off/manual scripts, not part of the worker's runtime: `train.py` (model experiments),
`ask_rinna.py`, `stt.py` (Whisper transcription), `tts.py` (XTTS/TinyLlama experiments),
`test_proxy.js`/`test_proxy.py` (manual SOCKS5 proxy smoke tests, run via `npm run test-proxy` or
directly).
