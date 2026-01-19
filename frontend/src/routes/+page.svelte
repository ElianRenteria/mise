<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb } from '$lib/pocketbase';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleLogin(e: Event) {
		e.preventDefault();
		error = '';
		loading = true;

		try {
			await pb.collection('users').authWithPassword(email, password);
			await goto('/kitchen');
		} catch (err) {
			error = 'invalid email or password';
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-full overflow-y-auto flex items-center justify-center px-4 py-6 mise-gradient-bg">
	<div class="w-full max-w-md">
		<!-- login card -->
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
			<form onsubmit={handleLogin} class="space-y-6">
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

				<div>
					<label for="password" class="mise-label">password</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						autocomplete="current-password"
						placeholder="••••••••"
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
					login
				</button>
			</form>

			<div class="mt-6 text-center space-y-2">
				<p class="text-sm text-surface-500 font-medium tracking-tighter">
					<a href="{base}/forgot-password" class="mise-link">forgot password?</a>
				</p>
				<p class="text-sm text-surface-500 font-medium tracking-tighter">
					don't have an account? <a href="{base}/signup" class="mise-link">create account</a>
				</p>
			</div>
		</div>
	</div>
</div>
