const MENTION_PATTERNS = [/@りんな/g, /@うな/g, /@うか/g, /@うの/g, /@たたも/g];

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

/** Mirrors rinna/utils.py normalize_text: strips mentions/brackets, then
 * disambiguates persona names from ordinary words by katakana-izing them
 * only at utterance boundaries or before a particle. */
export function normalizeText(text: string): string {
	let result = text;

	for (const pattern of MENTION_PATTERNS) {
		result = result.replace(pattern, '');
	}

	result = result.replace(/[\p{Ps}\p{Pe}\r\n]+/gu, ' ');
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
