export interface ResponseRecord {
	readonly createdAt: Date;
	readonly character: string;
	readonly inputMessages: readonly unknown[];
	readonly inputText: string;
	readonly inputDialog: string;
	readonly inputTokenLength: number;
	readonly output: string;
	readonly outputSpeech: string;
	readonly config: Record<string, unknown>;
	readonly message: Record<string, unknown>;
	readonly moderations: Record<string, unknown>;
	readonly threadTs?: string;
}

export interface ResponseLog {
	log(record: ResponseRecord): Promise<void>;
}
