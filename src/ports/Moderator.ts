export interface ModerationResult {
	readonly censored: boolean;
	readonly details: {
		readonly googleLanguageService: unknown;
		readonly azureContentModerator: unknown;
	};
}

export interface Moderator {
	moderate(text: string): Promise<ModerationResult>;
}
