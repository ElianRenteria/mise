import PocketBase from 'pocketbase';
import { PUBLIC_POCKETBASE_URL } from '$env/static/public';

export const pb = new PocketBase(PUBLIC_POCKETBASE_URL);
pb.autoCancellation(false);

export type User = {
	id: string;
	email: string;
	verified: boolean;
	created: string;
	updated: string;
};
