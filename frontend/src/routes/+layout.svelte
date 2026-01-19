<script lang="ts">
	import '../app.css';
	import { base } from '$app/paths';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href="{base}/bruno/head.svg" type="image/svg+xml" />
	<title>mise - everything in its place</title>
</svelte:head>

<div class="h-full w-full overflow-auto" data-theme="mise-theme">
	{@render children()}
</div>
