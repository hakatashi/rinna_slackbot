import {createServer, type Server} from 'node:http';
import {afterEach, describe, expect, it} from 'vitest';
import {AzureContentModerator} from '../../src/adapters/AzureContentModerator.js';

async function serveJson(body: unknown) {
	const server: Server = createServer((_req, res) => {
		res.writeHead(200, {'Content-Type': 'application/json'});
		res.end(JSON.stringify(body));
	});
	await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
	const address = server.address();
	if (address === null || typeof address === 'string')
		throw new Error('unexpected address');
	return {server, endpoint: `http://127.0.0.1:${address.port}`};
}

describe('AzureContentModerator', () => {
	let server: Server;

	afterEach(() => {
		server.close();
	});

	it('parses terms from the real (snake_case) response shape', async () => {
		// Confirmed against a live Azure Content Moderator response: the JSON
		// body uses snake_case keys (terms/term), not PascalCase.
		const served = await serveJson({
			terms: [
				{index: 0, original_index: 0, list_id: 'default', term: 'ng-word'},
			],
			original_text: 'x ng-word',
			normalized_text: 'x ng-word',
			tracking_id: 'abc',
			status: {code: 3000, description: 'OK'},
			language: 'jpn',
		});
		server = served.server;

		const moderator = new AzureContentModerator({
			endpoint: served.endpoint,
			subscriptionKey: 'k',
		});
		const {terms, raw} = await moderator.screenText('x ng-word');

		expect(terms).toEqual([{term: 'ng-word'}]);
		expect((raw as {terms?: unknown}).terms).toEqual([
			{index: 0, original_index: 0, list_id: 'default', term: 'ng-word'},
		]);
	});

	it('returns null terms when the response has no terms field (clean text)', async () => {
		const served = await serveJson({
			original_text: 'clean',
			normalized_text: 'clean',
			tracking_id: 'abc',
			status: {code: 3000, description: 'OK'},
			language: 'jpn',
		});
		server = served.server;

		const moderator = new AzureContentModerator({
			endpoint: served.endpoint,
			subscriptionKey: 'k',
		});
		const {terms} = await moderator.screenText('clean');

		expect(terms).toBeNull();
	});
});
