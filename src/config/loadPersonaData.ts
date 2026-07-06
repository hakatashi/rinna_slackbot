import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {parse as parseYaml} from 'yaml';
import {z} from 'zod';
import {PERSONA_IDS, type PersonaId} from '../domain/personas.js';
import type {PersonaPromptData} from '../domain/prompt/buildPrompt.js';

const personaEntrySchema = z.object({
	intro: z.string(),
	inquiryIntro: z.string().optional(),
	meaningIntro: z.string().optional(),
});

const personasFileSchema = z.record(z.string(), personaEntrySchema);
const usernamesFileSchema = z.record(z.string(), z.string());

export interface PersonaDataSet {
	personaData: Record<PersonaId, PersonaPromptData>;
	usernameMapping: Record<string, string>;
}

/** Loads the gitignored data/personas.yaml and data/usernames.yaml (the
 * successors to the old data/intro.py and data/users.py code-as-data
 * generators), validating shape at startup rather than failing deep inside
 * a generation call. */
export async function loadPersonaData(
	dataDir: string,
): Promise<PersonaDataSet> {
	const [personasRaw, usernamesRaw] = await Promise.all([
		readFile(path.join(dataDir, 'personas.yaml'), 'utf8'),
		readFile(path.join(dataDir, 'usernames.yaml'), 'utf8'),
	]);

	const personasParsed = personasFileSchema.parse(parseYaml(personasRaw));
	const usernameMapping = usernamesFileSchema.parse(parseYaml(usernamesRaw));

	const personaData = {} as Record<PersonaId, PersonaPromptData>;
	for (const id of PERSONA_IDS) {
		const entry = personasParsed[id];
		if (entry === undefined) {
			throw new Error(`data/personas.yaml is missing an entry for "${id}"`);
		}
		personaData[id] = {
			intro: entry.intro,
			...(entry.inquiryIntro !== undefined
				? {inquiryIntro: entry.inquiryIntro}
				: {}),
			...(entry.meaningIntro !== undefined
				? {meaningIntro: entry.meaningIntro}
				: {}),
		};
	}

	return {personaData, usernameMapping};
}
