const MENTION_PATTERNS = [/@りんな/g, /@うな/g, /@うか/g, /@うの/g, /@たたも/g];

/** Open→close pairs for the bracket characters this app cares about
 * (a practical subset of Unicode's \p{Ps}/\p{Pe} categories, not the full
 * set — anything outside this table is left untouched). */
const BRACKET_PAIRS: ReadonlyMap<string, string> = new Map([
	['(', ')'],
	['（', '）'],
	['[', ']'],
	['［', '］'],
	['{', '}'],
	['｛', '｝'],
	['「', '」'],
	['『', '』'],
	['【', '】'],
	['〔', '〕'],
	['〈', '〉'],
	['《', '》'],
	['〘', '〙'],
	['〚', '〛'],
]);

const CLOSING_TO_OPENING: ReadonlyMap<string, string> = new Map(
	[...BRACKET_PAIRS.entries()].map(([open, close]) => [close, open]),
);

/**
 * Prompt-injection guard: a stray, unmatched bracket (e.g. a lone `」`
 * injected to break out of the `${user}「${text}」` dialogue wrapping used
 * downstream in formatMessage.ts) gets removed, same as before. A properly
 * matched pair is now left in place instead of being stripped wholesale,
 * since the model handles nested brackets correctly. Single kagi brackets
 * that survive matching are converted to double kagi, since a bare `「」`
 * pair inside a user's own message text is indistinguishable, once wrapped,
 * from the `「`/`」` that delimits a persona's own speech.
 */
function normalizeBrackets(text: string): string {
	const chars = [...text];
	const isValidPair = new Array<boolean>(chars.length).fill(false);
	const stack: Array<{char: string; index: number}> = [];

	for (const [index, char] of chars.entries()) {
		if (BRACKET_PAIRS.has(char)) {
			stack.push({char, index});
		} else if (CLOSING_TO_OPENING.has(char)) {
			const top = stack.at(-1);
			if (top !== undefined && BRACKET_PAIRS.get(top.char) === char) {
				stack.pop();
				isValidPair[top.index] = true;
				isValidPair[index] = true;
			}
		}
	}

	return chars
		.map((char, index) => {
			if (!BRACKET_PAIRS.has(char) && !CLOSING_TO_OPENING.has(char)) {
				return char;
			}
			if (!isValidPair[index]) return ' ';
			if (char === '「') return '『';
			if (char === '」') return '』';
			return char;
		})
		.join('');
}

const KATAKANA_REPLACEMENTS: ReadonlyArray<readonly [RegExp, string]> = [
	[/今言うな/g, 'ウナ'],
	[/皿洗うか/g, 'ウカ'],
	[/皿洗うの/g, 'ウノ'],
	[/三脚たたも/g, 'タタモ'],
];

const NAME_BOUNDARY_REPLACEMENTS: ReadonlyArray<readonly [string, string]> = [
	['うな', 'ウナ'],
	['うか', 'ウカ'],
	['うの', 'ウノ'],
	['たたも', 'タタモ'],
];

/** Originally mirrored rinna/utils.py normalize_text (strip mentions, strip
 * every bracket unconditionally), now diverging on bracket handling — see
 * normalizeBrackets above — then disambiguates persona names from ordinary
 * words by katakana-izing them only at utterance boundaries or before a
 * particle. */
export function normalizeText(text: string): string {
	let result = text;

	for (const pattern of MENTION_PATTERNS) {
		result = result.replace(pattern, '');
	}

	result = result.replace(/[\r\n]+/g, ' ');
	result = normalizeBrackets(result);
	result = result.replace(/ {2,}/g, ' ');
	result = result.replace(/<.+?>/g, '');
	result = result.replace(/ワシ/g, '儂');

	for (const [pattern, replacement] of KATAKANA_REPLACEMENTS) {
		result = result.replace(pattern, replacement);
	}

	for (const [name, newName] of NAME_BOUNDARY_REPLACEMENTS) {
		result = result.replace(new RegExp(`^${name}`), newName);
		result = result.replace(new RegExp(`${name}$`), newName);
		result = result.replace(
			new RegExp(`${name}([はがのを])`, 'g'),
			`${newName}$1`,
		);
	}

	return result.trim();
}
