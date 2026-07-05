import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import type {Thermometer} from '../ports/Thermometer.js';

const execFileAsync = promisify(execFile);

const TEMP_PATTERN = /Temperature \(Sensor edge\) \(C\): ([\d.]+)/;

/** Mirrors worker.py's rinna-temperature handling: shells out to
 * `rocm-smi --showtemp` and extracts the sensor-edge reading. Returns null
 * (rather than throwing) only when the command succeeds but the expected
 * line isn't found in its output; command failures propagate to the
 * caller. */
export class RocmSmiThermometer implements Thermometer {
	async readGpuTemp(): Promise<string | null> {
		const {stdout} = await execFileAsync('rocm-smi', ['--showtemp'], {
			timeout: 10_000,
		});
		const match = TEMP_PATTERN.exec(stdout);
		return match?.[1] ?? null;
	}
}
