import {randomBytes} from 'node:crypto';
import type {Firestore} from 'firebase-admin/firestore';
import type {ResponseLog, ResponseRecord} from '../ports/ResponseLog.js';

const ID_ALPHABET =
	'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

function randomId(length = 20): string {
	const bytes = randomBytes(length);
	let out = '';
	for (let i = 0; i < length; i++) {
		out += ID_ALPHABET[(bytes[i] as number) % ID_ALPHABET.length];
	}
	return out;
}

/** Mirrors worker.py's writes to the `rinna-responses` Firestore collection,
 * used by the sibling repo's `info` command. */
export class FirestoreResponseLog implements ResponseLog {
	constructor(
		private readonly firestore: Firestore,
		private readonly collectionName = 'rinna-responses',
	) {}

	async log(record: ResponseRecord): Promise<void> {
		await this.firestore
			.collection(this.collectionName)
			.doc(randomId())
			.set({
				createdAt: record.createdAt,
				character: record.character,
				inputMessages: record.inputMessages,
				inputText: record.inputText,
				inputDialog: record.inputDialog,
				inputTokenLength: record.inputTokenLength,
				output: record.output,
				outputSpeech: record.outputSpeech,
				config: record.config,
				message: record.message,
				moderations: record.moderations,
				...(record.threadTs !== undefined ? {thread_ts: record.threadTs} : {}),
			});
	}
}
