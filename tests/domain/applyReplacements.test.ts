import {describe, expect, it} from 'vitest';
import {applyRinnaReplacements} from '../../src/domain/speech/applyReplacements.js';

describe('applyRinnaReplacements', () => {
	it('drops [UNK] tokens', () => {
		expect(applyRinnaReplacements('あ[UNK]い', 'りんな')).toBe('あい');
	});

	it('converts double brackets to single', () => {
		expect(applyRinnaReplacements('『こんにちは』', 'りんな')).toBe(
			'「こんにちは」',
		);
	});

	it('lowercases persona katakana names back to hiragana', () => {
		expect(applyRinnaReplacements('ウナとウカとウノとタタモ', 'りんな')).toBe(
			'うなとうかとうのとたたも',
		);
	});

	it('converts ワシ to 儂 only for たたも', () => {
		expect(applyRinnaReplacements('ワシじゃ', 'たたも')).toBe('儂じゃ');
		expect(applyRinnaReplacements('ワシじゃ', 'りんな')).toBe('ワシじゃ');
	});
});
