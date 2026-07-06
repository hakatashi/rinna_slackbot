import {initializeApp} from 'firebase-admin/app';
import {getFirestore} from 'firebase-admin/firestore';
import {AzureContentModerator} from './adapters/AzureContentModerator.js';
import {FirestoreResponseLog} from './adapters/FirestoreResponseLog.js';
import {GoogleLanguageModerator} from './adapters/GoogleLanguageModerator.js';
import {LlamaServerClient} from './adapters/LlamaServerClient.js';
import {LlamaServerProcess} from './adapters/llamaServerProcess.js';
import {downloadModel} from './adapters/modelDownloader.js';
import {ParallelModerator} from './adapters/ParallelModerator.js';
import {PubSubClient} from './adapters/PubSubClient.js';
import {RocmSmiThermometer} from './adapters/RocmSmiThermometer.js';
import {SlackChatPoster} from './adapters/SlackChatPoster.js';
import type {AppDependencies} from './app/deps.js';
import {createRouter} from './app/router.js';
import type {Env} from './config/env.js';
import {loadPersonaData} from './config/loadPersonaData.js';
import type {IncomingMessage} from './ports/MessageSource.js';
import type {RandomSource} from './ports/Random.js';

export interface ComposedApp {
	readonly deps: AppDependencies;
	readonly route: (message: IncomingMessage) => Promise<void>;
	readonly pubsub: PubSubClient;
	readonly llamaServerProcess: LlamaServerProcess;
}

function systemRandom(): RandomSource {
	return {
		choice: <T>(items: readonly T[]): T => {
			const index = Math.floor(Math.random() * items.length);
			return items[index] as T;
		},
	};
}

/** The single place that knows about concrete adapters: downloads/starts
 * llama-server, wires up Slack/Firestore/Pub/Sub/moderation clients, and
 * assembles the AppDependencies bag + router used by main.ts. */
export async function composeApp(env: Env): Promise<ComposedApp> {
	const modelPath = await downloadModel(
		{repo: env.MODEL_REPO, file: env.MODEL_FILE},
		env.HUGGINGFACE_TOKEN,
	);

	const llamaServerProcess = new LlamaServerProcess({
		binaryPath: env.LLAMA_SERVER_BINARY,
		modelPath,
		host: env.LLAMA_SERVER_HOST,
		port: env.LLAMA_SERVER_PORT,
		contextSize: env.LLAMA_CONTEXT_SIZE,
		gpuMode: env.LLAMA_GPU,
	});
	await llamaServerProcess.start();

	const llm = new LlamaServerClient({
		baseUrl: llamaServerProcess.baseUrl,
		modelName: env.MODEL_REPO,
		modelFile: env.MODEL_FILE,
	});

	const {personaData, usernameMapping} = await loadPersonaData(env.DATA_DIR);

	initializeApp();
	const firestore = getFirestore();

	const chatPoster = new SlackChatPoster(env.SLACK_TOKEN);
	const moderator = new ParallelModerator(
		new GoogleLanguageModerator(),
		new AzureContentModerator({
			endpoint: env.CONTENT_MODERATOR_ENDPOINT,
			subscriptionKey: env.CONTENT_MODERATOR_SUBSCRIPTION_KEY,
		}),
	);
	const responseLog = new FirestoreResponseLog(firestore);
	const pubsub = new PubSubClient({
		projectId: env.PROJECT_ID,
		subscriptionId: env.SUBSCRIPTION_ID,
	});
	const thermometer = new RocmSmiThermometer();

	const deps: AppDependencies = {
		llm,
		chatPoster,
		moderator,
		responseLog,
		publisher: pubsub,
		thermometer,
		clock: {now: () => new Date()},
		random: systemRandom(),
		personaData,
		usernameMapping,
		sandboxChannel: env.SANDBOX_CHANNEL_ID,
		mode: env.LLAMA_GPU ? 'GPU' : 'CPU',
	};

	const route = createRouter(deps);

	return {deps, route, pubsub, llamaServerProcess};
}
