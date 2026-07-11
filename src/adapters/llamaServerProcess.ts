import {type ChildProcess, spawn} from 'node:child_process';
import {existsSync} from 'node:fs';

export interface LlamaServerProcessOptions {
	readonly binaryPath: string;
	readonly modelPath: string;
	readonly mmprojPath: string;
	readonly host: string;
	readonly port: number;
	readonly contextSize: number;
	readonly gpuMode: boolean;
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => {
		setTimeout(resolve, ms);
	});
}

/** Mirrors rinna/transformer_models.py's llama-server subprocess management:
 * spawns the binary in its own process group, polls /health until ready
 * (or throws after a timeout), and on stop() sends SIGTERM to the whole
 * group before escalating to SIGKILL if it doesn't exit in time. */
export class LlamaServerProcess {
	private child: ChildProcess | undefined;

	constructor(private readonly options: LlamaServerProcessOptions) {}

	get baseUrl(): string {
		return `http://${this.options.host}:${this.options.port}`;
	}

	async start(): Promise<void> {
		if (!existsSync(this.options.binaryPath)) {
			throw new Error(`llama-server not found: ${this.options.binaryPath}`);
		}

		this.child = spawn(
			this.options.binaryPath,
			[
				'-m',
				this.options.modelPath,
				'--mmproj',
				this.options.mmprojPath,
				'--host',
				this.options.host,
				'--port',
				String(this.options.port),
				'-c',
				String(this.options.contextSize),
				'-ngl',
				this.options.gpuMode ? '-1' : '0',
			],
			{detached: true, stdio: ['ignore', 'pipe', 'pipe']},
		);

		await this.waitForHealth();
	}

	private async waitForHealth(timeoutMs = 360_000): Promise<void> {
		await sleep(3000);
		const start = Date.now();
		while (Date.now() - start < timeoutMs) {
			try {
				const response = await fetch(`${this.baseUrl}/health`);
				if (response.ok) return;
			} catch {
				// Server not accepting connections yet; keep polling.
			}
			await sleep(2000);
		}
		throw new Error('llama-server failed to start within timeout');
	}

	async stop(): Promise<void> {
		const child = this.child;
		if (child === undefined || child.pid === undefined) return;

		const pid = child.pid;
		process.kill(-pid, 'SIGTERM');

		await new Promise<void>((resolve) => {
			const timer = setTimeout(() => {
				try {
					process.kill(-pid, 'SIGKILL');
				} catch {
					// Already gone.
				}
				resolve();
			}, 10_000);
			child.once('exit', () => {
				clearTimeout(timer);
				resolve();
			});
		});
	}
}
