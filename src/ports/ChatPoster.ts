export interface PostMessageParams {
	readonly text: string;
	readonly channel: string;
	readonly iconUrl: string;
	readonly username: string;
	readonly threadTs?: string;
	readonly replyBroadcast?: boolean;
}

export interface ChatPoster {
	/** Returns the raw Slack API response payload, logged verbatim to Firestore. */
	post(params: PostMessageParams): Promise<Record<string, unknown>>;
}
