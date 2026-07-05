import {Mutex} from 'async-mutex';

/** Serializes generation (rinna-signal, rinna-meaning) so only one LLM
 * request runs at a time, mirroring worker.py's global `mutex`. */
export function createGenerationMutex(): Mutex {
	return new Mutex();
}
