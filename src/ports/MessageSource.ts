export interface IncomingMessage {
	readonly payload: unknown;
	ack(): void;
}

export interface MessageSource {
	subscribe(handler: (message: IncomingMessage) => void | Promise<void>): void;
}
