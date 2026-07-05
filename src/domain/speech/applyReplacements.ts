import type {PersonaId} from '../personas.js';

/** Mirrors rinna/generation.py _apply_rinna_replacements. */
export function applyRinnaReplacements(
	text: string,
	character: PersonaId,
): string {
	let result = text;
	result = result.replaceAll('[UNK]', '');
	result = result.replaceAll('『', '「');
	result = result.replaceAll('』', '」');
	result = result.replaceAll('ウナ', 'うな');
	result = result.replaceAll('ウカ', 'うか');
	result = result.replaceAll('ウノ', 'うの');
	result = result.replaceAll('タタモ', 'たたも');
	if (character === 'たたも') {
		result = result.replaceAll('ワシ', '儂');
	}
	return result;
}
