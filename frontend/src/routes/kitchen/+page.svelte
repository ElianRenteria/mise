<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { pb, type CookingSession, type TranscriptMessage, type UserPreferences } from '$lib/pocketbase';
	import { Room, RoomEvent, ConnectionState, TokenSource, Track, ParticipantKind, type RemoteTrack, type RemoteTrackPublication, type RemoteParticipant, type Participant, type TranscriptionSegment } from 'livekit-client';
	import { onDestroy, onMount } from 'svelte';
	import SessionSidebar from '$lib/components/SessionSidebar.svelte';
	import TranscriptView from '$lib/components/TranscriptView.svelte';

	// Auth check and initial data load
	onMount(async () => {
		// Redirect to login if not authenticated
		if (!pb.authStore.isValid || !pb.authStore.record) {
			goto(`${base}/`);
			return;
		}
		// Load user preferences on mount
		userPreferences = await loadUserPreferences();
	});

	// Sidebar state
	let sidebarOpen: boolean = $state(false);

	// Connection state
	let connectionState: 'idle' | 'connecting' | 'connected' | 'error' = $state('idle');
	let errorMessage: string = $state('');

	// Session tracking
	let currentSessionId: string | null = $state(null);
	let transcript: TranscriptMessage[] = $state([]);

	// Viewing past session transcript
	let viewingSession: CookingSession | null = $state(null);

	// Session continuation
	let continuingSession: CookingSession | null = $state(null);

	// User preferences (AI-managed)
	let userPreferences: UserPreferences | null = $state(null);
	let userPreferencesId: string | null = $state(null);
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

	// Cooking mode - true when Bruno is giving recipe instructions
	let isInCookingMode: boolean = $state(false);

	// Show thinking state with minimum duration
	let showThinking: boolean = $state(false);
	let thinkingStartTime: number = $state(0);
	let thinkingTimeout: ReturnType<typeof setTimeout> | null = null;
	const MINIMUM_THINKING_DURATION = 2500; // Show thinking for at least 2.5 seconds

	// Keep thinking state visible for minimum duration
	$effect(() => {
		const isThinkingNow = agentState === 'thinking' || isUsingTool;

		if (isThinkingNow && !showThinking) {
			// Start showing thinking
			showThinking = true;
			thinkingStartTime = Date.now();
			if (thinkingTimeout) {
				clearTimeout(thinkingTimeout);
				thinkingTimeout = null;
			}
		} else if (!isThinkingNow && showThinking) {
			// Agent stopped thinking, but enforce minimum duration
			const elapsed = Date.now() - thinkingStartTime;
			const remaining = MINIMUM_THINKING_DURATION - elapsed;

			if (remaining > 0) {
				// Wait for minimum duration before hiding
				if (!thinkingTimeout) {
					thinkingTimeout = setTimeout(() => {
						// Only hide if still not thinking and not speaking
						if (agentState !== 'thinking' && !isUsingTool) {
							showThinking = false;
						}
						thinkingTimeout = null;
					}, remaining);
				}
			} else {
				// Minimum duration passed, hide immediately
				showThinking = false;
			}
		}

		return () => {
			if (thinkingTimeout) {
				clearTimeout(thinkingTimeout);
				thinkingTimeout = null;
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

			// Log all agent attributes for debugging
			console.log('Agent attributes:', participant.attributes);
			console.log('Changed attributes:', changedAttributes);

			// Check for tool usage - agents report this via various attributes
			// Try multiple possible attribute names
			const toolCall = participant.attributes['lk.agent.llm.tool_call']
				|| participant.attributes['lk.agent.tool_call']
				|| participant.attributes['tool_call']
				|| changedAttributes['lk.agent.llm.tool_call']
				|| changedAttributes['lk.agent.tool_call']
				|| changedAttributes['tool_call'];

			if (toolCall) {
				try {
					const toolData = JSON.parse(toolCall);
					isUsingTool = true;
					// Try multiple possible property names for tool name
					currentToolName = toolData.name || toolData.tool || toolData.function?.name || toolData.tool_name || 'tool';
					console.log('Agent using tool:', currentToolName, toolData);

					// Enter cooking mode when recipe instructions are fetched
					if (currentToolName === 'get_recipe_instructions') {
						isInCookingMode = true;
						console.log('Entering cooking mode - Bruno will give instructions');
					}
				} catch {
					// Tool call might be a simple string
					isUsingTool = true;
					currentToolName = toolCall;
					console.log('Agent using tool (string):', currentToolName);

					// Check string tool name for cooking mode
					if (toolCall === 'get_recipe_instructions') {
						isInCookingMode = true;
						console.log('Entering cooking mode - Bruno will give instructions');
					}
				}
			} else if (changedAttributes['lk.agent.llm.tool_call'] === ''
				|| changedAttributes['lk.agent.tool_call'] === ''
				|| changedAttributes['tool_call'] === '') {
				// Tool call cleared
				isUsingTool = false;
				currentToolName = '';
			}

			// When agent is thinking, show that we're processing even if no specific tool
			if (state === 'thinking' && !isUsingTool) {
				// Agent is thinking but no tool call detected - still show thinking state
				console.log('Agent thinking (no tool detected)');
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

	// Session management functions
	async function createSession(): Promise<string | null> {
		const userId = pb.authStore.record?.id;
		if (!userId) {
			console.error('Cannot create session: No user ID');
			return null;
		}

		try {
			console.log('Creating session for user:', userId);

			// Create session with minimal required fields
			// status must be: in_progress, completed, or abandoned
			const sessionData = {
				user: userId,
				status: 'in_progress'
			};

			console.log('Session data:', sessionData);
			const session = await pb.collection('cooking_sessions').create<CookingSession>(sessionData);
			console.log('Session created successfully:', session.id);
			return session.id;
		} catch (err: unknown) {
			const errorObj = err as { status?: number; message?: string; data?: Record<string, { message: string }> };
			console.error('Failed to create session:', {
				status: errorObj.status,
				message: errorObj.message,
				data: errorObj.data
			});

			// Log specific field errors
			if (errorObj.data) {
				Object.entries(errorObj.data).forEach(([field, error]) => {
					console.error(`Field "${field}": ${error.message}`);
				});
			}

			errorMessage = 'Failed to save session. Check console for details.';
			return null;
		}
	}

	// Debounce timer for transcript updates
	let transcriptUpdateTimer: ReturnType<typeof setTimeout> | null = null;
	const TRANSCRIPT_UPDATE_INTERVAL = 3000; // Update every 3 seconds

	async function updateSessionTranscript() {
		if (!currentSessionId || transcript.length === 0) return;

		const sessionId = currentSessionId; // Capture current value
		const transcriptCopy = [...transcript]; // Copy to avoid race conditions

		try {
			console.log('Updating transcript for session:', sessionId, 'messages:', transcriptCopy.length);
			await pb.collection('cooking_sessions').update(sessionId, {
				transcript: transcriptCopy
			});
			console.log('Transcript updated successfully');
		} catch (err: unknown) {
			const errorObj = err as { status?: number; message?: string; data?: Record<string, { message: string }>; response?: { data?: Record<string, { message: string }> } };
			console.error('Failed to update transcript:', err);
			console.error('Error status:', errorObj.status);
			console.error('Error data:', errorObj.data || errorObj.response?.data);

			// If it's a validation error, log the full error
			if (errorObj.status === 400) {
				console.error('Full error object:', JSON.stringify(err, null, 2));
			}
		}
	}

	function scheduleTranscriptUpdate() {
		// Clear any pending update
		if (transcriptUpdateTimer) {
			clearTimeout(transcriptUpdateTimer);
		}
		// Schedule a new update
		transcriptUpdateTimer = setTimeout(() => {
			updateSessionTranscript();
			transcriptUpdateTimer = null;
		}, TRANSCRIPT_UPDATE_INTERVAL);
	}

	async function completeSession(status: 'completed' | 'abandoned' = 'completed') {
		if (!currentSessionId) return;

		// Cancel any pending transcript update
		if (transcriptUpdateTimer) {
			clearTimeout(transcriptUpdateTimer);
			transcriptUpdateTimer = null;
		}

		const sessionId = currentSessionId;
		const finalTranscript = [...transcript];

		try {
			console.log('Completing session:', sessionId, 'status:', status, 'messages:', finalTranscript.length);
			await pb.collection('cooking_sessions').update(sessionId, {
				status: status,
				transcript: finalTranscript
			});
			console.log('Session completed:', sessionId);
		} catch (err: unknown) {
			const errorObj = err as { status?: number; message?: string; data?: Record<string, { message: string }>; response?: { data?: Record<string, { message: string }> } };
			console.error('Failed to complete session:', err);
			console.error('Error status:', errorObj.status);
			console.error('Error data:', errorObj.data || errorObj.response?.data);
		}

		currentSessionId = null;
		transcript = [];
	}

	// Phrases that indicate Bruno is giving cooking instructions
	const COOKING_INSTRUCTION_PHRASES = [
		'first step',
		'step one',
		'step two',
		'step three',
		'next step',
		'now you',
		'let\'s start',
		'okay first',
		'alright first',
		'go ahead and',
		'you\'ll want to',
		'you\'re going to',
		'start by',
		'begin by',
		'grab your',
		'take your',
		'heat the',
		'preheat',
		'chop the',
		'dice the',
		'slice the',
		'mix the',
		'stir the',
		'add the',
		'pour the',
		'let me walk you through',
		'here\'s what you do',
		'instructions'
	];

	// Phrases that indicate Bruno is confirming a recipe choice
	const RECIPE_CONFIRMATION_PHRASES = [
		'good choice',
		'great choice',
		'nice choice',
		'excellent choice',
		'perfect',
		'sounds good',
		'let\'s make',
		'let\'s do',
		'we\'re making',
		'we\'ll make',
		'going with',
		'let me grab the instructions'
	];

	function detectCookingMode(content: string): boolean {
		const lowerContent = content.toLowerCase();
		return COOKING_INSTRUCTION_PHRASES.some(phrase => lowerContent.includes(phrase));
	}

	function detectRecipeConfirmation(content: string): boolean {
		const lowerContent = content.toLowerCase();
		return RECIPE_CONFIRMATION_PHRASES.some(phrase => lowerContent.includes(phrase));
	}

	// Try to extract recipe name from Bruno's confirmation or recent transcript
	function extractRecipeName(content: string): string | null {
		const lowerContent = content.toLowerCase();

		// Pattern: "let's make [the] [recipe name]"
		let match = lowerContent.match(/let'?s (?:make|do) (?:the |a |some )?(.+?)(?:\.|,|!|\?|$)/);
		if (match && match[1] && match[1].length > 3 && match[1].length < 50) {
			return match[1].trim();
		}

		// Pattern: "we're making [the] [recipe name]"
		match = lowerContent.match(/we'?re making (?:the |a |some )?(.+?)(?:\.|,|!|\?|$)/);
		if (match && match[1] && match[1].length > 3 && match[1].length < 50) {
			return match[1].trim();
		}

		// Pattern: "[recipe name] it is"
		match = lowerContent.match(/(.+?) it is/);
		if (match && match[1] && match[1].length > 3 && match[1].length < 50) {
			return match[1].trim();
		}

		// Pattern: "good choice" - look for recipe name in recent user message
		if (lowerContent.includes('good choice') || lowerContent.includes('great choice')) {
			// Find the last user message that might contain recipe selection
			for (let i = transcript.length - 1; i >= 0; i--) {
				const msg = transcript[i];
				if (msg.role === 'user') {
					// User might have said just the recipe name or "the [recipe]" or "I'll have the [recipe]"
					const userContent = msg.content.toLowerCase().trim();
					// Skip very short responses like "yes", "ok", "that one"
					if (userContent.length > 5 && !['yes', 'yeah', 'ok', 'okay', 'sure', 'that one', 'the first', 'the second', 'first one', 'second one'].some(skip => userContent === skip)) {
						// Clean up common prefixes
						let recipeName = userContent
							.replace(/^(i'?ll |i'?d like |let'?s |i want |the |how about |i'?ll have |i'?ll take |give me )/i, '')
							.replace(/( please| sounds good| one)?$/i, '')
							.trim();
						if (recipeName.length > 3 && recipeName.length < 50) {
							return recipeName;
						}
					}
					break; // Only check the most recent user message
				}
			}
		}

		return null;
	}

	// Track if we've already set a recipe name for this session
	let hasSetRecipeName: boolean = $state(false);

	function addTranscriptMessage(role: 'user' | 'assistant', content: string) {
		if (!content.trim()) return;

		const isFirstUserMessage = role === 'user' && !transcript.some(m => m.role === 'user');

		transcript = [...transcript, {
			role,
			content,
			timestamp: new Date().toISOString()
		}];

		console.log('Added transcript message:', role, content.slice(0, 50) + '...');

		// Detect recipe confirmation and update session title
		if (role === 'assistant' && !hasSetRecipeName && detectRecipeConfirmation(content)) {
			const recipeName = extractRecipeName(content);
			if (recipeName && currentSessionId) {
				console.log('Recipe selected:', recipeName);
				updateSessionTitle(recipeName);
				hasSetRecipeName = true;
			}
		}

		// Detect cooking mode from Bruno's speech
		if (role === 'assistant' && !isInCookingMode && detectCookingMode(content)) {
			isInCookingMode = true;
			console.log('Entered cooking mode - Bruno is giving instructions');
		}

		// Schedule debounced transcript update
		scheduleTranscriptUpdate();

		// If this is the first user message and no recipe name yet, use it as fallback title
		if (isFirstUserMessage && currentSessionId && !hasSetRecipeName) {
			updateSessionTitle(content);
		}
	}

	// Update session title (uses recipe_name field)
	async function updateSessionTitle(title: string) {
		if (!currentSessionId) return;

		// Truncate to first 50 chars and clean up
		const cleanTitle = title
			.replace(/[^\w\s]/g, '')
			.trim()
			.slice(0, 50)
			.toLowerCase();

		if (!cleanTitle) return;

		try {
			await pb.collection('cooking_sessions').update(currentSessionId, {
				recipe_name: cleanTitle + (title.length > 50 ? '...' : '')
			});
			console.log('Session title updated:', cleanTitle);
		} catch (err) {
			console.error('Failed to update session title:', err);
		}
	}

	// Handle data messages for transcript, tool calls, and AI preference updates
	function handleDataReceived(
		payload: Uint8Array,
		participant?: RemoteParticipant
	) {
		try {
			const data = JSON.parse(new TextDecoder().decode(payload));
			console.log('Data received:', data);

			// Handle tool call notifications from agent
			if (data.type === 'tool_call' || data.type === 'function_call' || data.tool_call || data.function_call) {
				const toolName = data.name || data.tool || data.function || data.tool_call?.name || data.function_call?.name || 'tool';
				isUsingTool = true;
				currentToolName = toolName;
				console.log('Tool call from data channel:', toolName);

				// Enter cooking mode when recipe instructions are fetched
				if (toolName === 'get_recipe_instructions') {
					isInCookingMode = true;
					console.log('Entering cooking mode - Bruno will give instructions');
				}
			}

			// Handle tool call completion
			if (data.type === 'tool_result' || data.type === 'function_result' || data.tool_result) {
				// Tool finished, clear the tool state after a short delay
				setTimeout(() => {
					if (agentState !== 'thinking') {
						isUsingTool = false;
						currentToolName = '';
					}
				}, 500);
			}

			// Handle different message formats from LiveKit agents
			if (data.type === 'transcript' || data.transcript) {
				const text = data.transcript || data.text || data.content;
				const role = participant?.kind === ParticipantKind.AGENT ? 'assistant' : 'user';
				if (text) {
					addTranscriptMessage(role, text);
				}
			}

			// Handle AI preference updates (context awareness)
			if (data.type === 'update_preferences' || data.preferences_update) {
				const updates = data.preferences_update || data.updates || data;
				updateUserPreferences(updates);
			}

			// Handle client tool calls (RPC from agent)
			if (data.method === 'update_user_preferences' || data.tool === 'update_user_preferences') {
				const params = data.params || data.arguments || data;
				handleUpdatePreferencesTool(params, data.id);
			}
		} catch {
			// Not JSON data, ignore
		}
	}

	// Handle transcription received events from LiveKit (speech-to-text)
	function handleTranscription(
		segments: TranscriptionSegment[],
		participant?: Participant
	) {
		for (const segment of segments) {
			// Only process final transcriptions, not interim
			if (!segment.final) continue;

			const text = segment.text?.trim();
			if (!text) continue;

			// Determine if this is from the user or the agent
			const isAgent = participant?.kind === ParticipantKind.AGENT;
			const role: 'user' | 'assistant' = isAgent ? 'assistant' : 'user';

			console.log(`Transcription [${role}]:`, text);
			addTranscriptMessage(role, text);
		}
	}

	// Handle the update_user_preferences client tool call
	// Params come as comma-separated strings from the agent
	async function handleUpdatePreferencesTool(
		params: Record<string, string>,
		requestId?: string
	) {
		console.log('Client tool called: update_user_preferences', params);

		// Parse comma-separated strings into arrays
		const parsedPreferences: Partial<UserPreferences> = {};

		if (params.dietary_restrictions) {
			parsedPreferences.dietary_restrictions = params.dietary_restrictions
				.split(',')
				.map(s => s.trim().toLowerCase())
				.filter(s => s);
		}
		if (params.disliked_ingredients) {
			parsedPreferences.disliked_ingredients = params.disliked_ingredients
				.split(',')
				.map(s => s.trim().toLowerCase())
				.filter(s => s);
		}
		if (params.favorite_cuisines) {
			parsedPreferences.favorite_cuisines = params.favorite_cuisines
				.split(',')
				.map(s => s.trim().toLowerCase())
				.filter(s => s);
		}
		if (params.notes) {
			parsedPreferences.notes = params.notes.trim();
		}

		try {
			await updateUserPreferences(parsedPreferences);

			// Send success response back to agent if request ID provided
			if (requestId && room) {
				const response = {
					id: requestId,
					result: { success: true, message: 'Preferences updated successfully' }
				};
				const encoder = new TextEncoder();
				await room.localParticipant.publishData(
					encoder.encode(JSON.stringify(response)),
					{ reliable: true }
				);
			}
		} catch (err) {
			console.error('Failed to update preferences from tool:', err);

			// Send error response back to agent
			if (requestId && room) {
				const response = {
					id: requestId,
					error: { message: 'Failed to update preferences' }
				};
				const encoder = new TextEncoder();
				await room.localParticipant.publishData(
					encoder.encode(JSON.stringify(response)),
					{ reliable: true }
				);
			}
		}
	}

	// AI-managed preference updates
	async function updateUserPreferences(updates: Partial<UserPreferences>) {
		const userId = pb.authStore.record?.id;
		if (!userId) return;

		try {
			// Merge with existing preferences
			const newPreferences: Partial<UserPreferences> = {
				...userPreferences,
				...updates,
				user: userId
			};

			// Merge arrays instead of replacing
			if (updates.dietary_restrictions && userPreferences?.dietary_restrictions) {
				newPreferences.dietary_restrictions = [...new Set([
					...userPreferences.dietary_restrictions,
					...updates.dietary_restrictions
				])];
			}
			if (updates.disliked_ingredients && userPreferences?.disliked_ingredients) {
				newPreferences.disliked_ingredients = [...new Set([
					...userPreferences.disliked_ingredients,
					...updates.disliked_ingredients
				])];
			}
			if (updates.favorite_cuisines && userPreferences?.favorite_cuisines) {
				newPreferences.favorite_cuisines = [...new Set([
					...userPreferences.favorite_cuisines,
					...updates.favorite_cuisines
				])];
			}

			if (userPreferencesId) {
				// Update existing
				await pb.collection('user_preferences').update(userPreferencesId, newPreferences);
			} else {
				// Create new
				const created = await pb.collection('user_preferences').create(newPreferences);
				userPreferencesId = created.id;
			}

			// Update local state
			userPreferences = { ...userPreferences, ...newPreferences } as UserPreferences;
			console.log('AI updated preferences:', newPreferences);
		} catch (err) {
			console.error('Failed to update preferences:', err);
		}
	}

	// Load user preferences from PocketBase
	async function loadUserPreferences(): Promise<UserPreferences | null> {
		const userId = pb.authStore.record?.id;
		if (!userId) return null;

		try {
			const records = await pb.collection('user_preferences').getList<UserPreferences>(1, 1, {
				filter: `user = "${userId}"`
			});

			if (records.items.length > 0) {
				const prefs = records.items[0];
				userPreferencesId = prefs.id;
				return {
					id: prefs.id,
					user: prefs.user,
					dietary_restrictions: prefs.dietary_restrictions || [],
					disliked_ingredients: prefs.disliked_ingredients || [],
					favorite_cuisines: prefs.favorite_cuisines || [],
					notes: prefs.notes || '',
					created: prefs.created,
					updated: prefs.updated
				};
			}
		} catch (err) {
			console.error('Failed to load preferences:', err);
		}
		return null;
	}

	// Send preferences and context to the agent via data message
	async function sendPreferencesToAgent() {
		if (!room) return;

		const userId = pb.authStore.record?.id;
		const contextMessage = {
			type: 'user_context',
			user_id: userId,
			preferences: userPreferences || {
				dietary_restrictions: [],
				disliked_ingredients: [],
				favorite_cuisines: [],
				notes: ''
			}
		};

		try {
			const encoder = new TextEncoder();
			const data = encoder.encode(JSON.stringify(contextMessage));
			await room.localParticipant.publishData(data, { reliable: true });
			console.log('Sent user context to agent:', contextMessage);
		} catch (err) {
			console.error('Failed to send context:', err);
		}
	}

	// Replace with your LiveKit sandbox ID from cloud.livekit.io
	const SANDBOX_ID = 'mise-kitchen-1tqe7v';

	// View a past session's transcript
	function viewSession(session: CookingSession) {
		viewingSession = session;
	}

	// Continue an existing session
	function continueSession(session: CookingSession) {
		viewingSession = null; // Close the transcript view
		continuingSession = session;

		// Parse transcript if needed
		let loadedTranscript = session.transcript;
		if (typeof loadedTranscript === 'string') {
			try {
				loadedTranscript = JSON.parse(loadedTranscript);
			} catch {
				loadedTranscript = [];
			}
		}
		transcript = Array.isArray(loadedTranscript) ? loadedTranscript : [];

		// Use the existing session ID
		currentSessionId = session.id;

		// Reset states for the new connection
		isInCookingMode = false;
		hasSetRecipeName = true; // Don't overwrite the recipe name

		startCooking();
	}

	// Send session context to agent immediately after connecting
	async function sendSessionContext() {
		if (!room || !continuingSession) return;

		// Build a summary of the previous conversation for Bruno
		const transcriptSummary = transcript.map(m =>
			`${m.role === 'user' ? 'User' : 'Bruno'}: ${m.content}`
		).join('\n');

		const contextMessage = {
			type: 'session_context',
			is_continuation: true,
			previous_transcript: transcript,
			transcript_summary: transcriptSummary,
			recipe_name: continuingSession.recipe_name,
			recipe_id: continuingSession.selected_recipe_id,
			current_phase: continuingSession.current_phase,
			current_step: continuingSession.current_step
		};

		try {
			const encoder = new TextEncoder();
			const data = encoder.encode(JSON.stringify(contextMessage));
			await room.localParticipant.publishData(data, { reliable: true });
			console.log('Sent session context to agent for continuation');
		} catch (err) {
			console.error('Failed to send session context:', err);
		}
	}

	async function startCooking() {
		if (connectionState === 'connecting') return;

		connectionState = 'connecting';
		errorMessage = '';

		try {
			// Load user preferences first
			userPreferences = await loadUserPreferences();

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

			room.on(RoomEvent.Connected, async () => {
				console.log('Room connected!');
				connectionState = 'connected';

				if (continuingSession) {
					// Continuing an existing session - send context immediately
					console.log('Continuing session:', continuingSession.id);
					await sendSessionContext();

					// Update session status back to in_progress
					try {
						await pb.collection('cooking_sessions').update(continuingSession.id, {
							status: 'in_progress'
						});
					} catch (err) {
						console.error('Failed to update session status:', err);
					}
				} else {
					// Create a new cooking session
					console.log('Attempting to create session...');
				try {
					currentSessionId = await createSession();
					console.log('Session creation result:', currentSessionId);
				} catch (err) {
					console.error('Session creation threw error:', err);
				}
				}

				// Send user preferences to the agent after a short delay to ensure agent is ready
				setTimeout(async () => {
					await sendPreferencesToAgent();
				}, 1000);
			});

			room.on(RoomEvent.Disconnected, async () => {
				connectionState = 'idle';
				// Complete the session when disconnected
				await completeSession('completed');
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

			// Listen for data messages (transcript updates from agent)
			room.on(RoomEvent.DataReceived, handleDataReceived);

			// Listen for transcription from LiveKit (speech-to-text)
			room.on(RoomEvent.TranscriptionReceived, handleTranscription);

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
		// Complete the session before disconnecting
		await completeSession('completed');

		if (room) {
			await room.disconnect();
			room = null;
		}
		connectionState = 'idle';
		isInCookingMode = false;
		hasSetRecipeName = false;
		continuingSession = null;
	}

	async function handleLogout() {
		// Mark session as abandoned on logout
		await completeSession('abandoned');

		if (room) {
			await room.disconnect();
		}
		pb.authStore.clear();
		goto(`${base}/`);
	}

	function handleStartNew() {
		isInCookingMode = false;
		hasSetRecipeName = false;
		continuingSession = null;
		startCooking();
	}

	onDestroy(async () => {
		// Mark session as abandoned if user leaves without stopping
		if (currentSessionId) {
			await completeSession('abandoned');
		}
		if (room) {
			await room.disconnect();
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

<!-- Session Sidebar -->
<SessionSidebar
	bind:isOpen={sidebarOpen}
	onStartNew={handleStartNew}
	onViewSession={viewSession}
	currentSessionId={currentSessionId}
/>

<!-- Transcript View Modal -->
{#if viewingSession}
	<TranscriptView
		session={viewingSession}
		onClose={() => viewingSession = null}
		onContinue={continueSession}
	/>
{/if}

<!-- Hidden container for audio elements from the agent -->
<div bind:this={audioContainer} class="hidden"></div>

<div class="min-h-full flex flex-col items-center justify-center px-4 py-12 mise-gradient-bg relative">
	<!-- Menu Button -->
	<button
		onclick={() => sidebarOpen = true}
		class="absolute top-4 left-4 p-3 rounded-full bg-white/80 hover:bg-white shadow-lg transition-all z-30"
		aria-label="Open menu"
	>
		<svg class="w-6 h-6 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
		</svg>
	</button>
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
				<!-- Bruno with mouth open (shown when speaking, NOT in cooking mode) -->
				<img
					src="{base}/bruno/standing-mouth-open.svg"
					alt="Bruno the raccoon chef talking"
					class="absolute inset-0 w-full h-auto drop-shadow-xl transition-opacity duration-300 ease-in-out"
					class:opacity-100={!showThinking && agentState === 'speaking' && !isInCookingMode}
					class:opacity-0={showThinking || agentState !== 'speaking' || isInCookingMode}
				/>
				<!-- Winking Bruno with spatula (shown when speaking in cooking mode - giving instructions) -->
				<img
					src="{base}/bruno/winking-spatula.svg"
					alt="Bruno the raccoon chef giving cooking instructions"
					class="absolute inset-0 w-full h-auto drop-shadow-xl transition-opacity duration-300 ease-in-out"
					class:opacity-100={!showThinking && agentState === 'speaking' && isInCookingMode}
					class:opacity-0={showThinking || agentState !== 'speaking' || !isInCookingMode}
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
					{#if isInCookingMode}
						bruno is guiding you...
					{:else}
						bruno is cooking up an answer...
					{/if}
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
	{:else if connectionState === 'connecting'}
		<!-- Connecting state: Show loading skeleton -->
		<div class="text-center space-y-8 animate-pulse">
			<div class="w-32 h-32 mx-auto rounded-full bg-surface-200"></div>
			<div class="space-y-3">
				<div class="h-10 bg-surface-200 rounded-xl w-64 mx-auto"></div>
				<div class="h-5 bg-surface-100 rounded-lg w-80 mx-auto"></div>
			</div>
			<div class="flex flex-col items-center gap-4">
				<button
					disabled
					class="cooking-btn connecting"
				>
					<span class="spatula">🥄</span>
					<span class="loading-dots">heating up</span>
				</button>
				<p class="text-sm font-medium tracking-tighter text-surface-400 lowercase">
					connecting to bruno...
				</p>
			</div>
		</div>
	{:else}
		<!-- Idle/Error state: Show button -->
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
				onclick={() => startCooking()}
				class="cooking-btn"
			>
				<span class="spatula">🍳</span>
				start cooking
			</button>

			{#if connectionState === 'error'}
				<p class="text-sm font-medium text-error-500 lowercase max-w-md">
					{errorMessage || 'something went wrong. please try again.'}
				</p>
			{/if}
		</div>
	{/if}

</div>
