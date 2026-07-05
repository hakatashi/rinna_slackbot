import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRouter} from '../../src/app/router.js';
import type {RinnaSignalPayload} from '../../src/contracts/pubsubPayloads.js';
import {createFakeDeps} from './fakeDeps.js';

const NOW = new Date(2026, 0, 5, 12, 0);

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

function signal(text: string): RinnaSignalPayload {
	return {
		type: 'rinna-signal',
		humanMessages: [{text, user: 'U1', ts: String(NOW.getTime() / 1000)}],
	};
}

describe('createRouter', () => {
	it('acks a rinna-signal message after the handler succeeds', async () => {
		const {llm, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];
		const route = createRouter(deps);
		const ack = vi.fn();

		const promise = route({payload: signal('りんな、こんにちは'), ack});
		await vi.runAllTimersAsync();
		await promise;

		expect(ack).toHaveBeenCalledTimes(1);
	});

	it('swallows a thrown error from a rinna-signal handler without acking', async () => {
		const {llm, deps} = createFakeDeps(NOW);
		llm.tokenize = () => Promise.reject(new Error('boom'));
		const route = createRouter(deps);
		const ack = vi.fn();
		const consoleError = vi
			.spyOn(console, 'error')
			.mockImplementation(() => {});

		await expect(
			route({payload: signal('りんな、こんにちは'), ack}),
		).resolves.toBeUndefined();

		expect(ack).not.toHaveBeenCalled();
		expect(consoleError).toHaveBeenCalled();
		consoleError.mockRestore();
	});

	it('acks a rinna-meaning message after success', async () => {
		const {llm, deps} = createFakeDeps(NOW);
		llm.generateOutput = 'こういう意味だよ」';
		const route = createRouter(deps);
		const ack = vi.fn();

		const promise = route({
			payload: {type: 'rinna-meaning', word: 'テスト'},
			ack,
		});
		await vi.runAllTimersAsync();
		await promise;

		expect(ack).toHaveBeenCalledTimes(1);
	});

	it('propagates an error from rinna-ping without acking (no try/catch, matching the original)', async () => {
		const {deps: baseDeps} = createFakeDeps(NOW);
		const nowMs = Date.now();
		const deps = {...baseDeps, clock: {now: () => new Date(nowMs)}};
		deps.publisher.publish = () => Promise.reject(new Error('publish failed'));
		const route = createRouter(deps);
		const ack = vi.fn();

		await expect(
			route({
				payload: {type: 'rinna-ping', topicId: `rinna-ping-${nowMs}`},
				ack,
			}),
		).rejects.toThrow('publish failed');

		expect(ack).not.toHaveBeenCalled();
	});

	it('acks rinna-ping on success and ignores stale pings without publishing', async () => {
		const {publisher, deps: baseDeps} = createFakeDeps(NOW);
		const nowMs = Date.now();
		const deps = {...baseDeps, clock: {now: () => new Date(nowMs)}};
		const route = createRouter(deps);
		const ack = vi.fn();

		const staleTopicId = `rinna-ping-${nowMs - 30_000}`;
		await route({payload: {type: 'rinna-ping', topicId: staleTopicId}, ack});

		expect(ack).toHaveBeenCalledTimes(1);
		expect(publisher.published).toHaveLength(0);
	});

	it('acks rinna-temperature even when the handler throws', async () => {
		const {thermometer, deps} = createFakeDeps(NOW);
		thermometer.readGpuTemp = () =>
			Promise.reject(new Error('rocm-smi missing'));
		const route = createRouter(deps);
		const ack = vi.fn();
		const consoleError = vi
			.spyOn(console, 'error')
			.mockImplementation(() => {});

		await route({payload: {type: 'rinna-temperature'}, ack});

		expect(ack).toHaveBeenCalledTimes(1);
		consoleError.mockRestore();
	});

	it('serializes concurrent rinna-signal messages through the generation mutex', async () => {
		const {llm, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];

		let busy = false;
		let overlapDetected = false;
		const originalTokenize = llm.tokenize.bind(llm);
		llm.tokenize = async (text: string) => {
			if (busy) overlapDetected = true;
			busy = true;
			await new Promise((resolve) => setTimeout(resolve, 5));
			busy = false;
			return originalTokenize(text);
		};

		const route = createRouter(deps);
		const ack1 = vi.fn();
		const ack2 = vi.fn();

		const p1 = route({payload: signal('りんな、hi'), ack: ack1});
		const p2 = route({payload: signal('うな、hi'), ack: ack2});
		await vi.runAllTimersAsync();
		await Promise.all([p1, p2]);

		expect(overlapDetected).toBe(false);
		expect(ack1).toHaveBeenCalledTimes(1);
		expect(ack2).toHaveBeenCalledTimes(1);
	});
});
