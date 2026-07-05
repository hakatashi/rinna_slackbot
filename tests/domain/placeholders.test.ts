import {describe, expect, it} from 'vitest';
import {
	substituteDatePlaceholders,
	substituteUserPlaceholders,
} from '../../src/domain/prompt/placeholders.js';

describe('substituteUserPlaceholders', () => {
	it('substitutes both user placeholders', () => {
		expect(substituteUserPlaceholders('{user1}と{user2}', 'A', 'B')).toBe(
			'AとB',
		);
	});

	it('falls back to defaults when null', () => {
		expect(substituteUserPlaceholders('{user1}と{user2}', null, null)).toBe(
			'博多市とひでお',
		);
	});
});

describe('substituteDatePlaceholders', () => {
	it('formats month/date/weekday/hour/minute/weather (AM, including noon quirk)', () => {
		// 2026-01-05 is a Monday; getHours()=12 is reported as "午前12" verbatim
		// (mirrors get_hour_str's `hour <= 12` boundary from the original Python).
		const date = new Date(2026, 0, 5, 12, 7);
		expect(
			substituteDatePlaceholders(
				'[MONTH]/[DATE] [WEEKDAY] [HOUR]:[MINUTE] [WEATHER]',
				date,
			),
		).toBe('1/5 月 午前12:7 くもり');
	});

	it('formats PM hours', () => {
		const date = new Date(2026, 0, 5, 13, 30);
		expect(substituteDatePlaceholders('[HOUR]', date)).toBe('午後1');
	});

	it('maps Sunday correctly', () => {
		const date = new Date(2026, 0, 4, 0, 0); // 2026-01-04 is a Sunday
		expect(substituteDatePlaceholders('[WEEKDAY]', date)).toBe('日');
	});
});
