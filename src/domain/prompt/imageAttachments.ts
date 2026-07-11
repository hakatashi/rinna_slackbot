import type {HumanMessage, SlackFile} from '../../contracts/pubsubPayloads.js';

/** llama.cpp's mtmd_default_marker(); prompt_string markers are substituted
 * positionally with multimodal_data entries, so this must match the
 * llama-server build exactly. */
export const IMAGE_MEDIA_MARKER = '<__media__>';

export function selectImageFiles(
	files: readonly SlackFile[] | undefined,
): readonly SlackFile[] {
	if (files === undefined) return [];
	return files.filter((file) => file.mimetype.startsWith('image/'));
}

/**
 * Scans all messages for image attachments and keeps only the most recent
 * maxImages across the whole window, returned in chronological order
 * (oldest kept image first).
 *
 * Note: normalizeText (used when formatting dialogue text in buildPrompt)
 * strips any `<...>` tag from message text, so image markers can't be
 * embedded into a message's own text — buildPrompt's extraSuffix parameter
 * is used instead to attach IMAGE_MEDIA_MARKER.repeat(urls.length) once, at
 * the end of the prompt.
 */
export function selectRecentImageUrls(
	messages: readonly HumanMessage[],
	maxImages: number,
): readonly string[] {
	interface Entry {
		readonly url: string;
		readonly ts: number;
	}

	const entries: Entry[] = [];
	for (const message of messages) {
		for (const file of selectImageFiles(message.files)) {
			entries.push({url: file.url_private, ts: Number.parseFloat(message.ts)});
		}
	}

	return entries
		.slice()
		.sort((a, b) => b.ts - a.ts)
		.slice(0, maxImages)
		.sort((a, b) => a.ts - b.ts)
		.map((entry) => entry.url);
}
