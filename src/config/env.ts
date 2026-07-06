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

	DATA_DIR: z.string().default('data'),
});

export type Env = z.infer<typeof envSchema>;

export function loadEnv(source: NodeJS.ProcessEnv = process.env): Env {
	return envSchema.parse(source);
}
