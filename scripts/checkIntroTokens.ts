import {loadPersonaData} from '../src/config/loadPersonaData.js';

const MAX_PROMPT_TOKENS = 11500;
const MAX_HISTORY_TOKENS = 2000;
const INTRO_TOKEN_LIMIT = MAX_PROMPT_TOKENS - MAX_HISTORY_TOKENS;

const DATA_DIR = process.env.DATA_DIR ?? 'data';
const LLAMA_SERVER_HOST = process.env.LLAMA_SERVER_HOST ?? '127.0.0.1';
const LLAMA_SERVER_PORT = process.env.LLAMA_SERVER_PORT ?? '8080';

interface TokenCount {
	tokens: number;
	exact: boolean;
}

/** Mirrors data/intro.py's _count_tokens: uses a live llama-server's
 * /tokenize endpoint when reachable, otherwise falls back to a
 * chars-times-1.3 estimate for Japanese text. */
async function countTokens(text: string, baseUrl: string): Promise<TokenCount> {
	try {
		const response = await fetch(`${baseUrl}/tokenize`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({content: text, add_special: false}),
			signal: AbortSignal.timeout(5000),
		});
		if (response.ok) {
			const data = (await response.json()) as {tokens: number[]};
			return {tokens: data.tokens.length, exact: true};
		}
	} catch {
		// llama-server not reachable; fall back to the estimate below.
	}
	return {tokens: Math.round(text.length * 1.3), exact: false};
}

/**
 * Read-only successor to the token-length check at the bottom of the old
 * data/intro.py: for each persona's intro/inquiryIntro/meaningIntro in
 * data/personas.yaml, reports char/token counts against the same budget
 * (MAX_PROMPT_TOKENS - MAX_HISTORY_TOKENS) used by domain/prompt/buildPrompt.
 * Does not write anything back to data/personas.yaml.
 */
async function main(): Promise<void> {
	const baseUrl = `http://${LLAMA_SERVER_HOST}:${LLAMA_SERVER_PORT}`;
	const {personaData} = await loadPersonaData(DATA_DIR);

	console.log(
		`=== Intro token lengths (limit: ${INTRO_TOKEN_LIMIT} tokens) ===`,
	);

	for (const [persona, data] of Object.entries(personaData)) {
		const fields: readonly (readonly [string, string | undefined])[] = [
			['intro', data.intro],
			['inquiryIntro', data.inquiryIntro],
			['meaningIntro', data.meaningIntro],
		];

		for (const [field, text] of fields) {
			if (text === undefined) continue;

			const trimmed = text.trim();
			const {tokens, exact} = await countTokens(trimmed, baseUrl);
			const label = exact ? '' : ' (estimated)';
			const flag = tokens <= INTRO_TOKEN_LIMIT ? '' : '  *** OVER LIMIT ***';
			console.log(
				`  ${persona}_${field}: ${trimmed.length} chars, ${tokens} tokens${label}${flag}`,
			);
		}
	}

	console.log(
		`  (approx. ${Math.round(INTRO_TOKEN_LIMIT / 1.3)} chars max for Japanese text)`,
	);
}

main().catch((error: unknown) => {
	console.error(error);
	process.exit(1);
});
