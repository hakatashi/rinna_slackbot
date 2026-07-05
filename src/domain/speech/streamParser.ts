import type {PersonaId} from '../personas.js';
import {SENTENCE_DELIMITERS} from '../sentenceDelimiters.js';
import {applyRinnaReplacements} from './applyReplacements.js';
import {normalizeSpeechChunk} from './normalizeChunk.js';

/**
 * Mirrors rinna/generation.py _stream_speech_chunks: consumes raw text
 * pieces from the LLM stream and yields complete sentences as soon as their
 * delimiter is confirmed not to be part of a longer run (e.g. "！？") and
 * not inside a bracket/quote. Note this tracks only whether we are
 * currently inside *a* bracket (open/close), not nested bracket depth —
 * that depth tracking happens separately in the llama-server adapter to
 * decide when generation should stop.
 */
export async function* streamSpeechChunks(
	pieces: AsyncIterable<string>,
	character: PersonaId,
): AsyncGenerator<string, void, undefined> {
	let currentChunk = '';
	let isInsideParens = false;
	let pendingSentenceEnd = false;

	for await (const piece of pieces) {
		for (const char of piece) {
			if (pendingSentenceEnd) {
				if (SENTENCE_DELIMITERS.includes(char)) {
					currentChunk += char;
					continue;
				}
				const chunk = applyRinnaReplacements(
					normalizeSpeechChunk(currentChunk),
					character,
				);
				if (chunk) yield chunk;
				currentChunk = char;
				pendingSentenceEnd = false;
			} else {
				currentChunk += char;
			}

			if (/\p{Ps}/u.test(char)) {
				isInsideParens = true;
			} else if (/\p{Pe}/u.test(char)) {
				isInsideParens = false;
			} else if (SENTENCE_DELIMITERS.includes(char) && !isInsideParens) {
				pendingSentenceEnd = true;
			}
		}
	}

	if (currentChunk) {
		const chunk = applyRinnaReplacements(
			normalizeSpeechChunk(currentChunk),
			character,
		);
		if (chunk) yield chunk;
	}
}
