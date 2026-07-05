import type {AppDependencies} from '../../src/app/deps.js';
import {PERSONA_IDS, type PersonaId} from '../../src/domain/personas.js';
import type {PersonaPromptData} from '../../src/domain/prompt/buildPrompt.js';
import type {
	ChatPoster,
	PostMessageParams,
} from '../../src/ports/ChatPoster.js';
import type {Clock} from '../../src/ports/Clock.js';
import type {GenerationConfig, LlmClient} from '../../src/ports/LlmClient.js';
import type {ModerationResult, Moderator} from '../../src/ports/Moderator.js';
import type {Publisher} from '../../src/ports/Publisher.js';
import type {RandomSource} from '../../src/ports/Random.js';
import type {ResponseLog, ResponseRecord} from '../../src/ports/ResponseLog.js';
import type {Thermometer} from '../../src/ports/Thermometer.js';

export class FakeLlmClient implements LlmClient {
	streamPieces: string[] = [];
	generateOutput = 'ダミー」';

	describe(): GenerationConfig {
		return {modelProvider: 'fake', modelName: 'fake-model'};
	}

	async tokenize(text: string): Promise<readonly number[]> {
		return Array.from(text, (_, i) => i);
	}

	async generate(
		_tokenIds: readonly number[],
	): Promise<{output: string; config: GenerationConfig}> {
		return {output: this.generateOutput, config: this.describe()};
	}

	async *streamGenerate(
		_tokenIds: readonly number[],
	): AsyncGenerator<string, void, undefined> {
		for (const piece of this.streamPieces) {
			yield piece;
		}
	}
}

export class FakeChatPoster implements ChatPoster {
	posts: PostMessageParams[] = [];

	async post(params: PostMessageParams): Promise<Record<string, unknown>> {
		this.posts.push(params);
		return {ts: String(this.posts.length), channel: params.channel};
	}
}

export class FakeModerator implements Moderator {
	censoredTexts = new Set<string>();

	async moderate(text: string): Promise<ModerationResult> {
		return {
			censored: this.censoredTexts.has(text),
			details: {googleLanguageService: null, azureContentModerator: null},
		};
	}
}

export class FakeResponseLog implements ResponseLog {
	records: ResponseRecord[] = [];

	async log(record: ResponseRecord): Promise<void> {
		this.records.push(record);
	}
}

export class FakePublisher implements Publisher {
	published: {topicId: string; payload: unknown}[] = [];

	async publish(topicId: string, payload: unknown): Promise<void> {
		this.published.push({topicId, payload});
	}
}

export class FakeThermometer implements Thermometer {
	temp: string | null = '42.0';

	async readGpuTemp(): Promise<string | null> {
		return this.temp;
	}
}

export function fixedClock(date: Date): Clock {
	return {now: () => date};
}

export function fixedRandom<T>(pick: T): RandomSource {
	return {choice: (() => pick) as RandomSource['choice']};
}

export function fakePersonaData(): Record<PersonaId, PersonaPromptData> {
	const data = {} as Record<PersonaId, PersonaPromptData>;
	for (const id of PERSONA_IDS) {
		data[id] = {intro: `${id}のイントロ`};
	}
	const una = data['うな'];
	data['うな'] = {...una, meaningIntro: 'うなquestion-intro'};
	return data;
}

export interface FakeDeps {
	llm: FakeLlmClient;
	chatPoster: FakeChatPoster;
	moderator: FakeModerator;
	responseLog: FakeResponseLog;
	publisher: FakePublisher;
	thermometer: FakeThermometer;
	deps: AppDependencies;
}

export function createFakeDeps(
	now: Date = new Date(2026, 0, 5, 12, 0),
): FakeDeps {
	const llm = new FakeLlmClient();
	const chatPoster = new FakeChatPoster();
	const moderator = new FakeModerator();
	const responseLog = new FakeResponseLog();
	const publisher = new FakePublisher();
	const thermometer = new FakeThermometer();

	const deps: AppDependencies = {
		llm,
		chatPoster,
		moderator,
		responseLog,
		publisher,
		thermometer,
		clock: fixedClock(now),
		random: fixedRandom<PersonaId>('りんな'),
		personaData: fakePersonaData(),
		usernameMapping: {U1: '博多市', U2: 'ひでお'},
		sandboxChannel: 'C_TEST',
		mode: 'CPU',
	};

	return {
		llm,
		chatPoster,
		moderator,
		responseLog,
		publisher,
		thermometer,
		deps,
	};
}
