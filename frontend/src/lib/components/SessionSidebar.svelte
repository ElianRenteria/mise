<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb, type CookingSession } from '$lib/pocketbase';

	// Props
	let {
		isOpen = $bindable(false),
		onStartNew,
		onViewSession,
		currentSessionId = null
	}: {
		isOpen: boolean;
		onStartNew: () => void;
		onViewSession: (session: CookingSession) => void;
		currentSessionId?: string | null;
	} = $props();

	let sessions: CookingSession[] = $state([]);
	let loading: boolean = $state(true);
	let deletingId: string | null = $state(null);
	let error: string = $state('');

	// Reload sessions when sidebar opens
	$effect(() => {
		if (isOpen) {
			loadSessions();
		}
	});

	async function loadSessions() {
		loading = true;
		error = '';
		try {
			const userId = pb.authStore.record?.id;
			if (!userId) {
				error = 'not logged in';
				return;
			}

			console.log('Loading sessions for user:', userId);

			// Load sessions sorted by most recent first
			const records = await pb.collection('cooking_sessions').getList<CookingSession>(1, 50, {
				filter: `user = "${userId}"`,
				sort: '-created'
			});

			console.log('Loaded sessions:', records.items.length);
			sessions = records.items;
		} catch (err: unknown) {
			console.error('Failed to load sessions:', err);
			const errorObj = err as { status?: number; message?: string; response?: { message?: string } };

			// Log full error for debugging
			console.error('Full error:', JSON.stringify(err, null, 2));

			if (errorObj.status === 400) {
				error = 'collection not configured correctly - check pocketbase';
			} else if (errorObj.status === 403 || errorObj.status === 404) {
				error = 'permission denied - check api rules';
			} else {
				error = errorObj.response?.message || errorObj.message || 'failed to load sessions';
			}
		} finally {
			loading = false;
		}
	}

	async function deleteSession(sessionId: string) {
		deletingId = sessionId;
		try {
			await pb.collection('cooking_sessions').delete(sessionId);
			sessions = sessions.filter(s => s.id !== sessionId);
		} catch (err) {
			console.error('Failed to delete session:', err);
		} finally {
			deletingId = null;
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const days = Math.floor(diff / (1000 * 60 * 60 * 24));

		if (days === 0) {
			return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
		} else if (days === 1) {
			return 'yesterday';
		} else if (days < 7) {
			return date.toLocaleDateString('en-US', { weekday: 'short' });
		} else {
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		}
	}

	function getSessionTitle(session: CookingSession): string {
		// Use recipe_name as the title (we store the session title here)
		if (session.recipe_name) {
			return session.recipe_name;
		}
		// Fallback to first user message from transcript
		// Handle potential stringified JSON from old bug
		let transcriptData = session.transcript;
		if (typeof transcriptData === 'string') {
			try {
				transcriptData = JSON.parse(transcriptData);
			} catch {
				transcriptData = [];
			}
		}
		if (Array.isArray(transcriptData) && transcriptData.length > 0) {
			const firstUserMessage = transcriptData.find(m => m.role === 'user');
			if (firstUserMessage) {
				const content = firstUserMessage.content
					.replace(/[^\w\s]/g, '')
					.trim()
					.slice(0, 40)
					.toLowerCase();
				return content + (firstUserMessage.content.length > 40 ? '...' : '');
			}
		}
		return 'new session';
	}

	function getStatusIcon(status: string): string {
		switch (status) {
			case 'completed': return '✓';
			case 'in_progress': return '●';
			case 'abandoned': return '○';
			default: return '○';
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'completed': return 'text-success-500';
			case 'in_progress': return 'text-primary-500';
			case 'abandoned': return 'text-surface-400';
			default: return 'text-surface-400';
		}
	}

	function close() {
		isOpen = false;
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			close();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			close();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Backdrop -->
{#if isOpen}
	<button
		class="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 transition-opacity duration-300 cursor-default border-none"
		onclick={handleBackdropClick}
		aria-label="Close sidebar"
	></button>
{/if}

<!-- Sidebar -->
<div
	class="fixed inset-y-0 left-0 w-full max-w-sm bg-surface-100 shadow-2xl z-50 transform transition-transform duration-300 ease-out flex flex-col"
	class:translate-x-0={isOpen}
	class:-translate-x-full={!isOpen}
>
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-surface-200">
		<div class="flex items-center gap-3">
			<img src="{base}/bruno/head.svg" alt="Bruno" class="w-8 h-8" />
			<h2 class="text-xl font-black tracking-tighter text-surface-700 lowercase">
				kitchen history
			</h2>
		</div>
		<button
			onclick={close}
			class="p-2 rounded-full hover:bg-surface-200 transition-colors"
			aria-label="Close sidebar"
		>
			<svg class="w-5 h-5 text-surface-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	<!-- New Session Button -->
	<div class="p-4 border-b border-surface-200">
		<button
			onclick={() => { onStartNew(); close(); }}
			class="w-full py-3 px-4 bg-primary-500 hover:bg-primary-600 text-white font-bold tracking-tighter lowercase rounded-xl transition-colors flex items-center justify-center gap-2"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
			</svg>
			cook something new
		</button>
	</div>

	<!-- Sessions List -->
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<!-- Loading Skeletons -->
			<div class="p-2 space-y-1">
				{#each [1, 2, 3, 4] as _}
					<div class="bg-white rounded-xl p-3 animate-pulse">
						<div class="flex items-start gap-3">
							<div class="w-5 h-5 bg-surface-200 rounded-full"></div>
							<div class="flex-1 space-y-2">
								<div class="h-4 bg-surface-200 rounded w-3/4"></div>
								<div class="h-3 bg-surface-100 rounded w-1/2"></div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{:else if error}
			<div class="text-center py-12 px-4">
				<div class="text-4xl mb-3">⚠️</div>
				<p class="text-error-500 font-medium tracking-tighter lowercase mb-2">
					{error}
				</p>
				<button
					onclick={() => loadSessions()}
					class="text-sm text-primary-500 hover:text-primary-600 font-medium tracking-tighter lowercase"
				>
					try again
				</button>
			</div>
		{:else if sessions.length === 0}
			<div class="text-center py-12 px-4">
				<div class="text-4xl mb-3">🍳</div>
				<p class="text-surface-500 font-medium tracking-tighter lowercase">
					no cooking sessions yet
				</p>
			</div>
		{:else}
			<div class="p-2 space-y-1">
				{#each sessions as session (session.id)}
					<div
						class="group relative bg-white rounded-xl p-3 hover:bg-surface-50 transition-colors border border-transparent hover:border-surface-200 w-full text-left cursor-pointer"
						class:border-primary-200={currentSessionId === session.id}
						class:bg-primary-50={currentSessionId === session.id}
						onclick={() => {
							onViewSession(session);
							close();
						}}
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								onViewSession(session);
								close();
							}
						}}
						role="button"
						tabindex="0"
					>
						<!-- Session Info -->
						<div class="flex items-start gap-3">
							<span class="text-lg {getStatusColor(session.status)}" title={session.status}>
								{getStatusIcon(session.status)}
							</span>
							<div class="flex-1 min-w-0">
								<h3 class="text-sm font-bold tracking-tighter text-surface-700 lowercase truncate">
									{getSessionTitle(session)}
								</h3>
								<p class="text-xs font-medium tracking-tighter text-surface-400 lowercase mt-0.5">
									{formatDate(session.created)}
									{#if session.transcript && session.transcript.length > 0}
										· {session.transcript.length} msgs
									{/if}
								</p>
							</div>
						</div>

						<!-- Action Buttons (visible on hover) -->
						<div
							class="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
							onclick={(e) => e.stopPropagation()}
							onkeydown={(e) => e.stopPropagation()}
							role="group"
						>
							<!-- View transcript button -->
							<button
								onclick={() => { onViewSession(session); close(); }}
								class="p-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white transition-colors"
								title="View transcript"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
								</svg>
							</button>
							<button
								onclick={() => deleteSession(session.id)}
								disabled={deletingId === session.id}
								class="p-2 rounded-lg bg-surface-200 hover:bg-error-100 text-surface-500 hover:text-error-500 transition-colors disabled:opacity-50"
								title="Delete session"
							>
								{#if deletingId === session.id}
									<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
								{:else}
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
									</svg>
								{/if}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Footer -->
	<div class="p-4 border-t border-surface-200">
		<button
			onclick={() => { pb.authStore.clear(); goto(`${base}/`); }}
			class="w-full py-2 text-sm font-medium tracking-tighter text-surface-500 hover:text-primary-500 lowercase transition-colors"
		>
			logout
		</button>
	</div>
</div>
