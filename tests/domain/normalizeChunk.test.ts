import {describe, expect, it} from 'vitest';
import {
	joinChunksToSpeech,
	normalizeSpeechChunk,
} from '../../src/domain/speech/normalizeChunk.js';

describe('normalizeSpeechChunk', () => {
	it('strips a single trailing 。', () => {
		expect(normalizeSpeechChunk('おはよう。')).toBe('おはよう');
	});

	it('keeps a run of two or more trailing 。', () => {
		expect(normalizeSpeechChunk('えっと。。')).toBe('えっと。。');
	});

	it('leaves chunks without a trailing 。 untouched', () => {
		expect(normalizeSpeechChunk('元気？')).toBe('元気？');
	});
});

describe('joinChunksToSpeech', () => {
	it('inserts 。 between chunks that do not already end with a delimiter', () => {
		expect(joinChunksToSpeech(['おはよう', 'げんき'])).toBe('おはよう。げんき');
	});

	it('inserts a space between chunks when the first already ends with a delimiter', () => {
		expect(joinChunksToSpeech(['元気？', 'うん！'])).toBe('元気？ うん！');
	});

	it('does not append anything after the last chunk', () => {
		expect(joinChunksToSpeech(['ひとつだけ'])).toBe('ひとつだけ');
	});
});
