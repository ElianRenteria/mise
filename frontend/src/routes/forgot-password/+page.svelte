<script lang="ts">
	import { base } from '$app/paths';
	import { pb } from '$lib/pocketbase';

	let email = $state('');
	let error = $state('');
	let success = $state(false);
	let loading = $state(false);

	async function handleReset(e: Event) {
		e.preventDefault();
		error = '';
		loading = true;

		try {
			await pb.collection('users').requestPasswordReset(email);
			success = true;
		} catch (err) {
			error = 'failed to send reset link';
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-full overflow-y-auto flex items-center justify-center px-4 py-6 bg-surface-300">
	<div class="w-full max-w-md">
		<!-- forgot password card -->
		<div class="mise-card">
			<!-- mise branding -->
			<div class="flex flex-col items-center mb-6">
				<img
					src="{base}/bruno/head.svg"
					alt="Bruno the raccoon"
					class="w-52 h-52 md:w-60 md:h-60 -mb-4"
					style="filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.25)) drop-shadow(0 3px 6px rgba(0, 0, 0, 0.2)) drop-shadow(0 1px 3px rgba(0, 0, 0, 0.15));"
				/>
				<h1 class="text-4xl font-black tracking-tighter lowercase text-surface-700" style="text-shadow: 0 1px 0 rgba(0,0,0,0.1);">
					mise
				</h1>
				<p class="mt-1 text-sm font-medium tracking-tighter lowercase text-surface-500">
					everything in its place
				</p>
			</div>
			{#if success}
				<div class="text-center space-y-4">
					<div class="text-5xl">📧</div>
					<h2 class="text-xl font-black tracking-tighter lowercase text-surface-700">
						check your email
					</h2>
					<p class="text-sm font-medium tracking-tighter text-surface-500">
						we've sent a password reset link to {email}
					</p>
					<a href="{base}/" class="mise-link block mt-4">back to login</a>
				</div>
			{:else}
				<form onsubmit={handleReset} class="space-y-6">
					{#if error}
						<div class="bg-error-100 border border-error-500 text-error-700 px-4 py-3 rounded-xl text-sm font-medium tracking-tighter lowercase">
							{error}
						</div>
					{/if}

					<div>
						<label for="email" class="mise-label">email</label>
						<input
							id="email"
							type="email"
							bind:value={email}
							required
							autocomplete="email"
							placeholder="you@example.com"
							class="mise-input"
						/>
					</div>

					<button
						type="submit"
						disabled={loading}
						class="mise-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{#if loading}
							<span class="inline-block animate-spin mr-2">🥄</span>
						{/if}
						send reset link
					</button>
				</form>

				<div class="mt-6 text-center">
					<a href="{base}/" class="mise-link">back to login</a>
				</div>
			{/if}
		</div>
	</div>
</div>
