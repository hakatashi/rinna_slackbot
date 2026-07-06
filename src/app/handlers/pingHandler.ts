import type {RinnaPingPayload} from '../../contracts/pubsubPayloads.js';
import type {AppDependencies} from '../deps.js';

const PING_STALE_MS = 20_000;

/**
 * Mirrors worker.py's rinna-ping handling: a health-check round trip. The
 * ping's timestamp is embedded as the topic id's trailing numeric segment
 * (e.g. "rinna-ping-<epoch-ms>"); pings older than 20s are silently
 * ignored, otherwise a rinna-pong reply is published to that same
 * ephemeral topic.
 */
export async function pingHandler(
	payload: RinnaPingPayload,
	deps: AppDependencies,
): Promise<void> {
	const tsSegment = payload.topicId.split('-').at(-1) ?? '';
	const ts = Number.parseInt(tsSegment, 10);
	const currentTime = deps.clock.now().getTime();

	if (currentTime - ts > PING_STALE_MS) return;

	await deps.publisher.publish(payload.topicId, {
		type: 'rinna-pong',
		mode: deps.mode,
	});
}
