<script lang="ts">
	import { goto } from '$app/navigation';
	import { pb } from '$lib/pocketbase';

	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSignup(e: Event) {
		e.preventDefault();
		error = '';

		if (password !== confirmPassword) {
			error = 'passwords do not match';
			return;
		}

		if (password.length < 8) {
			error = 'password must be at least 8 characters';
			return;
		}

		loading = true;

		try {
			await pb.collection('users').create({
				email,
				password,
				passwordConfirm: confirmPassword
			});

			// Auto-login after signup
			await pb.collection('users').authWithPassword(email, password);
			await goto('/kitchen');
		} catch (err: any) {
			if (err?.data?.data?.email?.message) {
				error = err.data.data.email.message.toLowerCase();
			} else {
				error = 'failed to create account';
			}
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-full overflow-y-auto flex items-center justify-center px-4 py-6 bg-surface-300">
	<div class="w-full max-w-md">
		<!-- signup card -->
		<div class="mise-card">
			<!-- mise branding -->
			<div class="flex flex-col items-center mb-6">
				<h1 class="text-4xl font-black tracking-tighter lowercase text-surface-700" style="text-shadow: 0 1px 0 rgba(0,0,0,0.1);">
					mise
				</h1>
				<p class="mt-1 text-sm font-medium tracking-tighter lowercase text-surface-500">
					everything in its place
				</p>
			</div>
			<form onsubmit={handleSignup} class="space-y-6">
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
						autocomplete="new-password"
						placeholder="••••••••"
						class="mise-input"
					/>
				</div>

				<div>
					<label for="confirmPassword" class="mise-label">confirm password</label>
					<input
						id="confirmPassword"
						type="password"
						bind:value={confirmPassword}
						required
						autocomplete="new-password"
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
					create account
				</button>
			</form>

			<div class="mt-6 text-center">
				<p class="text-sm text-surface-500 font-medium tracking-tighter">
					already have an account? <a href="/" class="mise-link">login</a>
				</p>
			</div>
		</div>
	</div>
</div>
