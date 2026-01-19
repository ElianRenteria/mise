<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>mise - everything in its place</title>
</svelte:head>

<div class="h-full w-full" data-theme="mise-theme">
	{@render children()}
</div>
