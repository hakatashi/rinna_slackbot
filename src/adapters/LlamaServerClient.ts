import type {
	GenerateInput,
	GenerationConfig,
	LlmClient,
} from '../ports/LlmClient.js';

export interface LlamaServerClientOptions {
	readonly baseUrl: string;
	readonly modelName: string;
	readonly modelFile: string;
}

const SAMPLING_PARAMS = {
	seed: -1,
	temperature: 0.6,
	top_p: 0.85,
	top_k: 30,
	repeat_penalty: 1.2,
};

/** Builds the /completion `prompt` field: a plain token array for the
 * text-only path, or a {prompt_string, multimodal_data} object when images
 * are attached (llama-server's multimodal prompt shape). */
function buildPromptField(
	input: GenerateInput,
):
	| readonly number[]
	| {prompt_string: string; multimodal_data: readonly string[]} {
	if ('tokenIds' in input) return input.tokenIds;
	return {prompt_string: input.promptText, multimodal_data: input.images};
}

async function* readSseLines(
	body: ReadableStream<Uint8Array>,
): AsyncGenerator<string, void, undefined> {
	const reader = body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	try {
		for (;;) {
			const {done, value} = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, {stream: true});

			let newlineIdx = buffer.indexOf('\n');
			while (newlineIdx !== -1) {
				const rawLine = buffer.slice(0, newlineIdx);
				buffer = buffer.slice(newlineIdx + 1);
				const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
				if (line.length > 0) yield line;
				newlineIdx = buffer.indexOf('\n');
			}
		}
	} finally {
		reader.releaseLock();
	}
}

/** Mirrors rinna/transformer_models.py's llama-server HTTP client
 * (get_token_ids/generate_text/stream_text). */
export class LlamaServerClient implements LlmClient {
	constructor(private readonly options: LlamaServerClientOptions) {}

	describe(): GenerationConfig {
		return {
			modelProvider: 'llama-server',
			modelName: `${this.options.modelName}/${this.options.modelFile}`,
		};
	}

	async tokenize(text: string): Promise<readonly number[]> {
		const response = await fetch(`${this.options.baseUrl}/tokenize`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({content: text, add_special: false}),
		});
		if (!response.ok) {
			throw new Error(
				`llama-server /tokenize returned ${response.status}: ${await response.text()}`,
			);
		}
		const data = (await response.json()) as {tokens: number[]};
		return data.tokens;
	}

	async generate(
		input: GenerateInput,
	): Promise<{output: string; config: GenerationConfig}> {
		const response = await fetch(`${this.options.baseUrl}/completion`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({
				prompt: buildPromptField(input),
				n_predict: 200,
				stop: ['」'],
				...SAMPLING_PARAMS,
			}),
		});
		if (!response.ok) {
			throw new Error(
				`llama-server /completion returned ${response.status}: ${await response.text()}`,
			);
		}
		const data = (await response.json()) as {content: string};
		if (data.content.length === 0) {
			throw new Error('output_text is empty');
		}
		return {output: data.content, config: this.describe()};
	}

	async *streamGenerate(
		input: GenerateInput,
	): AsyncGenerator<string, void, undefined> {
		const response = await fetch(`${this.options.baseUrl}/completion`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({
				prompt: buildPromptField(input),
				n_predict: 200,
				stream: true,
				...SAMPLING_PARAMS,
			}),
		});
		if (!response.ok || response.body === null) {
			throw new Error(
				`llama-server /completion returned ${response.status}: ${await response.text()}`,
			);
		}

		let bracketDepth = 0;

		for await (const line of readSseLines(response.body)) {
			if (!line.startsWith('data: ')) continue;
			const data = JSON.parse(line.slice(6)) as {
				content?: string;
				stop?: boolean;
			};
			const piece = data.content ?? '';

			let stopIdx: number | null = null;
			const chars = Array.from(piece);
			for (let i = 0; i < chars.length; i++) {
				const char = chars[i] as string;
				if (char === '「') {
					bracketDepth += 1;
				} else if (char === '」') {
					if (bracketDepth === 0) {
						stopIdx = i;
						break;
					}
					bracketDepth -= 1;
				}
			}

			if (stopIdx !== null) {
				if (stopIdx > 0) yield chars.slice(0, stopIdx).join('');
				return;
			}

			if (piece) yield piece;

			if (data.stop === true) break;
		}
	}
}
