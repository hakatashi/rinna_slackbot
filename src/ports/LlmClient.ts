export interface GenerationConfig {
	readonly modelProvider: string;
	readonly modelName: string;
}

export interface LlmClient {
	/** Static provider/model identity, for logging generations that don't go through generate(). */
	describe(): GenerationConfig;
	tokenize(text: string): Promise<readonly number[]>;
	/** Non-streaming generation, stopping at the outer speech's closing 」. Used by the meaning flow. */
	generate(
		tokenIds: readonly number[],
	): Promise<{output: string; config: GenerationConfig}>;
	/** Streaming generation. Yields raw text pieces and stops once the outer
	 * speech's closing 」 is detected (tracking 「/」 nesting depth so a quoted
	 * word inside the speech doesn't end generation early). */
	streamGenerate(tokenIds: readonly number[]): AsyncIterable<string>;
}
