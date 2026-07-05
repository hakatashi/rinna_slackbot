import {rinnaPayloadSchema} from '../contracts/pubsubPayloads.js';
import type {IncomingMessage} from '../ports/MessageSource.js';
import type {AppDependencies} from './deps.js';
import {meaningHandler} from './handlers/meaningHandler.js';
import {pingHandler} from './handlers/pingHandler.js';
import {signalHandler} from './handlers/signalHandler.js';
import {temperatureHandler} from './handlers/temperatureHandler.js';
import {createGenerationMutex} from './mutex.js';

function assertNever(value: never): never {
	throw new Error(`Unhandled payload: ${JSON.stringify(value)}`);
}

/**
 * Mirrors worker.py's pubsub_callback dispatch. Ack/error semantics are
 * intentionally different per branch, matching the original:
 * - rinna-signal / rinna-meaning: serialized by the generation mutex; ack
 *   only fires after the handler succeeds, and a thrown error is logged
 *   and swallowed (message is left to be redelivered).
 * - rinna-ping: no error handling at all — an error propagates and the
 *   message is never acked.
 * - rinna-temperature: errors are caught and logged, but the message is
 *   acked unconditionally regardless.
 */
export function createRouter(deps: AppDependencies) {
	const mutex = createGenerationMutex();

	return async function route(message: IncomingMessage): Promise<void> {
		const parsed = rinnaPayloadSchema.safeParse(message.payload);
		if (!parsed.success) {
			console.error(
				'Unrecognized pubsub payload',
				parsed.error,
				message.payload,
			);
			return;
		}
		const payload = parsed.data;

		switch (payload.type) {
			case 'rinna-signal': {
				await mutex.runExclusive(async () => {
					try {
						await signalHandler(payload, deps);
						message.ack();
					} catch (error) {
						console.error(error);
					}
				});
				return;
			}

			case 'rinna-meaning': {
				await mutex.runExclusive(async () => {
					try {
						await meaningHandler(
							{
								word: payload.word,
								character: 'うな',
								...(payload.ts !== undefined ? {threadTs: payload.ts} : {}),
							},
							deps,
						);
						message.ack();
					} catch (error) {
						console.error(error);
					}
				});
				return;
			}

			case 'rinna-ping': {
				await pingHandler(payload, deps);
				message.ack();
				return;
			}

			case 'rinna-temperature': {
				try {
					await temperatureHandler(deps);
				} catch (error) {
					console.error(error);
				}
				message.ack();
				return;
			}

			default:
				assertNever(payload);
		}
	};
}
