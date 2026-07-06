import {downloadFileToCacheDir} from '@huggingface/hub';

export interface ModelLocation {
	readonly repo: string;
	readonly file: string;
}

/** Mirrors rinna/transformer_models.py's hf_hub_download call: downloads the
 * given file into the local HF cache if not already present, returning its
 * local path. */
export async function downloadModel(
	{repo, file}: ModelLocation,
	hfToken: string | undefined,
): Promise<string> {
	return downloadFileToCacheDir({
		repo: {type: 'model', name: repo},
		path: file,
		accessToken: hfToken,
	});
}
