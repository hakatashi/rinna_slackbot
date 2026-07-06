export interface RandomSource {
	choice<T>(items: readonly T[]): T;
}
