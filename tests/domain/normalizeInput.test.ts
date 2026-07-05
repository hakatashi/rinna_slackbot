import {describe, expect, it} from 'vitest';
import {normalizeText} from '../../src/domain/prompt/normalizeInput.js';

describe('normalizeText', () => {
	it('strips persona mentions', () => {
		expect(normalizeText('@りんな こんにちは')).toBe('こんにちは');
	});

	it('collapses brackets and newlines to a space', () => {
		expect(normalizeText('こんにちは(元気?)\nさようなら')).toBe(
			'こんにちは 元気? さようなら',
		);
	});

	it('strips slack tag syntax like <@U123>', () => {
		expect(normalizeText('<@U123> やあ')).toBe('やあ');
	});

	it('katakana-izes a persona name at the start of an utterance', () => {
		expect(normalizeText('うな、おはよう')).toBe('ウナ、おはよう');
	});

	it('katakana-izes a persona name at the end of an utterance', () => {
		expect(normalizeText('呼んだのはうな')).toBe('呼んだのはウナ');
	});

	it('katakana-izes a persona name before a particle', () => {
		expect(normalizeText('うなが来た')).toBe('ウナが来た');
	});

	it('does not katakana-ize a persona name in the middle of an unrelated word', () => {
		expect(normalizeText('やまうなぎ')).toBe('やまうなぎ');
	});

	it('normalizes the compound bot display names to katakana before the per-name pass', () => {
		expect(normalizeText('今言うなが言った')).toBe('ウナが言った');
	});
});
