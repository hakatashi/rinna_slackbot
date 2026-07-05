import {describe, expect, it} from 'vitest';
import {hasOffensiveTerm} from '../../src/domain/dispatch/moderationRules.js';

describe('hasOffensiveTerm', () => {
	it('returns false when terms is null', () => {
		expect(hasOffensiveTerm(null)).toBe(false);
	});

	it('returns false when every matched term is allowlisted', () => {
		expect(hasOffensiveTerm([{term: 'えた'}, {term: 'クリ'}])).toBe(false);
	});

	it('returns true when at least one term is not allowlisted', () => {
		expect(hasOffensiveTerm([{term: 'えた'}, {term: 'ng-word'}])).toBe(true);
	});

	it('returns false for an empty list', () => {
		expect(hasOffensiveTerm([])).toBe(false);
	});
});
