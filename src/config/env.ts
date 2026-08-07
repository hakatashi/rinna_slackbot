import {homedir} from 'node:os';
import path from 'node:path';
import {z} from 'zod';

const envSchema = z.object({
	SLACK_TOKEN: z.string().min(1),
	CONTENT_MODERATOR_ENDPOINT: z.string().min(1),
	CONTENT_MODERATOR_SUBSCRIPTION_KEY: z.string().min(1),
	HUGGINGFACE_TOKEN: z.string().optional(),

	PROJECT_ID: z.string().default('hakatabot-firebase-functions'),
	SUBSCRIPTION_ID: z.string().default('rinna-signal'),
	SANDBOX_CHANNEL_ID: z.string().default('C7AAX50QY'),

	LLAMA_SERVER_BINARY: z
		.string()
		.default(
			path.join(homedir(), 'Documents/GitHub/llama.cpp/build/bin/llama-server'),
		),
	LLAMA_SERVER_HOST: z.string().default('127.0.0.1'),
	LLAMA_SERVER_PORT: z.coerce.number().int().default(8080),
	LLAMA_CONTEXT_SIZE: z.coerce.number().int().default(12288),
	LLAMA_GPU: z
		.string()
		.default('false')
		.transform((value) => value === 'true' || value === '1'),

	MODEL_REPO: z.string().default('mradermacher/Qwen3.5-35B-A3B-Base-GGUF'),
	MODEL_FILE: z.string().default('Qwen3.5-35B-A3B-Base.Q6_K.gguf'),
	MMPROJ_FILE: z.string().default('Qwen3.5-35B-A3B-Base.mmproj-Q8_0.gguf'),
	/** Local .gguf path, used instead of downloading MODEL_FILE from
	 * MODEL_REPO — for models quantized here that aren't published to the Hub. */
	MODEL_PATH: z.string().optional(),
	/** The MODEL_PATH counterpart of MMPROJ_FILE. Leaving both this and
	 * MMPROJ_FILE empty configures no mmproj at all, i.e. a text-only model. */
	MMPROJ_PATH: z.string().optional(),
	MAX_RECENT_IMAGES: z.coerce.number().int().default(1),

	DATA_DIR: z.string().default('data'),

	IGNORED_USERS: z
		.string()
		.default('')
		.transform((value) =>
			value
				.split(',')
				.map((u) => u.trim())
				.filter((u) => u !== ''),
		),
});

export type Env = z.infer<typeof envSchema>;

export function loadEnv(source: NodeJS.ProcessEnv = process.env): Env {
	return envSchema.parse(source);
}
