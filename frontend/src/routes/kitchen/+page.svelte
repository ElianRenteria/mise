<script lang="ts">
	import { goto } from '$app/navigation';
	import { pb } from '$lib/pocketbase';
	import { Room, RoomEvent, ConnectionState, TokenSource, Track, type RemoteTrack, type RemoteTrackPublication, type RemoteParticipant } from 'livekit-client';
	import { onDestroy, onMount } from 'svelte';

	// Connection state
	let connectionState: 'idle' | 'connecting' | 'connected' | 'error' = $state('idle');
	let errorMessage: string = $state('');
	let room: Room | null = $state(null);
	let audioContainer: HTMLDivElement;

	// Handle incoming audio tracks from the agent
	function handleTrackSubscribed(
		track: RemoteTrack,
		publication: RemoteTrackPublication,
		participant: RemoteParticipant
	) {
		console.log('Track subscribed:', track.kind, 'from', participant.identity);
		if (track.kind === Track.Kind.Audio) {
			const audioElement = track.attach();
			audioContainer?.appendChild(audioElement);
		}
	}

	// Clean up when tracks are unsubscribed
	function handleTrackUnsubscribed(
		track: RemoteTrack,
		publication: RemoteTrackPublication,
		participant: RemoteParticipant
	) {
		console.log('Track unsubscribed:', track.kind);
		track.detach();
	}

	// Replace with your LiveKit sandbox ID from cloud.livekit.io
	const SANDBOX_ID = 'mise-kitchen-1tqe7v';

	async function startCooking() {
		if (connectionState === 'connecting') return;

		connectionState = 'connecting';
		errorMessage = '';

		try {
			// Create token source from sandbox
			const tokenSource = TokenSource.sandboxTokenServer(SANDBOX_ID);

			// Generate a unique room name based on user
			const roomName = `kitchen-${pb.authStore.record?.id || 'guest'}-${Date.now()}`;

			// Fetch token and dispatch the Bruno agent
			const { serverUrl, participantToken } = await tokenSource.fetch({
				roomName,
				agentName: 'Bruno'
			});

			// Create and connect to room
			room = new Room();

			room.on(RoomEvent.Connected, () => {
				connectionState = 'connected';
			});

			room.on(RoomEvent.Disconnected, () => {
				connectionState = 'idle';
			});

			room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
				if (state === ConnectionState.Disconnected) {
					connectionState = 'idle';
				}
			});

			// Subscribe to audio tracks from the agent
			room.on(RoomEvent.TrackSubscribed, handleTrackSubscribed);
			room.on(RoomEvent.TrackUnsubscribed, handleTrackUnsubscribed);

			await room.connect(serverUrl, participantToken);

			// Enable microphone for voice interaction (requires HTTPS on mobile)
			try {
				const mediaDevices = navigator.mediaDevices;
				if (mediaDevices !== undefined) {
					await room.localParticipant.setMicrophoneEnabled(true);
				} else {
					console.warn('MediaDevices API not available - microphone disabled. Use HTTPS for full functionality.');
				}
			} catch (micError) {
				console.warn('Could not enable microphone:', micError);
			}

		} catch (err) {
			console.error('Failed to connect:', err);
			connectionState = 'error';
			errorMessage = err instanceof Error ? err.message : 'Failed to connect to kitchen';
		}
	}

	async function stopCooking() {
		if (room) {
			await room.disconnect();
			room = null;
		}
		connectionState = 'idle';
	}

	function handleLogout() {
		if (room) {
			room.disconnect();
		}
		pb.authStore.clear();
		goto('/');
	}

	onDestroy(() => {
		if (room) {
			room.disconnect();
		}
	});
</script>

