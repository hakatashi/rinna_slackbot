import {personaMeta} from '../../domain/personas.js';
import type {AppDependencies} from '../deps.js';

/** Mirrors worker.py's rinna-temperature handling: reports うな's "body
 * temperature" (really the GPU's) via rocm-smi. No-op if the reading is
 * unavailable. */
export async function temperatureHandler(deps: AppDependencies): Promise<void> {
	const temp = await deps.thermometer.readGpuTemp();
	if (temp === null) return;

	const meta = personaMeta['うな'];
	await deps.chatPoster.post({
		text: `今のうなの体温は${temp}度だにゃ～！`,
		channel: deps.sandboxChannel,
		iconUrl: meta.slackUserIcon,
		username: meta.slackUserName,
	});
}
