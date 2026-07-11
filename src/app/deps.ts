import type {PersonaId} from '../domain/personas.js';
import type {PersonaPromptData} from '../domain/prompt/buildPrompt.js';
import type {ChatPoster} from '../ports/ChatPoster.js';
import type {Clock} from '../ports/Clock.js';
import type {ImageDownloader} from '../ports/ImageDownloader.js';
import type {LlmClient} from '../ports/LlmClient.js';
import type {Moderator} from '../ports/Moderator.js';
import type {Publisher} from '../ports/Publisher.js';
import type {RandomSource} from '../ports/Random.js';
import type {ResponseLog} from '../ports/ResponseLog.js';
import type {Thermometer} from '../ports/Thermometer.js';

/** The full set of ports a handler may need, wired up once in composeRoot. */
export interface AppDependencies {
	readonly llm: LlmClient;
	readonly chatPoster: ChatPoster;
	readonly imageDownloader: ImageDownloader;
	readonly moderator: Moderator;
	readonly responseLog: ResponseLog;
	readonly publisher: Publisher;
	readonly thermometer: Thermometer;
	readonly clock: Clock;
	readonly random: RandomSource;
	readonly personaData: Record<PersonaId, PersonaPromptData>;
	readonly usernameMapping: Record<string, string>;
	readonly sandboxChannel: string;
	/** Echoed back verbatim in rinna-pong replies; mirrors sys.argv[1] ('CPU'/'GPU') from worker.py. */
	readonly mode: string;
	/** Cap on how many recent Slack image attachments to send per generation. */
	readonly maxRecentImages: number;
}
