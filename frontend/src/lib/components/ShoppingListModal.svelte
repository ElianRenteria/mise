<script lang="ts">
	let {
		recipeName,
		items,
		onClose
	}: {
		recipeName: string;
		items: string[];
		onClose: () => void;
	} = $props();

	let copied = $state(false);
	let shared = $state(false);

	// Check if Web Share API is available
	const canShare = typeof navigator !== 'undefined' && !!navigator.share;

	function formatListForSharing(): string {
		const header = `Shopping List for ${recipeName}`;
		const itemList = items.map(item => `• ${item}`).join('\n');
		return `${header}\n\n${itemList}\n\n— from mise`;
	}

	async function handleShare() {
		const text = formatListForSharing();

		if (canShare) {
			try {
				await navigator.share({
					title: `Shopping List: ${recipeName}`,
					text: text
				});
				shared = true;
				setTimeout(() => shared = false, 2000);
			} catch (err) {
				// User cancelled or share failed, fall back to copy
				if ((err as Error).name !== 'AbortError') {
					await handleCopy();
				}
			}
		} else {
			await handleCopy();
		}
	}

	async function handleCopy() {
		const text = formatListForSharing();

		try {
			await navigator.clipboard.writeText(text);
			copied = true;
			setTimeout(() => copied = false, 2000);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Backdrop -->
<button
	class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 cursor-default border-none"
	onclick={onClose}
	aria-label="Close"
></button>

<!-- Modal -->
<div class="fixed inset-4 md:inset-8 lg:inset-16 bg-white rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden max-w-lg mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 md:p-6 border-b border-surface-200">
		<div class="flex items-center gap-3">
			<span class="text-2xl">🛒</span>
			<div>
				<h2 class="text-lg font-black tracking-tighter text-surface-700 lowercase">
					shopping list
				</h2>
				<p class="text-sm text-surface-500 font-medium tracking-tighter lowercase">
					{recipeName}
				</p>
			</div>
		</div>
		<button
			onclick={onClose}
			class="p-2 rounded-full hover:bg-surface-100 transition-colors"
			aria-label="Close"
		>
			<svg class="w-6 h-6 text-surface-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	<!-- List -->
	<div class="flex-1 overflow-y-auto p-4 md:p-6">
		<ul class="space-y-3">
			{#each items as item, i (i)}
				<li class="flex items-start gap-3 p-3 bg-surface-50 rounded-xl">
					<span class="w-6 h-6 rounded-full border-2 border-surface-300 flex-shrink-0 mt-0.5"></span>
					<span class="text-surface-700 font-medium tracking-tighter">{item}</span>
				</li>
			{/each}
		</ul>
	</div>

	<!-- Footer -->
	<div class="p-4 md:p-6 border-t border-surface-200 space-y-3">
		<button
			onclick={handleShare}
			class="w-full py-3 px-4 bg-primary-500 hover:bg-primary-600 text-white font-bold tracking-tighter lowercase rounded-xl transition-colors flex items-center justify-center gap-2"
		>
			{#if copied}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
				copied!
			{:else if shared}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
				shared!
			{:else if canShare}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
				</svg>
				share list
			{:else}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
				</svg>
				copy list
			{/if}
		</button>

		<p class="text-xs text-center text-surface-400 font-medium tracking-tighter lowercase">
			come back when you have everything and bruno will start cooking with you
		</p>
	</div>
</div>
