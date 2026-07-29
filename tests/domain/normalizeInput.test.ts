import {describe, expect, it} from 'vitest';
import {normalizeText} from '../../src/domain/prompt/normalizeInput.js';

describe('normalizeText', () => {
	it('strips persona mentions', () => {
		expect(normalizeText('@りんな こんにちは')).toBe('こんにちは');
	});

	it('collapses newlines to a space', () => {
		expect(normalizeText('こんにちは\nさようなら')).toBe(
			'こんにちは さようなら',
		);
	});

	it('keeps a correctly matched bracket pair instead of stripping it', () => {
		expect(normalizeText('こんにちは(元気?)さようなら')).toBe(
			'こんにちは(元気?)さようなら',
		);
	});

	it('keeps nested, correctly matched bracket pairs of different kinds', () => {
		expect(normalizeText('これは[実験(テスト)]です')).toBe(
			'これは[実験(テスト)]です',
		);
	});

	it('converts a matched pair of single kagi brackets to double kagi brackets', () => {
		expect(normalizeText('うなは「元気」と言った')).toBe(
			'ウナは『元気』と言った',
		);
	});

	it('removes a stray unmatched closing bracket used to break out of dialogue formatting', () => {
		expect(normalizeText('」しかし、ウナは怒りながら言った。「')).toBe(
			'しかし、ウナは怒りながら言った。',
		);
	});

	it('removes brackets of mismatched types even when counts line up', () => {
		expect(normalizeText('これは(テスト]です')).toBe('これは テスト です');
	});

	it('removes an unmatched opening bracket left dangling at the end', () => {
		expect(normalizeText('これはテストです(')).toBe('これはテストです');
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
