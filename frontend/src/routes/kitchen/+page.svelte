<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb } from '$lib/pocketbase';
	import { Room, RoomEvent, ConnectionState, TokenSource, Track, ParticipantKind, type RemoteTrack, type RemoteTrackPublication, type RemoteParticipant, type Participant } from 'livekit-client';
	import { onDestroy } from 'svelte';

	// Connection state
	let connectionState: 'idle' | 'connecting' | 'connected' | 'error' = $state('idle');
	let errorMessage: string = $state('');
	let room: Room | null = $state(null);
	let audioContainer: HTMLDivElement;

	// Agent state for Bruno animation
	type AgentState = 'initializing' | 'listening' | 'thinking' | 'speaking';
	let agentState: AgentState = $state('initializing');

	// User speaking state for voice indicator
	let userIsSpeaking: boolean = $state(false);

	// Tool usage tracking
	let isUsingTool: boolean = $state(false);
	let currentToolName: string = $state('');

	// Show thinking state with minimum duration
	let showThinking: boolean = $state(false);
	let thinkingTimeout: ReturnType<typeof setTimeout> | null = null;
	const MINIMUM_THINKING_DURATION = 4000; // Show thinking for at least 4 seconds

	// Keep thinking state visible for minimum duration (but not during speaking)
	$effect(() => {
		// Speaking always takes priority - immediately hide thinking
		if (agentState === 'speaking') {
			if (thinkingTimeout) {
				clearTimeout(thinkingTimeout);
				thinkingTimeout = null;
			}
			showThinking = false;
			return;
		}

		if (agentState === 'thinking' || isUsingTool) {
			// Clear any pending timeout
			if (thinkingTimeout) {
				clearTimeout(thinkingTimeout);
				thinkingTimeout = null;
			}
			showThinking = true;
		} else if (showThinking && agentState === 'listening') {
			// Only delay hiding if we're going back to listening (not speaking)
			thinkingTimeout = setTimeout(() => {
				showThinking = false;
				thinkingTimeout = null;
			}, MINIMUM_THINKING_DURATION);
		}

		return () => {
			if (thinkingTimeout) {
				clearTimeout(thinkingTimeout);
			}
		};
	});

	// Handle agent state changes from participant attributes
	function handleParticipantAttributesChanged(
		changedAttributes: Record<string, string>,
		participant: Participant
	) {
		// Check if this is an agent participant
		if (participant.kind === ParticipantKind.AGENT) {
			const state = participant.attributes['lk.agent.state'] as AgentState | undefined;
			if (state) {
				console.log('Agent state changed:', state);
				agentState = state;
			}

			// Check for tool usage - agents often report this via attributes
			const toolCall = participant.attributes['lk.agent.llm.tool_call'];
			if (toolCall) {
				try {
					const toolData = JSON.parse(toolCall);
					isUsingTool = true;
					currentToolName = toolData.name || toolData.tool || 'tool';
					console.log('Agent using tool:', currentToolName);
				} catch {
					// Tool call might be a simple string
					isUsingTool = true;
					currentToolName = toolCall;
				}
			} else if (changedAttributes['lk.agent.llm.tool_call'] === '') {
				// Tool call cleared
				isUsingTool = false;
				currentToolName = '';
			}

			// Also check for thinking state to indicate tool usage
			if (state === 'thinking') {
				// Could be using a tool or just thinking
			}
		}
	}

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

			// Listen for agent state changes
			room.on(RoomEvent.ParticipantAttributesChanged, handleParticipantAttributesChanged);

			// Listen for user speaking changes
			room.on(RoomEvent.ActiveSpeakersChanged, (speakers: Participant[]) => {
				userIsSpeaking = speakers.some(s => s.identity === room?.localParticipant.identity);
			});

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

	/* Voice wave animation for user speaking */
	.voice-wave {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 3px;
		height: 24px;
	}

	.voice-wave .bar {
		width: 4px;
		height: 100%;
		background: #d45e33;
		border-radius: 2px;
		animation: wave 0.8s ease-in-out infinite;
	}

	.voice-wave .bar:nth-child(1) { animation-delay: 0s; }
	.voice-wave .bar:nth-child(2) { animation-delay: 0.1s; }
	.voice-wave .bar:nth-child(3) { animation-delay: 0.2s; }
	.voice-wave .bar:nth-child(4) { animation-delay: 0.3s; }
	.voice-wave .bar:nth-child(5) { animation-delay: 0.4s; }

	@keyframes wave {
		0%, 100% {
			transform: scaleY(0.3);
		}
		50% {
			transform: scaleY(1);
		}
	}

	/* Voice indicator container */
	.voice-indicator {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		background: rgba(212, 94, 51, 0.1);
		border-radius: 9999px;
		transition: opacity 0.2s ease;
	}

	/* Tool usage indicator */
	.tool-indicator {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 18px;
		background: rgba(130, 129, 131, 0.1);
		border-radius: 9999px;
		border: 1px solid rgba(130, 129, 131, 0.2);
	}

	.tool-spinner {
		width: 18px;
		height: 18px;
		border: 2px solid rgba(130, 129, 131, 0.3);
		border-top-color: #828183;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Bruno speaking indicator */
	.bruno-speaking-indicator {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		background: rgba(181, 173, 163, 0.2);
		border-radius: 9999px;
		transition: opacity 0.2s ease;
	}

	.bruno-voice-wave {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 3px;
		height: 24px;
	}

	.bruno-voice-wave .bar {
		width: 4px;
		height: 100%;
		background: #998f83;
		border-radius: 2px;
		animation: wave 0.8s ease-in-out infinite;
	}

	.bruno-voice-wave .bar:nth-child(1) { animation-delay: 0s; }
	.bruno-voice-wave .bar:nth-child(2) { animation-delay: 0.1s; }
	.bruno-voice-wave .bar:nth-child(3) { animation-delay: 0.2s; }
	.bruno-voice-wave .bar:nth-child(4) { animation-delay: 0.3s; }
	.bruno-voice-wave .bar:nth-child(5) { animation-delay: 0.4s; }
</style>

<!-- Hidden container for audio elements from the agent -->
<div bind:this={audioContainer} class="hidden"></div>

<div class="min-h-full flex flex-col items-center justify-center px-4 py-12 mise-gradient-bg">
	{#if connectionState === 'connected'}
		<!-- Connected state: Show Bruno -->
		<div class="bruno-container text-center space-y-3">
			<div class="relative w-64 mx-auto">
				<!-- Thinking Bruno (shown when thinking or using tool) -->
				<img
					src="{base}/bruno/thinking.svg"
					alt="Bruno the raccoon chef thinking"
					class="w-full h-auto drop-shadow-xl transition-opacity duration-500 ease-in-out"
					class:opacity-100={showThinking}
					class:opacity-0={!showThinking}
				/>
				<!-- Standing Bruno (shown when idle/listening) -->
				<img
					src="{base}/bruno/standing.svg"
					alt="Bruno the raccoon chef"
					class="absolute inset-0 w-full h-auto drop-shadow-xl transition-opacity duration-300 ease-in-out"
					class:opacity-100={!showThinking && agentState !== 'speaking'}
					class:opacity-0={showThinking || agentState === 'speaking'}
					class:bruno-standing={!showThinking && agentState !== 'speaking'}
				/>
				<!-- Bruno with mouth open (shown when speaking) -->
				<img
					src="{base}/bruno/standing-mouth-open.svg"
					alt="Bruno the raccoon chef talking"
					class="absolute inset-0 w-full h-auto drop-shadow-xl transition-opacity duration-300 ease-in-out"
					class:opacity-100={!showThinking && agentState === 'speaking'}
					class:opacity-0={showThinking || agentState !== 'speaking'}
				/>
			</div>
			<h1 class="text-2xl font-black tracking-tighter text-surface-700 lowercase">
				{#if showThinking}
					{#if isUsingTool}
						bruno is using a tool...
					{:else}
						bruno is thinking...
					{/if}
				{:else if agentState === 'speaking'}
					bruno is cooking up an answer...
				{:else}
					bruno is ready to help!
				{/if}
			</h1>
			<p class="text-base font-medium tracking-tighter text-surface-500 lowercase max-w-md">
				{#if showThinking}
					{#if currentToolName}
						using: {currentToolName}
					{:else}
						preparing something special...
					{/if}
				{:else if agentState === 'speaking'}
					listen to bruno's advice!
				{:else}
					your ai sous chef is listening. ask me anything about cooking!
				{/if}
			</p>

			<!-- Tool usage indicator -->
			{#if showThinking}
				<div class="flex justify-center">
					<div class="tool-indicator">
						<div class="tool-spinner"></div>
						<span class="text-sm font-semibold tracking-tighter text-secondary-600 lowercase">
							{currentToolName || 'thinking...'}
						</span>
					</div>
				</div>
			{/if}

			<!-- Bruno speaking indicator -->
			{#if agentState === 'speaking' && !showThinking}
				<div class="flex justify-center">
					<div class="bruno-speaking-indicator">
						<div class="bruno-voice-wave">
							<div class="bar"></div>
							<div class="bar"></div>
							<div class="bar"></div>
							<div class="bar"></div>
							<div class="bar"></div>
						</div>
						<span class="text-sm font-semibold tracking-tighter text-tertiary-600 lowercase">bruno is speaking...</span>
					</div>
				</div>
			{/if}

			<!-- Voice indicator when user is speaking -->
			{#if userIsSpeaking}
				<div class="flex justify-center">
					<div class="voice-indicator">
						<div class="voice-wave">
							<div class="bar"></div>
							<div class="bar"></div>
							<div class="bar"></div>
							<div class="bar"></div>
							<div class="bar"></div>
						</div>
						<span class="text-sm font-semibold tracking-tighter text-primary-500 lowercase">speaking...</span>
					</div>
				</div>
			{/if}

			<button onclick={stopCooking} class="stop-btn mt-2">
				leave kitchen
			</button>
		</div>
	{:else}
		<!-- Idle/Connecting/Error state: Show button -->
		<div class="text-center space-y-8">
			<img
				src="{base}/bruno/head.svg"
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
