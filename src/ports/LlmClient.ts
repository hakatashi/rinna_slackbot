export interface GenerationConfig {
	readonly modelProvider: string;
	readonly modelName: string;
}

/** Either a pre-tokenized text-only prompt, or a raw prompt string paired
 * with base64-encoded images (llama-server's multimodal /completion path,
 * which requires an untokenized prompt_string). */
export type GenerateInput =
	| {readonly tokenIds: readonly number[]}
	| {readonly promptText: string; readonly images: readonly string[]};

export interface LlmClient {
	/** Static provider/model identity, for logging generations that don't go through generate(). */
	describe(): GenerationConfig;
	tokenize(text: string): Promise<readonly number[]>;
	/** Non-streaming generation, stopping at the outer speech's closing 」. Used by the meaning flow. */
	generate(
		input: GenerateInput,
	): Promise<{output: string; config: GenerationConfig}>;
	/** Streaming generation. Yields raw text pieces and stops once the outer
	 * speech's closing 」 is detected (tracking 「/」 nesting depth so a quoted
	 * word inside the speech doesn't end generation early). */
	streamGenerate(input: GenerateInput): AsyncIterable<string>;
}
