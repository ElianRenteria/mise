<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb, getAvatarUrl, type UserPreferences, type FavoriteRecipe } from '$lib/pocketbase';
	import { onMount } from 'svelte';

	// Tab state
	type Tab = 'settings' | 'favorites';
	let activeTab: Tab = $state('settings');

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

	// Favorites
	let favorites: FavoriteRecipe[] = $state([]);
	let loadingFavorites = $state(false);
	let favoritesLoaded = $state(false);
	let selectedFavorite: FavoriteRecipe | null = $state(null);

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

	async function loadFavorites() {
		const userId = pb.authStore.record?.id;
		if (!userId) return;

		loadingFavorites = true;
		try {
			const records = await pb.collection('favorite_recipes').getList<FavoriteRecipe>(1, 50, {
				filter: `user = "${userId}"`,
				sort: '-created'
			});
			favorites = records.items;
			favoritesLoaded = true;
		} catch (err) {
			console.error('Failed to load favorites:', err);
			favoritesLoaded = true; // Mark as loaded even on error to prevent infinite retries
		} finally {
			loadingFavorites = false;
		}
	}

	async function deleteFavorite(id: string) {
		try {
			await pb.collection('favorite_recipes').delete(id);
			favorites = favorites.filter(f => f.id !== id);
			if (selectedFavorite?.id === id) {
				selectedFavorite = null;
			}
		} catch (err) {
			console.error('Failed to delete favorite:', err);
		}
	}

	async function updateRating(id: string, rating: number) {
		try {
			await pb.collection('favorite_recipes').update(id, { rating });
			favorites = favorites.map(f => f.id === id ? { ...f, rating } : f);
			if (selectedFavorite?.id === id) {
				selectedFavorite = { ...selectedFavorite, rating };
			}
		} catch (err) {
			console.error('Failed to update rating:', err);
		}
	}

	// Load favorites when switching to that tab
	$effect(() => {
		if (activeTab === 'favorites' && !favoritesLoaded && !loadingFavorites) {
			loadFavorites();
		}
	});

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
			const updatedUser = await pb.collection('users').update(userId, {
				name: name.trim()
			});

			// Update DiceBear avatar if user doesn't have a custom avatar
			if (!updatedUser.avatar) {
				const seed = name.trim() || email.split('@')[0];
				avatarUrl = `https://api.dicebear.com/9.x/dylan/svg?seed=${encodeURIComponent(seed)}`;
			}

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

	function renderStars(rating: number | undefined): string {
		const filled = rating || 0;
		return '★'.repeat(filled) + '☆'.repeat(5 - filled);
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

		<!-- Tab Navigation -->
		<div class="max-w-2xl mx-auto px-4">
			<div class="flex gap-1 bg-surface-100 p-1 rounded-xl">
				<button
					onclick={() => activeTab = 'settings'}
					class="flex-1 py-2 px-4 rounded-lg font-bold tracking-tighter lowercase text-sm transition-all {activeTab === 'settings' ? 'bg-white text-surface-700 shadow-sm' : 'text-surface-500 hover:text-surface-700'}"
				>
					settings
				</button>
				<button
					onclick={() => activeTab = 'favorites'}
					class="flex-1 py-2 px-4 rounded-lg font-bold tracking-tighter lowercase text-sm transition-all {activeTab === 'favorites' ? 'bg-white text-surface-700 shadow-sm' : 'text-surface-500 hover:text-surface-700'}"
				>
					favorites
				</button>
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
		{:else if activeTab === 'settings'}
			<!-- Settings Tab -->
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
		{:else}
			<!-- Favorites Tab -->
			{#if loadingFavorites}
				<div class="space-y-4">
					{#each [1, 2, 3] as _}
						<div class="bg-white rounded-2xl p-4 shadow-sm animate-pulse">
							<div class="flex gap-4">
								<div class="w-20 h-20 bg-surface-200 rounded-xl"></div>
								<div class="flex-1 space-y-2">
									<div class="h-5 bg-surface-200 rounded w-3/4"></div>
									<div class="h-4 bg-surface-100 rounded w-1/2"></div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else if favorites.length === 0}
				<div class="text-center py-12 bg-white rounded-2xl shadow-sm">
					<div class="text-5xl mb-4">🍽️</div>
					<h3 class="text-lg font-bold tracking-tighter text-surface-700 lowercase mb-2">
						no favorites yet
					</h3>
					<p class="text-sm text-surface-500 tracking-tighter lowercase max-w-xs mx-auto">
						after cooking a recipe, tell bruno you want to add it to your favorites
					</p>
				</div>
			{:else}
				<div class="space-y-3">
					{#each favorites as favorite (favorite.id)}
						<button
							onclick={() => selectedFavorite = favorite}
							class="w-full bg-white rounded-2xl p-4 shadow-sm hover:shadow-md transition-shadow text-left"
						>
							<div class="flex gap-4 items-center">
								{#if favorite.recipe_image}
									<img
										src={favorite.recipe_image}
										alt={favorite.recipe_name}
										class="w-24 h-24 rounded-xl object-cover bg-surface-100 flex-shrink-0"
									/>
								{:else}
									<div class="w-24 h-24 rounded-xl bg-surface-100 flex items-center justify-center text-4xl flex-shrink-0">
										🍳
									</div>
								{/if}
								<div class="flex-1 min-w-0">
									<h3 class="font-bold tracking-tighter text-surface-700 lowercase truncate">
										{favorite.recipe_name}
									</h3>
									<p class="text-primary-500 text-sm mt-1">
										{renderStars(favorite.rating)}
									</p>
									{#if favorite.description}
										<p class="text-sm text-surface-500 mt-1 line-clamp-2">
											{favorite.description}
										</p>
									{/if}
								</div>
							</div>
						</button>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>

<!-- Favorite Detail Modal -->
{#if selectedFavorite}
	<button
		class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 cursor-default border-none"
		onclick={() => selectedFavorite = null}
		aria-label="Close"
	></button>
	<div class="fixed inset-4 md:inset-8 lg:inset-16 bg-white rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden">
		<!-- Header -->
		<div class="flex items-start justify-between p-4 md:p-6 border-b border-surface-200">
			<div class="flex-1 min-w-0 pr-4">
				<h2 class="text-xl font-black tracking-tighter text-surface-700 lowercase truncate">
					{selectedFavorite.recipe_name}
				</h2>
				<!-- Star Rating -->
				<div class="flex items-center gap-1 mt-2">
					{#each [1, 2, 3, 4, 5] as star}
						<button
							onclick={() => updateRating(selectedFavorite!.id, star)}
							class="text-2xl transition-colors {star <= (selectedFavorite?.rating || 0) ? 'text-primary-500' : 'text-surface-300 hover:text-primary-300'}"
						>
							★
						</button>
					{/each}
				</div>
			</div>
			<button
				onclick={() => selectedFavorite = null}
				class="p-2 rounded-full hover:bg-surface-200 transition-colors"
				aria-label="Close"
			>
				<svg class="w-6 h-6 text-surface-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-4 md:p-6">
			{#if selectedFavorite.recipe_image}
				<img
					src={selectedFavorite.recipe_image}
					alt={selectedFavorite.recipe_name}
					class="w-full h-48 md:h-64 rounded-xl object-cover mb-6"
				/>
			{/if}

			{#if selectedFavorite.description}
				<div class="mb-6">
					<h3 class="text-sm font-bold tracking-tighter text-surface-500 lowercase mb-2">description</h3>
					<p class="text-surface-700">{selectedFavorite.description}</p>
				</div>
			{/if}

			{#if selectedFavorite.ingredients && selectedFavorite.ingredients.length > 0}
				<div>
					<h3 class="text-sm font-bold tracking-tighter text-surface-500 lowercase mb-2">ingredients</h3>
					<div class="flex flex-wrap gap-2">
						{#each selectedFavorite.ingredients as ingredient}
							<span class="px-3 py-1 bg-surface-100 text-surface-700 rounded-full text-sm font-medium tracking-tighter lowercase">
								{ingredient}
							</span>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="p-4 border-t border-surface-200 flex justify-between items-center">
			<button
				onclick={() => { deleteFavorite(selectedFavorite!.id); }}
				class="px-4 py-2 text-error-500 hover:bg-error-50 font-bold tracking-tighter lowercase rounded-xl transition-colors"
			>
				remove from favorites
			</button>
			<button
				onclick={() => selectedFavorite = null}
				class="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-bold tracking-tighter lowercase rounded-xl transition-colors"
			>
				close
			</button>
		</div>
	</div>
{/if}
