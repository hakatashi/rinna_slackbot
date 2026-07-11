import sharp from 'sharp';
import type {ImageDownloader} from '../ports/ImageDownloader.js';

/** Caps the resized image at this many pixels per side (fit: inside, so the
 * actual width*height stays comfortably under llama-server's mmproj
 * image_max_pixels=4194304 for this model regardless of aspect ratio).
 * Oversized/exotic-format Slack uploads (large photos, CMYK JPEGs, animated
 * GIFs, ...) are the main cause of mtmd's "failed to process image" 500s. */
const MAX_IMAGE_DIMENSION = 2048;
const JPEG_QUALITY = 85;

/** Slack's Web API has no RPC for fetching file bytes; url_private is a
 * plain authenticated GET (Authorization: Bearer <token>). The response is
 * re-encoded to a size- and format-normalized JPEG so llama.cpp's mtmd image
 * decoder — which has narrower format/size support than real-world Slack
 * uploads — doesn't choke on it. */
export class SlackImageDownloader implements ImageDownloader {
	constructor(private readonly token: string) {}

	async downloadBase64(url: string): Promise<string> {
		const response = await fetch(url, {
			headers: {Authorization: `Bearer ${this.token}`},
		});
		if (!response.ok) {
			throw new Error(
				`Slack file download returned ${response.status}: ${url}`,
			);
		}
		const buffer = Buffer.from(await response.arrayBuffer());

		try {
			const resized = await sharp(buffer)
				.rotate()
				.resize({
					width: MAX_IMAGE_DIMENSION,
					height: MAX_IMAGE_DIMENSION,
					fit: 'inside',
					withoutEnlargement: true,
				})
				.jpeg({quality: JPEG_QUALITY})
				.toBuffer();
			return resized.toString('base64');
		} catch (error) {
			throw new Error(
				`Failed to normalize downloaded image (${url}): ${(error as Error).message}`,
			);
		}
	}
}
