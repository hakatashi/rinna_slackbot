import {SENTENCE_DELIMITERS} from '../sentenceDelimiters.js';

/** Mirrors rinna/utils.py normalize_speech_chunk: strips a single trailing
 * 。/｡ but leaves a run of two or more (e.g. an ellipsis-like "。。") intact. */
export function normalizeSpeechChunk(chunk: string): string {
	if (/[。｡]$/.test(chunk) && !/[。｡]{2,}$/.test(chunk)) {
		return chunk.replace(/[。｡]$/, '');
	}
	return chunk;
}

/** Mirrors rinna/utils.py join_chunks_to_speech. */
export function joinChunksToSpeech(chunks: readonly string[]): string {
	let result = '';
	for (const [i, chunk] of chunks.entries()) {
		result += chunk;
		if (i < chunks.length - 1) {
			const lastChar = chunk.at(-1);
			if (
				chunk.length === 0 ||
				lastChar === undefined ||
				!SENTENCE_DELIMITERS.includes(lastChar)
			) {
				result += '。';
			} else {
				result += ' ';
			}
		}
	}
	return result;
}
