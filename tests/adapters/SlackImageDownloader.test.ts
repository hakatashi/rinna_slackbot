import {createServer, type Server} from 'node:http';
import sharp from 'sharp';
import {afterEach, describe, expect, it} from 'vitest';
import {SlackImageDownloader} from '../../src/adapters/SlackImageDownloader.js';

function makePng(width: number, height: number): Promise<Buffer> {
	return sharp({
		create: {
			width,
			height,
			channels: 3,
			background: {r: 200, g: 100, b: 50},
		},
	})
		.png()
		.toBuffer();
}

async function serveOnce(
	handler: (headers: Record<string, string | string[] | undefined>) => {
		status: number;
		body: Buffer;
	},
) {
	const server: Server = createServer((req, res) => {
		const {status, body} = handler(req.headers);
		res.writeHead(status);
		res.end(body);
	});
	await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
	const address = server.address();
	if (address === null || typeof address === 'string')
		throw new Error('unexpected address');
	return {server, baseUrl: `http://127.0.0.1:${address.port}`};
}

describe('SlackImageDownloader', () => {
	let server: Server;

	afterEach(() => {
		server.close();
	});

	it('sends the token as a Bearer Authorization header and returns a decodable base64 image', async () => {
		let capturedAuth: string | undefined;
		const png = await makePng(100, 80);
		const served = await serveOnce((headers) => {
			capturedAuth = headers.authorization as string | undefined;
			return {status: 200, body: png};
		});
		server = served.server;

		const downloader = new SlackImageDownloader('xoxb-test-token');
		const result = await downloader.downloadBase64(`${served.baseUrl}/img.png`);

		expect(capturedAuth).toBe('Bearer xoxb-test-token');
		const metadata = await sharp(Buffer.from(result, 'base64')).metadata();
		expect(metadata.format).toBe('jpeg');
		expect(metadata.width).toBe(100);
		expect(metadata.height).toBe(80);
	});

	it('downscales images larger than the max dimension without upscaling smaller ones', async () => {
		const large = await makePng(3000, 1500);
		const served = await serveOnce(() => ({status: 200, body: large}));
		server = served.server;

		const downloader = new SlackImageDownloader('xoxb-test-token');
		const result = await downloader.downloadBase64(`${served.baseUrl}/big.png`);

		const metadata = await sharp(Buffer.from(result, 'base64')).metadata();
		expect(metadata.width).toBeLessThanOrEqual(2048);
		expect(metadata.height).toBeLessThanOrEqual(2048);
		// aspect ratio preserved (2:1)
		expect(metadata.width).toBe((metadata.height ?? 0) * 2);
	});

	it('throws when the download fails', async () => {
		const served = await serveOnce(() => ({
			status: 404,
			body: Buffer.from('not found'),
		}));
		server = served.server;

		const downloader = new SlackImageDownloader('xoxb-test-token');
		await expect(
			downloader.downloadBase64(`${served.baseUrl}/missing.png`),
		).rejects.toThrow('404');
	});

	it('throws a clear error when the downloaded bytes are not a valid image', async () => {
		const served = await serveOnce(() => ({
			status: 200,
			body: Buffer.from('not an image'),
		}));
		server = served.server;

		const downloader = new SlackImageDownloader('xoxb-test-token');
		await expect(
			downloader.downloadBase64(`${served.baseUrl}/broken.png`),
		).rejects.toThrow('Failed to normalize downloaded image');
	});
});
