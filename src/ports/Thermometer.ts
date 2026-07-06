export interface Thermometer {
	/** Returns the raw matched temperature string (e.g. "45.0"), not a parsed
	 * number, since the original just interpolates the regex match verbatim. */
	readGpuTemp(): Promise<string | null>;
}
