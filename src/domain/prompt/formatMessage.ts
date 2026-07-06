export interface DialogueEntry {
	text: string;
	user: string;
}

export function formatMessage(message: DialogueEntry): string {
	if (message.user === 'context') return `(${message.text})`;
	return `${message.user}「${message.text}」`;
}
