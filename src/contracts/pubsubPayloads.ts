import {z} from 'zod';

/**
 * Slack message shape as published by the sibling repo
 * (hakatabot-firebase-functions/functions/src/slack.ts, `interface Message`).
 * Only the fields worker.py's rinna-signal flow actually reads are required;
 * everything else is optional since Slack payloads carry many unused fields.
 */
export const humanMessageSchema = z.object({
	text: z.string().nullable().optional(),
	ts: z.string(),
	user: z.string().optional(),
	username: z.string().optional(),
	bot_id: z.string().optional(),
	subtype: z.string().optional(),
	thread_ts: z.string().optional(),
});

export type HumanMessage = z.infer<typeof humanMessageSchema>;

export const rinnaSignalPayloadSchema = z.object({
	type: z.literal('rinna-signal'),
	humanMessages: z.array(humanMessageSchema),
	botMessages: z.array(humanMessageSchema).optional(),
	lastSignal: z.number().optional(),
});

export type RinnaSignalPayload = z.infer<typeof rinnaSignalPayloadSchema>;

export const rinnaMeaningPayloadSchema = z.object({
	type: z.literal('rinna-meaning'),
	word: z.string(),
	ts: z.string().optional(),
});

export type RinnaMeaningPayload = z.infer<typeof rinnaMeaningPayloadSchema>;

export const rinnaPingPayloadSchema = z.object({
	type: z.literal('rinna-ping'),
	topicId: z.string(),
});

export type RinnaPingPayload = z.infer<typeof rinnaPingPayloadSchema>;

export const rinnaTemperaturePayloadSchema = z.object({
	type: z.literal('rinna-temperature'),
	ts: z.string().optional(),
	channel: z.string().optional(),
});

export type RinnaTemperaturePayload = z.infer<
	typeof rinnaTemperaturePayloadSchema
>;

export const rinnaPayloadSchema = z.discriminatedUnion('type', [
	rinnaSignalPayloadSchema,
	rinnaMeaningPayloadSchema,
	rinnaPingPayloadSchema,
	rinnaTemperaturePayloadSchema,
]);

export type RinnaPayload = z.infer<typeof rinnaPayloadSchema>;
