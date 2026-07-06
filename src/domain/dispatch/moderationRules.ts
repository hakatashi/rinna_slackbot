export const MODERATION_ALLOWLIST: readonly string[] = ['えた', 'クリ'];

export interface AzureModerationTerm {
	term: string;
}

/** Mirrors rinna/utils.py has_offensive_term: censor unless every matched
 * term is on the allowlist. */
export function hasOffensiveTerm(
	terms: readonly AzureModerationTerm[] | null,
): boolean {
	if (terms === null) return false;
	return terms.some((term) => !MODERATION_ALLOWLIST.includes(term.term));
}
