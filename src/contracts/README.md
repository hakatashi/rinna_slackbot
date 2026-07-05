# Pub/Sub contract with `hakatabot-firebase-functions`

`src/contracts/pubsubPayloads.ts` mirrors the payloads published by the sibling
repository `hakatabot-firebase-functions` (`functions/src/slack.ts`) to the
`hakatabot` Pub/Sub topic. **This repo cannot edit that repo** — the two are
kept in sync by hand. Whenever `slack.ts` changes what it publishes, update the
schemas here to match, and vice versa.

## Correspondence table

| Type | Emitted by (`slack.ts`) | Consumed by (this repo) | Notes |
|---|---|---|---|
| `rinna-signal` | `pubsubClient.topic('hakatabot').publishMessage(...)` in the "Rinna signal" handler (~line 471) | `signalHandler` | `humanMessages`/`botMessages` are `Message[]` (see `interface Message`, line 59) — a 15-minute sliding window slice, already trimmed by the block list / opt-out logic on the sender side. |
| `rinna-meaning` | "Wakaran-penalty" handler (~line 258) | `meaningHandler` | Fired when TSG slackbot posts a message ending in `わからん`. |
| `rinna-ping` | *(not currently emitted by slack.ts — originates from an external health-check caller)* | `pingHandler` | Worker replies by publishing `{type: 'rinna-pong', mode}` back to `topicId`; this repo does not parse `rinna-pong` since it only ever produces it. |
| `rinna-temperature` | "Rinna temperature signal" handler (~line 271) | `temperatureHandler` | Payload also carries `ts`/`channel`, currently unused by the handler (kept optional in the schema for forward-compat). |

## `Message` field mapping

`slack.ts`'s `interface Message` declares `text`/`user`/`username`/`bot_id` etc.
as required, but real Slack events omit many of them. `humanMessageSchema`
only requires `ts` and treats everything else as optional/nullable, matching
what the Python worker actually read via `dict.get(...)`.

## Sync procedure

1. When `slack.ts` adds/removes a published field or a new `type`, update the
   corresponding zod schema in `pubsubPayloads.ts` in the same PR as this
   repo's handler change.
2. Run `npm run typecheck && npm test` — the `router.ts` switch is exhaustive
   (`assertNever`), so an unhandled new `type` fails to compile.
3. Update this table.
