import {describe, expect, it} from 'vitest';
import {
	detectTriggeredPersonas,
	pickFallbackPersona,
} from '../../src/domain/dispatch/detectPersonas.js';
import type {RandomSource} from '../../src/ports/Random.js';

function fixedChoice<T>(pick: T): RandomSource {
	return {choice: (() => pick) as RandomSource['choice']};
}

describe('detectTriggeredPersonas', () => {
	it('returns an empty list when no persona name is mentioned', () => {
		expect(detectTriggeredPersonas('こんにちは')).toEqual([]);
	});

	it('detects a single persona', () => {
		expect(detectTriggeredPersonas('りんな、おはよう')).toEqual(['りんな']);
	});

	it('detects multiple personas in fixed order regardless of mention order', () => {
		expect(
			detectTriggeredPersonas('たたも、うのと一緒にりんなも呼んで'),
		).toEqual(['りんな', 'うの', 'たたも']);
	});

	it('うな substring also matches inside 今言うな-derived text', () => {
		// worker.py checks the raw trigger text with plain substring matching;
		// 'うな' being a substring of other words is a known, preserved quirk.
		expect(detectTriggeredPersonas('うなぎが食べたい')).toEqual(['うな']);
	});
});

describe('pickFallbackPersona', () => {
	it('narrows to うか/うの when the trigger mentions 皿洗', () => {
		const random = fixedChoice('うか' as const);
		expect(pickFallbackPersona('皿洗いをして', random)).toBe('うか');
	});

	it('otherwise excludes たたも from the random pool', () => {
		const seenPools: unknown[] = [];
		const random: RandomSource = {
			choice: (items) => {
				seenPools.push(items);
				return items[0] as never;
			},
		};
		pickFallbackPersona('特に名前は出てない', random);
		expect(seenPools).toEqual([['りんな', 'うな', 'うか', 'うの']]);
	});
});
