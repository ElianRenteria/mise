<script lang="ts">
	import { base } from '$app/paths';
	import type { CookingSession, TranscriptMessage } from '$lib/pocketbase';

	let {
		session,
		onClose,
		onContinue
	}: {
		session: CookingSession;
		onClose: () => void;
		onContinue?: (session: CookingSession) => void;
	} = $props();

	// Parse transcript - handle both array and stringified JSON
	function getTranscript(): TranscriptMessage[] {
		let transcriptData = session.transcript;
		if (typeof transcriptData === 'string') {
			try {
				transcriptData = JSON.parse(transcriptData);
			} catch {
				return [];
			}
		}
		return Array.isArray(transcriptData) ? transcriptData : [];
	}

	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit',
			hour12: true
		});
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			year: 'numeric'
		});
	}

	function getSessionTitle(): string {
		if (session.recipe_name) {
			return session.recipe_name;
		}
		const transcript = getTranscript();
		if (transcript.length > 0) {
			const firstUserMessage = transcript.find(m => m.role === 'user');
			if (firstUserMessage) {
				return firstUserMessage.content.slice(0, 50).toLowerCase() + (firstUserMessage.content.length > 50 ? '...' : '');
			}
		}
		return 'cooking session';
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		}
	}

	const transcript = getTranscript();
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Backdrop -->
<button
	class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 transition-opacity duration-300 cursor-default border-none"
	onclick={handleBackdropClick}
	aria-label="Close transcript"
></button>

<!-- Transcript Modal -->
<div class="fixed inset-4 md:inset-8 lg:inset-16 bg-white rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 md:p-6 border-b border-surface-200 bg-surface-50">
		<div class="flex items-center gap-3">
			<img src="{base}/bruno/head.svg" alt="Bruno" class="w-10 h-10" />
			<div>
				<h2 class="text-xl font-black tracking-tighter text-surface-700 lowercase">
					{getSessionTitle()}
				</h2>
				<p class="text-sm font-medium tracking-tighter text-surface-400 lowercase">
					{formatDate(session.created)}
				</p>
			</div>
		</div>
		<button
			onclick={onClose}
			class="p-2 rounded-full hover:bg-surface-200 transition-colors"
			aria-label="Close transcript"
		>
			<svg class="w-6 h-6 text-surface-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	<!-- Transcript Content -->
	<div class="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
		{#if transcript.length === 0}
			<div class="text-center py-12">
				<div class="text-4xl mb-3">📝</div>
				<p class="text-surface-500 font-medium tracking-tighter lowercase">
					no messages in this session
				</p>
			</div>
		{:else}
			{#each transcript as message, i (i)}
				<div class="flex gap-3 {message.role === 'user' ? 'flex-row-reverse' : ''}">
					<!-- Avatar -->
					<div class="flex-shrink-0">
						{#if message.role === 'assistant'}
							<img src="{base}/bruno/head.svg" alt="Bruno" class="w-8 h-8 rounded-full" />
						{:else}
							<div class="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center">
								<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
								</svg>
							</div>
						{/if}
					</div>

					<!-- Message Bubble -->
					<div class="flex flex-col {message.role === 'user' ? 'items-end' : 'items-start'} max-w-[80%]">
						<div class="px-4 py-2 rounded-2xl {message.role === 'user'
							? 'bg-primary-500 text-white rounded-br-md'
							: 'bg-surface-100 text-surface-700 rounded-bl-md'}">
							<p class="text-sm leading-relaxed">{message.content}</p>
						</div>
						{#if message.timestamp}
							<span class="text-xs text-surface-400 mt-1 px-2">
								{formatTime(message.timestamp)}
							</span>
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>

	<!-- Footer -->
	<div class="p-4 border-t border-surface-200 bg-surface-50">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<span class="text-sm font-medium tracking-tighter text-surface-500 lowercase">
					{transcript.length} messages
				</span>
				<span class="text-surface-300">·</span>
				<span class="text-sm font-medium tracking-tighter lowercase {
					session.status === 'completed' ? 'text-success-500' :
					session.status === 'in_progress' ? 'text-primary-500' : 'text-surface-400'
				}">
					{session.status === 'in_progress' ? 'in progress' : session.status}
				</span>
			</div>
			<div class="flex items-center gap-2">
				{#if onContinue && transcript.length > 0}
					<button
						onclick={() => { onContinue(session); onClose(); }}
						class="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-bold tracking-tighter lowercase rounded-xl transition-colors flex items-center gap-2"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						continue
					</button>
				{/if}
				<button
					onclick={onClose}
					class="px-4 py-2 bg-surface-200 hover:bg-surface-300 text-surface-600 font-bold tracking-tighter lowercase rounded-xl transition-colors"
				>
					close
				</button>
			</div>
		</div>
	</div>
</div>
