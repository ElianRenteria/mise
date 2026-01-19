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

export type TranscriptMessage = {
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
};

export type CookingSession = {
	id: string;
	user: string;
	status: 'in_progress' | 'completed' | 'abandoned';
	current_phase?: 'greeting' | 'ingredient_gathering' | 'recipe_selection' | 'cooking' | 'completed';
	ingredients?: unknown[];
	selected_recipe_id?: number;
	current_step?: number;
	recipe_name?: string;
	recipe_data?: unknown;
	transcript?: TranscriptMessage[];
	modifications?: string;
	rating?: number;
	completed?: string;
	created: string;
	updated: string;
};

export type UserPreferences = {
	id: string;
	user: string;
	dietary_restrictions: string[];
	disliked_ingredients: string[];
	favorite_cuisines: string[];
	notes: string;
	created: string;
	updated: string;
};
