import {SENTENCE_DELIMITERS} from '../sentenceDelimiters.js';
import {normalizeSpeechChunk} from './normalizeChunk.js';

/** Mirrors rinna/utils.py split_speech_to_chunks: splits on sentence
 * delimiters, but not while inside a paired bracket/quote, and treats a run
 * of consecutive delimiters (e.g. "！？") as a single boundary. */
export function splitSpeechToChunks(speech: string): string[] {
	const chars = Array.from(speech);
	const chunks: string[] = [];
	let currentChunk = '';
	let isInsideParentheses = false;

	for (let i = 0; i < chars.length; i++) {
		const c = chars[i] as string;
		currentChunk += c;

		if (/\p{Ps}/u.test(c)) {
			isInsideParentheses = true;
		} else if (/\p{Pe}/u.test(c)) {
			isInsideParentheses = false;
		} else if (SENTENCE_DELIMITERS.includes(c) && !isInsideParentheses) {
			const next = chars[i + 1];
			if (next !== undefined && SENTENCE_DELIMITERS.includes(next)) {
				continue;
			}
			chunks.push(currentChunk);
			currentChunk = '';
		}
	}

	if (currentChunk !== '') {
		chunks.push(currentChunk);
	}

	return chunks.map(normalizeSpeechChunk);
}
