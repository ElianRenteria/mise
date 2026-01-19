<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb, getAvatarUrl, type UserPreferences } from '$lib/pocketbase';
	import { onMount } from 'svelte';

	// User info
	let name = $state('');
	let email = $state('');
	let avatarUrl: string | null = $state(null);

	// Preferences
	let dietaryRestrictions: string[] = $state([]);
	let dislikedIngredients: string[] = $state([]);
	let favoriteCuisines: string[] = $state([]);
	let notes = $state('');
	let preferencesId: string | null = $state(null);

	// UI state
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let success = $state('');


	onMount(async () => {
		if (!pb.authStore.isValid || !pb.authStore.record) {
			goto(`${base}/`);
			return;
		}

		// Load user info
		const user = pb.authStore.record;
		name = user.name || '';
		email = user.email || '';

		// Load avatar - fallback to DiceBear if none stored
		if (user.avatar) {
			avatarUrl = getAvatarUrl(user.id, user.avatar);
		} else if (user.name || user.email) {
			const seed = user.name || user.email.split('@')[0];
			avatarUrl = `https://api.dicebear.com/9.x/dylan/svg?seed=${encodeURIComponent(seed)}`;
		}

		// Load preferences
		await loadPreferences();
		loading = false;
	});

	async function loadPreferences() {
		const userId = pb.authStore.record?.id;
		if (!userId) return;

		try {
			const records = await pb.collection('user_preferences').getList<UserPreferences>(1, 1, {
				filter: `user = "${userId}"`
			});

			if (records.items.length > 0) {
				const prefs = records.items[0];
				preferencesId = prefs.id;
				dietaryRestrictions = prefs.dietary_restrictions || [];
				dislikedIngredients = prefs.disliked_ingredients || [];
				favoriteCuisines = prefs.favorite_cuisines || [];
				notes = prefs.notes || '';
			}
		} catch (err) {
			console.error('Failed to load preferences:', err);
		}
	}

	async function saveProfile() {
		saving = true;
		error = '';
		success = '';

		const userId = pb.authStore.record?.id;
		if (!userId) {
			error = 'not logged in';
			saving = false;
			return;
		}

		try {
			// Update user name
			await pb.collection('users').update(userId, {
				name: name.trim()
			});

			// Update or create preferences
			const prefsData = {
				user: userId,
				dietary_restrictions: dietaryRestrictions,
				disliked_ingredients: dislikedIngredients,
				favorite_cuisines: favoriteCuisines,
				notes: notes.trim()
			};

			if (preferencesId) {
				await pb.collection('user_preferences').update(preferencesId, prefsData);
			} else {
				const created = await pb.collection('user_preferences').create(prefsData);
				preferencesId = created.id;
			}

			success = 'profile saved successfully!';
			setTimeout(() => success = '', 3000);
		} catch (err: any) {
			console.error('Failed to save profile:', err);
			error = err?.message || 'failed to save profile';
		} finally {
			saving = false;
		}
	}

	function removeItem(list: string[], item: string): string[] {
		return list.filter(i => i !== item);
	}
</script>

