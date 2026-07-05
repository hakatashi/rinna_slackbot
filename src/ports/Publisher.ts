export interface Publisher {
	publish(topicId: string, payload: unknown): Promise<void>;
}
