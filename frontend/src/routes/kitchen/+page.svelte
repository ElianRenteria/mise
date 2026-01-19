<script lang="ts">
	import { goto } from '$app/navigation';
	import { pb } from '$lib/pocketbase';

	function handleLogout() {
		pb.authStore.clear();
		goto('/');
	}
</script>

<div class="min-h-full flex flex-col items-center justify-center px-4 py-12 bg-surface-300">
	<div class="text-center space-y-6">
		<div class="text-8xl">🦝</div>
		<h1 class="text-4xl font-black tracking-tighter text-surface-700 lowercase">
			kitchen history
		</h1>
		<p class="text-xl font-medium tracking-tighter text-surface-500 lowercase">
			coming soon...
		</p>
		<p class="text-sm font-medium tracking-tighter text-surface-500 max-w-md">
			bruno is getting the kitchen ready for you. check back soon to start cooking with your ai sous chef!
		</p>
		<button onclick={handleLogout} class="mise-link mt-8 inline-block">
			logout
		</button>
	</div>
</div>
