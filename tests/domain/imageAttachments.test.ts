import {describe, expect, it} from 'vitest';
import type {HumanMessage} from '../../src/contracts/pubsubPayloads.js';
import {
	selectImageFiles,
	selectRecentImageUrls,
} from '../../src/domain/prompt/imageAttachments.js';

function msg(
	text: string,
	ts: string,
	files?: HumanMessage['files'],
): HumanMessage {
	return {text, ts, files};
}

describe('selectImageFiles', () => {
	it('keeps only image/* mimetypes', () => {
		const files = [
			{url_private: 'a', mimetype: 'image/png'},
			{url_private: 'b', mimetype: 'application/pdf'},
			{url_private: 'c', mimetype: 'image/jpeg'},
		];
		expect(selectImageFiles(files)).toEqual([
			{url_private: 'a', mimetype: 'image/png'},
			{url_private: 'c', mimetype: 'image/jpeg'},
		]);
	});

	it('returns an empty array when files is undefined', () => {
		expect(selectImageFiles(undefined)).toEqual([]);
	});
});

describe('selectRecentImageUrls', () => {
	it('returns an empty array when nothing has image attachments', () => {
		const messages = [msg('hello', '1')];
		expect(selectRecentImageUrls(messages, 3)).toEqual([]);
	});

	it('collects image urls from messages that carry them', () => {
		const messages = [
			msg('no image', '1'),
			msg('with image', '2', [{url_private: 'img1', mimetype: 'image/png'}]),
		];
		expect(selectRecentImageUrls(messages, 3)).toEqual(['img1']);
	});

	it('ignores non-image attachments', () => {
		const messages = [
			msg('a doc', '1', [{url_private: 'doc', mimetype: 'application/pdf'}]),
		];
		expect(selectRecentImageUrls(messages, 3)).toEqual([]);
	});

	it('caps at maxImages, keeping the newest ones in chronological order', () => {
		const messages = [
			msg('1', '10', [{url_private: 'img1', mimetype: 'image/png'}]),
			msg('2', '20', [{url_private: 'img2', mimetype: 'image/png'}]),
			msg('3', '30', [{url_private: 'img3', mimetype: 'image/png'}]),
			msg('4', '40', [{url_private: 'img4', mimetype: 'image/png'}]),
		];
		// img1 (ts=10) is dropped as the oldest; survivors are returned oldest
		// first among themselves, matching the order they'll be attached in.
		expect(selectRecentImageUrls(messages, 3)).toEqual([
			'img2',
			'img3',
			'img4',
		]);
	});

	it('collects multiple images from a single message', () => {
		const messages = [
			msg('multi', '1', [
				{url_private: 'a', mimetype: 'image/png'},
				{url_private: 'b', mimetype: 'image/jpeg'},
			]),
		];
		expect(selectRecentImageUrls(messages, 3)).toEqual(['a', 'b']);
	});
});
