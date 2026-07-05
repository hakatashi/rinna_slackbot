import {WebClient} from '@slack/web-api';
import type {ChatPoster, PostMessageParams} from '../ports/ChatPoster.js';

export class SlackChatPoster implements ChatPoster {
	private readonly client: WebClient;

	constructor(token: string) {
		this.client = new WebClient(token);
	}

	async post(params: PostMessageParams): Promise<Record<string, unknown>> {
		const threadOptions =
			params.threadTs !== undefined
				? {
						thread_ts: params.threadTs,
						reply_broadcast: params.replyBroadcast ?? true,
					}
				: {};

		const response = await this.client.chat.postMessage({
			text: params.text,
			channel: params.channel,
			icon_url: params.iconUrl,
			username: params.username,
			...threadOptions,
		});

		return response as unknown as Record<string, unknown>;
	}
}
