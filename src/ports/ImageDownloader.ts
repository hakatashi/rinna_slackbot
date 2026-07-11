export interface ImageDownloader {
	/** Downloads an authenticated image URL (e.g. Slack's url_private) and
	 * returns its bytes as a base64-encoded string. */
	downloadBase64(url: string): Promise<string>;
}
