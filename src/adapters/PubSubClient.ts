import {type Message, PubSub} from '@google-cloud/pubsub';
import type {IncomingMessage, MessageSource} from '../ports/MessageSource.js';
import type {Publisher} from '../ports/Publisher.js';

export interface PubSubClientOptions {
	readonly projectId: string;
	readonly subscriptionId: string;
}

/** Mirrors worker.py's SubscriberClient/PublisherClient usage: pulls from
 * the fixed `rinna-signal` subscription, and publishes replies to whatever
 * topic id the caller specifies (used for both the shared `hakatabot`
 * topic and rinna-ping's ephemeral per-request pong topic). */
export class PubSubClient implements MessageSource, Publisher {
	private readonly pubsub: PubSub;
	private readonly subscriptionId: string;

	constructor(options: PubSubClientOptions) {
		this.pubsub = new PubSub({projectId: options.projectId});
		this.subscriptionId = options.subscriptionId;
	}

	subscribe(handler: (message: IncomingMessage) => void | Promise<void>): void {
		const subscription = this.pubsub.subscription(this.subscriptionId);
		subscription.on('message', (message: Message) => {
			let payload: unknown;
			try {
				payload = JSON.parse(message.data.toString('utf8'));
			} catch {
				message.nack();
				return;
			}
			void handler({
				payload,
				ack: () => message.ack(),
			});
		});
	}

	async publish(topicId: string, payload: unknown): Promise<void> {
		const topic = this.pubsub.topic(topicId);
		await topic.publishMessage({data: Buffer.from(JSON.stringify(payload))});
	}
}
