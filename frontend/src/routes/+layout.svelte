<script lang="ts">
	import '../app.css';
	import { base } from '$app/paths';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href="{base}/bruno/head.svg" type="image/svg+xml" />
	<title>mise - everything in its place</title>
</svelte:head>

<!-- Landscape orientation overlay for mobile -->
<div class="landscape-overlay">
	<div class="flex flex-col items-center justify-center h-full text-center p-8 mise-gradient-bg">
		<img src="{base}/bruno/thinking.svg" alt="Bruno" class="w-32 h-32 mb-6" />
		<h2 class="text-2xl font-black tracking-tighter text-surface-700 lowercase mb-2">
			please rotate your device
		</h2>
		<p class="text-surface-500 font-medium tracking-tighter lowercase">
			mise works best in portrait mode
		</p>
		<div class="mt-6 animate-bounce">
			<svg class="w-10 h-10 text-primary-500 rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l-7-7 7-7m8 14l-7-7 7-7" />
			</svg>
		</div>
	</div>
</div>

<div class="h-full w-full overflow-auto" data-theme="mise-theme">
	{@render children()}
</div>

<style>
	/* Hide landscape overlay by default */
	.landscape-overlay {
		display: none;
		position: fixed;
		inset: 0;
		z-index: 9999;
		background: white;
	}

	/* Show overlay only on mobile devices in landscape */
	@media screen and (max-height: 500px) and (orientation: landscape) {
		.landscape-overlay {
			display: block;
		}
	}
</style>
