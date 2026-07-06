import {describe, expect, it} from 'vitest';
import type {HumanMessage} from '../../src/contracts/pubsubPayloads.js';
import {trimHistory} from '../../src/domain/dispatch/trimHistory.js';

function msg(text: string | null, ts: string): HumanMessage {
	return {text, ts};
}

describe('trimHistory', () => {
	it('keeps full history and strips nothing when no directive is present', () => {
		const messages = [msg('hello', '1'), msg('world', '2')];
		const result = trimHistory(messages);
		expect(result.messages.map((m) => m.text)).toEqual(['hello', 'world']);
		expect(result.triggerText).toBe('world');
	});

	it('truncates history to the most recent /clear message', () => {
		const messages = [
			msg('a', '1'),
			msg('/clear b', '2'),
			msg('c', '3'),
			msg('d /clear', '4'),
			msg('e', '5'),
		];
		const result = trimHistory(messages);
		// last_clear_index is at ts=4 ('d /clear'); window starts there.
		expect(result.messages.map((m) => m.text)).toEqual(['d', 'e']);
		expect(result.triggerText).toBe('e');
	});

	it('/no_clear on the trigger message disables truncation even if /clear appears earlier', () => {
		const messages = [
			msg('/clear a', '1'),
			msg('b', '2'),
			msg('c /no_clear', '3'),
		];
		const result = trimHistory(messages);
		expect(result.messages.map((m) => m.text)).toEqual(['a', 'b', 'c']);
		expect(result.triggerText).toBe('c');
	});

	it('strips the directive tokens from every message text, not just the trigger', () => {
		const messages = [msg('/clear りんな呼んで', '1')];
		const result = trimHistory(messages);
		expect(result.messages[0]?.text).toBe('りんな呼んで');
		expect(result.triggerText).toBe('りんな呼んで');
	});

	it('passes through messages with null text unchanged', () => {
		const messages = [msg(null, '1'), msg('hi', '2')];
		const result = trimHistory(messages);
		expect(result.messages[0]?.text).toBeNull();
	});
});
