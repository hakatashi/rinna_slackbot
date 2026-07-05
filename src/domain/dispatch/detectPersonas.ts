import type {RandomSource} from '../../ports/Random.js';
import type {PersonaId} from '../personas.js';

/** Mirrors worker.py's independent per-persona substring checks
 * (`if 'りんな' in trigger_text: ...`, then うな/うか/うの/たたも), which can
 * all fire for a single trigger message. Order matters: it is the order in
 * which replies get appended to history and posted. */
export function detectTriggeredPersonas(triggerText: string): PersonaId[] {
	const triggered: PersonaId[] = [];
	if (triggerText.includes('りんな')) triggered.push('りんな');
	if (triggerText.includes('うな')) triggered.push('うな');
	if (triggerText.includes('うか')) triggered.push('うか');
	if (triggerText.includes('うの')) triggered.push('うの');
	if (triggerText.includes('たたも')) triggered.push('たたも');
	return triggered;
}

/** Mirrors worker.py's fallback when no persona name matched: '皿洗' narrows
 * to the two dishwashing sisters, otherwise a uniform pick that notably
 * excludes たたも. */
export function pickFallbackPersona(
	triggerText: string,
	random: RandomSource,
): PersonaId {
	if (triggerText.includes('皿洗')) {
		return random.choice(['うか', 'うの']);
	}
	return random.choice(['りんな', 'うな', 'うか', 'うの']);
}