<div class="min-h-screen mise-gradient-bg pb-8">
	<!-- Header -->
	<div class="sticky top-0 bg-white/80 backdrop-blur-sm border-b border-surface-200 z-10">
		<div class="max-w-2xl mx-auto px-4 py-4 flex items-center gap-4">
			<button
				onclick={() => goto(`${base}/kitchen`)}
				class="p-2 rounded-full hover:bg-surface-100 transition-colors"
				aria-label="Back to kitchen"
			>
				<svg class="w-6 h-6 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</button>
			<div class="flex items-center gap-3">
				{#if avatarUrl}
					<img
						src={avatarUrl}
						alt="Your avatar"
						class="w-10 h-10 rounded-full object-cover bg-surface-200"
					/>
				{:else}
					<div class="w-10 h-10 rounded-full bg-primary-500 flex items-center justify-center">
						<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
						</svg>
					</div>
				{/if}
				<h1 class="text-xl font-black tracking-tighter text-surface-700 lowercase">
					chef's profile
				</h1>
			</div>
		</div>
	</div>

	<!-- Content -->
	<div class="max-w-2xl mx-auto px-4 py-6">
		{#if loading}
			<div class="space-y-6 animate-pulse">
				<div class="bg-white rounded-2xl p-6 space-y-4">
					<div class="h-6 bg-surface-200 rounded w-1/4"></div>
					<div class="h-12 bg-surface-100 rounded-xl"></div>
					<div class="h-12 bg-surface-100 rounded-xl"></div>
				</div>
			</div>
		{:else}
			<!-- Messages -->
			{#if error}
				<div class="mb-4 bg-error-100 border border-error-500 text-error-700 px-4 py-3 rounded-xl text-sm font-medium tracking-tighter lowercase">
					{error}
				</div>
			{/if}
			{#if success}
				<div class="mb-4 bg-success-100 border border-success-500 text-success-700 px-4 py-3 rounded-xl text-sm font-medium tracking-tighter lowercase">
					{success}
				</div>
			{/if}

			<form onsubmit={(e) => { e.preventDefault(); saveProfile(); }} class="space-y-6">
				<!-- Basic Info Card -->
				<div class="bg-white rounded-2xl p-6 shadow-sm">
					<h2 class="text-lg font-bold tracking-tighter text-surface-700 lowercase mb-4">
						basic info
					</h2>

					<div class="space-y-4">
						<div>
							<label for="name" class="mise-label">name</label>
							<input
								id="name"
								type="text"
								bind:value={name}
								placeholder="your name"
								class="mise-input"
							/>
						</div>

						<div>
							<label for="email" class="mise-label">email</label>
							<input
								id="email"
								type="email"
								value={email}
								disabled
								class="mise-input bg-surface-50 text-surface-500 cursor-not-allowed"
							/>
							<p class="text-xs text-surface-400 mt-1 tracking-tighter">email cannot be changed</p>
						</div>
					</div>
				</div>

				<!-- Cooking Preferences Card -->
				<div class="bg-white rounded-2xl p-6 shadow-sm">
					<h2 class="text-lg font-bold tracking-tighter text-surface-700 lowercase mb-4">
						cooking preferences
					</h2>
					<p class="text-sm text-surface-500 tracking-tighter lowercase mb-4">
						bruno learns these as you cook together. you can remove any that aren't right.
					</p>

					<div class="space-y-6">
						<!-- Dietary Restrictions -->
						<div>
							<label class="mise-label">dietary restrictions</label>
							{#if dietaryRestrictions.length > 0}
								<div class="flex flex-wrap gap-2">
									{#each dietaryRestrictions as item}
										<span class="inline-flex items-center gap-1 px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium tracking-tighter lowercase">
											{item}
											<button
												type="button"
												onclick={() => dietaryRestrictions = removeItem(dietaryRestrictions, item)}
												class="hover:text-primary-900"
												aria-label="Remove {item}"
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
												</svg>
											</button>
										</span>
									{/each}
								</div>
							{:else}
								<p class="text-sm text-surface-400 italic">none yet — tell bruno about any dietary needs while cooking</p>
							{/if}
						</div>

						<!-- Disliked Ingredients -->
						<div>
							<label class="mise-label">disliked ingredients</label>
							{#if dislikedIngredients.length > 0}
								<div class="flex flex-wrap gap-2">
									{#each dislikedIngredients as item}
										<span class="inline-flex items-center gap-1 px-3 py-1 bg-error-100 text-error-700 rounded-full text-sm font-medium tracking-tighter lowercase">
											{item}
											<button
												type="button"
												onclick={() => dislikedIngredients = removeItem(dislikedIngredients, item)}
												class="hover:text-error-900"
												aria-label="Remove {item}"
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
												</svg>
											</button>
										</span>
									{/each}
								</div>
							{:else}
								<p class="text-sm text-surface-400 italic">none yet — mention ingredients you don't like to bruno</p>
							{/if}
						</div>

						<!-- Favorite Cuisines -->
						<div>
							<label class="mise-label">favorite cuisines</label>
							{#if favoriteCuisines.length > 0}
								<div class="flex flex-wrap gap-2">
									{#each favoriteCuisines as item}
										<span class="inline-flex items-center gap-1 px-3 py-1 bg-success-100 text-success-700 rounded-full text-sm font-medium tracking-tighter lowercase">
											{item}
											<button
												type="button"
												onclick={() => favoriteCuisines = removeItem(favoriteCuisines, item)}
												class="hover:text-success-900"
												aria-label="Remove {item}"
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
												</svg>
											</button>
										</span>
									{/each}
								</div>
							{:else}
								<p class="text-sm text-surface-400 italic">none yet — share your favorite cuisines with bruno</p>
							{/if}
						</div>

						<!-- Notes -->
						<div>
							<label for="notes" class="mise-label">additional notes</label>
							<textarea
								id="notes"
								bind:value={notes}
								placeholder="bruno will add notes here about your cooking style..."
								rows="3"
								class="mise-input resize-none"
								disabled
							></textarea>
							<p class="text-xs text-surface-400 mt-1 tracking-tighter">notes are managed by bruno based on your conversations</p>
						</div>
					</div>
				</div>

				<!-- Save Button -->
				<button
					type="submit"
					disabled={saving}
					class="w-full mise-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if saving}
						<span class="inline-block animate-spin mr-2">🥄</span>
						saving...
					{:else}
						save profile
					{/if}
				</button>
			</form>
		{/if}
	</div>
</div>
