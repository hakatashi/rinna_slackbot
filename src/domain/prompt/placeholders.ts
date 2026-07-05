const WEEKDAY_KANJI = '月火水木金土日';

/** date.getDay() is Sunday=0..Saturday=6; Python's weekday() is Monday=0..Sunday=6. */
function weekdayKanji(date: Date): string {
	const pythonWeekday = (date.getDay() + 6) % 7;
	return WEEKDAY_KANJI[pythonWeekday] as string;
}

/** Mirrors rinna/utils.py get_hour_str verbatim, including that noon (12)
 * is reported as "午前12" rather than "午後0" or "正午". */
function hourStr(hour: number): string {
	if (hour <= 12) return `午前${hour}`;
	return `午後${hour - 12}`;
}

export function substituteUserPlaceholders(
	text: string,
	user1: string | null,
	user2: string | null,
): string {
	return text
		.replaceAll('{user1}', user1 ?? '博多市')
		.replaceAll('{user2}', user2 ?? 'ひでお');
}

export function substituteDatePlaceholders(
	text: string,
	date: Date,
	weather = 'くもり',
): string {
	return text
		.replaceAll('[MONTH]', String(date.getMonth() + 1))
		.replaceAll('[DATE]', String(date.getDate()))
		.replaceAll('[WEEKDAY]', weekdayKanji(date))
		.replaceAll('[HOUR]', hourStr(date.getHours()))
		.replaceAll('[MINUTE]', String(date.getMinutes()))
		.replaceAll('[WEATHER]', weather);
}
