import 'dotenv/config';
import {composeApp} from './composeRoot.js';
import {loadEnv} from './config/env.js';

async function main(): Promise<void> {
	const env = loadEnv();
	const {route, pubsub, llamaServerProcess} = await composeApp(env);

	pubsub.subscribe(route);

	let shuttingDown = false;
	const shutdown = async (): Promise<void> => {
		if (shuttingDown) return;
		shuttingDown = true;
		console.info('Shutting down...');
		await llamaServerProcess.stop();
		process.exit(0);
	};

	process.on('SIGINT', () => {
		void shutdown();
	});
	process.on('SIGTERM', () => {
		void shutdown();
	});

	console.info(
		`Listening for messages on subscription ${env.SUBSCRIPTION_ID}...`,
	);
}

main().catch((error: unknown) => {
	console.error(error);
	process.exit(1);
});
