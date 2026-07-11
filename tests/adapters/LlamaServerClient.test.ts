import {createServer, type Server} from 'node:http';
import {afterEach, describe, expect, it} from 'vitest';
import {LlamaServerClient} from '../../src/adapters/LlamaServerClient.js';

function sseBody(events: readonly Record<string, unknown>[]): string {
	return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
}

async function serveOnce(
	handler: (path: string, body: string) => {status: number; body: string},
) {
	const server: Server = createServer((req, res) => {
		const chunks: Buffer[] = [];
		req.on('data', (chunk: Buffer) => chunks.push(chunk));
		req.on('end', () => {
			const body = Buffer.concat(chunks).toString('utf8');
			const {status, body: responseBody} = handler(req.url ?? '', body);
			res.writeHead(status, {'Content-Type': 'text/event-stream'});
			res.end(responseBody);
		});
	});
	await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
	const address = server.address();
	if (address === null || typeof address === 'string')
		throw new Error('unexpected address');
	return {server, baseUrl: `http://127.0.0.1:${address.port}`};
}

describe('LlamaServerClient.streamGenerate', () => {
	let server: Server;

	afterEach(() => {
		server.close();
	});

	it('yields pieces and stops at data.stop=true when no closing bracket appears', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: sseBody([{content: 'おはよ'}, {content: 'う', stop: true}]),
		}));
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		const chunks: string[] = [];
		for await (const piece of client.streamGenerate({tokenIds: [1, 2, 3]})) {
			chunks.push(piece);
		}
		expect(chunks.join('')).toBe('おはよう');
	});

	it('stops exactly at the outer closing 」 and discards anything after it', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: sseBody([
				{content: 'おはよう」ignored-tail', stop: false},
				{content: 'more', stop: true},
			]),
		}));
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		const chunks: string[] = [];
		for await (const piece of client.streamGenerate({tokenIds: [1]})) {
			chunks.push(piece);
		}
		expect(chunks.join('')).toBe('おはよう');
	});

	it('does not stop on a 」 that closes a nested 「quote」 inside the speech', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: sseBody([
				{content: 'それは「入れ子」だよ', stop: false},
				{content: '」', stop: true},
			]),
		}));
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		const chunks: string[] = [];
		for await (const piece of client.streamGenerate({tokenIds: [1]})) {
			chunks.push(piece);
		}
		// The nested 「入れ子」 pair doesn't trigger the stop; only the final
		// unmatched 」 (bracket depth back to 0) does, and it yields nothing
		// after it since stopIdx === 0 for that lone-character piece.
		expect(chunks.join('')).toBe('それは「入れ子」だよ');
	});

	it('sends the tokenized prompt and sampling params as the request body', async () => {
		let capturedBody = '';
		const served = await serveOnce((_path, body) => {
			capturedBody = body;
			return {status: 200, body: sseBody([{content: 'ok', stop: true}])};
		});
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		for await (const _piece of client.streamGenerate({tokenIds: [7, 8, 9]})) {
			// drain
		}

		const parsed = JSON.parse(capturedBody) as {
			prompt: number[];
			stream: boolean;
			temperature: number;
		};
		expect(parsed.prompt).toEqual([7, 8, 9]);
		expect(parsed.stream).toBe(true);
		expect(parsed.temperature).toBe(0.6);
	});

	it('sends a prompt_string/multimodal_data object when images are attached', async () => {
		let capturedBody = '';
		const served = await serveOnce((_path, body) => {
			capturedBody = body;
			return {status: 200, body: sseBody([{content: 'ok', stop: true}])};
		});
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		for await (const _piece of client.streamGenerate({
			promptText: '質問「これは何？」<__media__>',
			images: ['base64data'],
		})) {
			// drain
		}

		const parsed = JSON.parse(capturedBody) as {
			prompt: {prompt_string: string; multimodal_data: string[]};
		};
		expect(parsed.prompt).toEqual({
			prompt_string: '質問「これは何？」<__media__>',
			multimodal_data: ['base64data'],
		});
	});
});

describe('LlamaServerClient.tokenize', () => {
	afterEach(() => {
		server.close();
	});
	let server: Server;

	it('returns the flat token id array from /tokenize', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: JSON.stringify({tokens: [10, 20, 30]}),
		}));
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		await expect(client.tokenize('こんにちは')).resolves.toEqual([10, 20, 30]);
	});
});

describe('LlamaServerClient.generate', () => {
	afterEach(() => {
		server.close();
	});
	let server: Server;

	it('returns content and config on success', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: JSON.stringify({content: 'おはよう」'}),
		}));
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'my-model',
			modelFile: 'f.gguf',
		});
		const result = await client.generate({tokenIds: [1, 2]});
		expect(result.output).toBe('おはよう」');
		expect(result.config).toEqual({
			modelProvider: 'llama-server',
			modelName: 'my-model/f.gguf',
		});
	});

	it('throws when the server returns an empty completion', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: JSON.stringify({content: ''}),
		}));
		server = served.server;

		const client = new LlamaServerClient({
			baseUrl: served.baseUrl,
			modelName: 'm',
			modelFile: 'f',
		});
		await expect(client.generate({tokenIds: [1]})).rejects.toThrow(
			'output_text is empty',
		);
	});
});