<style>
	/* Animated cooking button styles */
	.cooking-btn {
		position: relative;
		padding: 1.25rem 2.5rem;
		font-size: 1.25rem;
		font-weight: 800;
		letter-spacing: -0.05em;
		text-transform: lowercase;
		border: none;
		border-radius: 9999px;
		cursor: pointer;
		overflow: hidden;
		transition: all 0.3s ease;
		background: linear-gradient(135deg, #d45e33 0%, #e87a4f 50%, #d45e33 100%);
		background-size: 200% 200%;
		color: white;
		box-shadow:
			0 4px 15px rgba(212, 94, 51, 0.4),
			0 0 0 0 rgba(212, 94, 51, 0.4);
	}

	.cooking-btn:hover:not(:disabled) {
		transform: translateY(-2px) scale(1.02);
		box-shadow:
			0 8px 25px rgba(212, 94, 51, 0.5),
			0 0 0 4px rgba(212, 94, 51, 0.2);
		animation: shimmer 1.5s ease infinite;
	}

	.cooking-btn:active:not(:disabled) {
		transform: translateY(0) scale(0.98);
	}

	.cooking-btn:disabled {
		cursor: not-allowed;
		opacity: 0.8;
	}

	@keyframes shimmer {
		0% { background-position: 0% 50%; }
		50% { background-position: 100% 50%; }
		100% { background-position: 0% 50%; }
	}

	/* Steam animation for connecting state */
	.cooking-btn.connecting {
		animation: pulse 1s ease-in-out infinite, shimmer 1.5s ease infinite;
	}

	@keyframes pulse {
		0%, 100% {
			box-shadow:
				0 4px 15px rgba(212, 94, 51, 0.4),
				0 0 0 0 rgba(212, 94, 51, 0.4);
		}
		50% {
			box-shadow:
				0 4px 15px rgba(212, 94, 51, 0.6),
				0 0 0 10px rgba(212, 94, 51, 0);
		}
	}

	/* Spatula icon animation */
	.spatula {
		display: inline-block;
		margin-right: 0.5rem;
		transition: transform 0.3s ease;
	}

	.cooking-btn:hover:not(:disabled) .spatula {
		animation: flip 0.6s ease;
	}

	@keyframes flip {
		0% { transform: rotate(0deg); }
		25% { transform: rotate(-15deg); }
		75% { transform: rotate(15deg); }
		100% { transform: rotate(0deg); }
	}

	/* Loading dots */
	.loading-dots::after {
		content: '';
		animation: dots 1.5s steps(4, end) infinite;
	}

	@keyframes dots {
		0%, 20% { content: ''; }
		40% { content: '.'; }
		60% { content: '..'; }
		80%, 100% { content: '...'; }
	}

	/* Bruno entrance animation */
	.bruno-container {
		animation: slideUp 0.6s ease-out;
	}

	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateY(30px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Bruno subtle idle animation */
	.bruno-standing {
		animation: breathe 3s ease-in-out infinite;
	}

	@keyframes breathe {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.02); }
	}

	/* Stop button */
	.stop-btn {
		padding: 0.75rem 1.5rem;
		font-size: 1rem;
		font-weight: 700;
		letter-spacing: -0.05em;
		text-transform: lowercase;
		border: 2px solid #d45e33;
		border-radius: 9999px;
		cursor: pointer;
		background: transparent;
		color: #d45e33;
		transition: all 0.3s ease;
	}

	.stop-btn:hover {
		background: #d45e33;
		color: white;
	}
</style>

<!-- Hidden container for audio elements from the agent -->
<div bind:this={audioContainer} class="hidden"></div>

<div class="min-h-full flex flex-col items-center justify-center px-4 py-12 bg-surface-300">
	{#if connectionState === 'connected'}
		<!-- Connected state: Show Bruno standing -->
		<div class="bruno-container text-center space-y-6">
			<img
				src="/bruno/standing.svg"
				alt="Bruno the raccoon chef"
				class="bruno-standing w-64 h-auto mx-auto drop-shadow-xl"
			/>
			<h1 class="text-3xl font-black tracking-tighter text-surface-700 lowercase">
				bruno is ready to help!
			</h1>
			<p class="text-lg font-medium tracking-tighter text-surface-500 lowercase max-w-md">
				your ai sous chef is listening. ask me anything about cooking!
			</p>
			<button onclick={stopCooking} class="stop-btn mt-4">
				leave kitchen
			</button>
		</div>
	{:else}
		<!-- Idle/Connecting/Error state: Show button -->
		<div class="text-center space-y-8">
			<img
				src="/bruno/head.svg"
				alt="Bruno the raccoon"
				class="w-32 h-32 mx-auto drop-shadow-lg"
			/>
			<h1 class="text-4xl font-black tracking-tighter text-surface-700 lowercase">
				welcome to the kitchen
			</h1>
			<p class="text-lg font-medium tracking-tighter text-surface-500 lowercase max-w-md">
				bruno is ready to be your ai sous chef. click below to start your cooking session!
			</p>

			<button
				onclick={startCooking}
				disabled={connectionState === 'connecting'}
				class="cooking-btn"
				class:connecting={connectionState === 'connecting'}
			>
				{#if connectionState === 'connecting'}
					<span class="spatula">🥄</span>
					<span class="loading-dots">heating up</span>
				{:else}
					<span class="spatula">🍳</span>
					start cooking
				{/if}
			</button>

			{#if connectionState === 'error'}
				<p class="text-sm font-medium text-error-500 lowercase max-w-md">
					{errorMessage || 'something went wrong. please try again.'}
				</p>
			{/if}
		</div>
	{/if}

	<button onclick={handleLogout} class="mise-link mt-12 inline-block">
		logout
	</button>
</div>
