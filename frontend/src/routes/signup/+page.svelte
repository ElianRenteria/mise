<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb } from '$lib/pocketbase';

	let firstName = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSignup(e: Event) {
		e.preventDefault();
		error = '';

		if (!firstName.trim()) {
			error = 'please enter your first name';
			return;
		}

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
			// Create the user account
			const newUser = await pb.collection('users').create({
				email,
				password,
				passwordConfirm: confirmPassword,
				name: firstName.trim()
			});

			// Request verification email
			try {
				await pb.collection('users').requestVerification(email);
			} catch (verifyErr) {
				console.warn('Failed to send verification email:', verifyErr);
			}

			// Auto-login after signup
			await pb.collection('users').authWithPassword(email, password);

			// Generate and set DiceBear avatar
			try {
				const avatarUrl = `https://api.dicebear.com/9.x/dylan/svg?seed=${encodeURIComponent(firstName.trim())}`;
				const response = await fetch(avatarUrl);
				const svgBlob = await response.blob();

				// Create a File object from the blob
				const avatarFile = new File([svgBlob], `avatar-${firstName.trim()}.svg`, { type: 'image/svg+xml' });

				// Upload avatar to user record
				const formData = new FormData();
				formData.append('avatar', avatarFile);
				await pb.collection('users').update(newUser.id, formData);

				// Refresh auth to get updated user data with avatar
				await pb.collection('users').authRefresh();
			} catch (avatarErr) {
				// Avatar upload failed, but account was created - continue anyway
				console.warn('Failed to set avatar:', avatarErr);
			}

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

<div class="min-h-full overflow-y-auto flex items-center justify-center px-4 py-6 mise-gradient-bg">
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
					<label for="firstName" class="mise-label">first name</label>
					<input
						id="firstName"
						type="text"
						bind:value={firstName}
						required
						autocomplete="given-name"
						placeholder="chef"
						class="mise-input"
					/>
				</div>

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
					already have an account? <a href="{base}/" class="mise-link">login</a>
				</p>
			</div>
		</div>
	</div>
</div>
