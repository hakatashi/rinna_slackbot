export const RINNA_BOT_ID = 'BEHP604TV';

export type PersonaId = 'りんな' | 'うな' | 'うか' | 'うの' | 'たたも';

export const PERSONA_IDS: readonly PersonaId[] = [
	'りんな',
	'うな',
	'うか',
	'うの',
	'たたも',
];

export interface PersonaMeta {
	readonly id: PersonaId;
	readonly nameInText: string;
	readonly slackUserName: string;
	readonly slackUserIcon: string;
}

export const personaMeta: Record<PersonaId, PersonaMeta> = {
	りんな: {
		id: 'りんな',
		nameInText: 'りんな',
		slackUserName: 'りんな',
		slackUserIcon:
			'https://huggingface.co/rinna/japanese-gpt-1b/resolve/main/rinna.png',
	},
	うな: {
		id: 'うな',
		nameInText: 'ウナ',
		slackUserName: '今言うな',
		slackUserIcon:
			'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/una_icon.png',
	},
	うか: {
		id: 'うか',
		nameInText: 'ウカ',
		slackUserName: '皿洗うか',
		slackUserIcon:
			'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/uka_icon_edit.png',
	},
	うの: {
		id: 'うの',
		nameInText: 'ウノ',
		slackUserName: '皿洗うの',
		slackUserIcon:
			'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/uno_icon.png',
	},
	たたも: {
		id: 'たたも',
		nameInText: 'タタモ',
		slackUserName: '三脚たたも',
		slackUserIcon:
			'https://hakata-public.s3.ap-northeast-1.amazonaws.com/slackbot/user03.png',
	},
};

export function findPersonaByBotUsername(
	username: string,
): PersonaMeta | undefined {
	return Object.values(personaMeta).find(
		(persona) => persona.slackUserName === username,
	);
}
