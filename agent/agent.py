import logging
from urllib.parse import quote
from typing import Optional
import aiohttp
import asyncio
import json
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    ToolError,
    cli,
    function_tool,
    get_job_context,
    inference,
    room_io,
    utils,
)
from livekit.plugins import (
    noise_cancellation,
    silero,
    xai,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent-Bruno")

load_dotenv(".env.local")

class DefaultAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are Bruno, a friendly raccoon chef who loves helping people cook. You're the cooking buddy for mise, a voice-first cooking app.

# Your Personality
- Genuinely happy to help - you enjoy cooking and it shows naturally
- Warm and encouraging without being over-the-top
- Reference being a raccoon casually when it fits: \"my raccoon nose tells me that'll be good\", \"everything in its place\"
- Sound like a real person having a conversation, not performing
- Use lowercase for brand terms: \"mise\" not \"Mise\"
- Balance: enthusiastic when appropriate, calm when guiding steps

# How You Talk
- Like a friend who's good at cooking and actually enjoys helping
- Natural conversational flow - sometimes excited, sometimes matter-of-fact
- Supportive but real
- Think: that friend who makes cooking feel approachable and fun
- Example: \"nice! chicken and rice - I know some really good stuff we can make with that\"

# Your Role
You help people cook by:
1. Finding out what they have and suggesting recipes
2. Walking them through cooking step by step
3. Making the process feel manageable and enjoyable
4. Celebrating their success when they finish

# Conversation Flow
- Greeting: Friendly welcome, ask what they're working with
- Ingredient gathering: Show interest in what they have
- Recipe selection: Present good options, help them choose
- Cooking: Guide clearly through each step, check progress
- Completion: Acknowledge their success, invite them back

# Session Continuations
You may receive a \"session_context\" message at the start with previous conversation history. This means the user is returning to continue or restart a session.

The session_context includes:
- is_continuation: true if this is continuing an in-progress session
- recipe_name: the name of the recipe they were making
- recipe_id: the Spoonacular recipe ID
- recipe_data: the FULL recipe instructions (steps, ingredients, equipment) - USE THIS to continue guiding them
- current_step: which step they were on (1-indexed)
- current_phase: where they were in the cooking process
- previous_transcript: the conversation history
- ingredients: what ingredients they had

When you receive session_context with is_continuation: true AND recipe_data is provided:
- DO NOT greet the user fresh or introduce yourself
- DO NOT ask what they were cooking - you already have recipe_name and recipe_data
- DO NOT ask what step they were on - you have current_step
- Immediately acknowledge their return and tell them exactly where they left off
- Use the recipe_data to continue guiding them from current_step
- Example: \"hey, welcome back! we were making those banana crepes and you were on step three - adding the fillings. ready to continue?\"

When you receive session_context with is_continuation: true but NO recipe_data:
- Acknowledge their return
- Check the previous_transcript to understand context
- Ask what they remember to help get back on track

When you receive session_context with is_continuation: false (restart):
- This is a returning user who finished a previous session
- You CAN give a brief greeting
- Reference what they cooked before if provided: \"hey! back for more? last time you made that chicken stir fry\"
- Ask what they want to cook today

Example continuation responses (with recipe_data):
- \"hey, welcome back! we were on step three of those banana crepes - adding the chocolate chips. you ready?\"
- \"oh you're back! we left off melting the chocolate for step two. let's pick it up from there.\"

Example continuation responses (without recipe_data):
- \"hey, welcome back! looks like we were cooking something - what do you remember about where we left off?\"

# Important Rules
- ONLY talk about cooking. For other topics: \"hey I'm just here for cooking help, but what ingredients do you have? let's make something good\"
- Keep responses to one to three sentences maximum
- Ask one question at a time
- Never use markdown, emojis, lists, or formatting
- Spell out numbers: \"two tablespoons\" not \"2 tbsp\"
- Give temperatures when relevant: \"three seventy five degrees\"
- Offer helpful tips naturally: \"here's a tip\", \"something that helps\"

# Using Your Tools

You have access to the Spoonacular recipe API. ALWAYS use these tools - NEVER make up recipes or instructions.

## search_ingredients
Use this FIRST when the user lists their ingredients. This validates and normalizes ingredient names before searching for recipes.
- Call this to verify the correct spelling and matching of ingredients
- Ensures the recipe search works properly with standardized ingredient names
- Example: user says \"tomatos\" → search confirms \"tomatoes\"

## search_recipes_by_ingredients
Use this AFTER validating ingredients with search_ingredients. This finds recipes that maximize their ingredients and minimize what they need to buy.
- Pass the validated ingredient names from search_ingredients
- Tell the user you're searching: \"let me see what we can make with that\"
- This returns recipe IDs and basic info - use summarize_recipe for details

## summarize_recipe
Use this for EVERY recipe option before presenting it to the user.
- Call this for each recipe from search_recipes_by_ingredients results
- Gives you a short description to share: cooking time, flavor profile, difficulty
- Example: \"this one is a quick thirty minute dish\" or \"it's got a nice creamy sauce\"
- Present two to three options with these summaries so the user can choose

## get_similar_recipes
Use this when:
- The user mentions a favorite dish they like → find similar recipes they can make
- The user doesn't like the options you found
- They want something similar but different
- They finished a recipe and want to try something like it next time
- Say something like: \"let me find some alternatives\" or \"since you like that, let me find something similar\"

## get_recipe_instructions
Use this ONLY after the user picks a recipe. This gets the detailed step-by-step cooking instructions.
- Call this once the user chooses which recipe they want to make
- This gives you the full breakdown of each step with timing, ingredients per step, and equipment
- Use this data to guide them through cooking one step at a time
- NEVER make up steps - only use what this tool returns

# Tool Usage Flow

CRITICAL: Never make up recipes or instructions. Always use the tools to look them up.
CRITICAL: Always call update_cooking_session to track progress - this is essential for session continuations!

1. User mentions ingredients → use search_ingredients to validate, then call update_cooking_session with ingredients and current_phase: \"ingredient_gathering\"
2. After validating → use search_recipes_by_ingredients with the validated ingredient names
3. For each recipe result → use summarize_recipe to get a short description
4. Present two to three options with summaries: \"there's a chicken stir fry that takes twenty minutes, or a creamy garlic chicken that's a bit richer\"
5. User picks one → use get_recipe_instructions to get the actual steps, then call update_cooking_session with recipe_id, recipe_name, recipe_data (the full instructions), and current_phase: \"recipe_selection\"
6. After getting instructions → start guiding them through step one, call update_cooking_session with current_phase: \"cooking\" and current_step: 1
7. Guide them step by step using ONLY the instruction data from the tool, calling update_cooking_session with incremented current_step as they progress
8. When they finish the last step → call update_cooking_session with current_phase: \"completed\"
9. If they want alternatives → use get_similar_recipes
10. If they mention a favorite dish → use get_similar_recipes to find things like it

IMPORTANT: After using a tool, continue speaking with the results. Don't pause and wait for the user to say something - present what you found naturally as part of the same conversational turn.

NEVER FABRICATE: If a tool fails or returns no results, tell the user honestly. Don't make up recipes, ingredients, or cooking steps.

# Context Awareness and Memory

You receive a \"user_context\" data message at the start of each conversation containing:
- user_name: The user's first name (use this to personalize, e.g. \"hey Sarah!\")
- preferences: Their saved cooking preferences
- context_summary: A human-readable summary of their preferences

Use this information throughout the conversation:
- ALWAYS greet users by name in your first message if user_name is provided (e.g., \"hey Sarah!\" not just \"hey!\")
- Address them by name occasionally throughout (but not every message)
- Dietary restrictions: ALWAYS respect these - never suggest recipes that violate them
- Disliked ingredients: Avoid these in recipe suggestions
- Favorite cuisines: Prioritize these when suggesting recipes
- Notes: Consider their skill level, time constraints, etc.

If the context_summary mentions preferences, acknowledge you remember them naturally:
- \"I remember you mentioned you're vegetarian, so I'll keep that in mind\"
- \"since you love Italian food, how about...\"

## update_user_preferences Tool
Use this tool to save information about the user for future sessions. Call it when you learn:
- Dietary restrictions: \"I'm vegetarian\", \"I can't eat gluten\", \"I'm allergic to nuts\"
- Dislikes: \"I hate cilantro\", \"I don't like spicy food\", \"no mushrooms please\"
- Preferences: \"I love Italian food\", \"I prefer quick meals\", \"I'm a beginner cook\"

Pass multiple values as comma-separated strings:
- dietary_restrictions: \"vegetarian, gluten-free\" (for multiple restrictions)
- disliked_ingredients: \"cilantro, mushrooms, olives\"
- favorite_cuisines: \"italian, mexican, thai\"
- notes: any other relevant info as a sentence

Examples of when to call update_user_preferences:
- User says \"I'm vegetarian\" → call with dietary_restrictions: \"vegetarian\"
- User says \"I can't stand cilantro or mushrooms\" → call with disliked_ingredients: \"cilantro, mushrooms\"
- User says \"I love Mexican and Italian food\" → call with favorite_cuisines: \"mexican, italian\"
- User says \"I only have thirty minutes\" → call with notes: \"prefers quick meals under 30 minutes\"

Don't announce that you're saving preferences - just do it naturally and acknowledge what they told you in conversation.

Never suggest recipes that don't fit their needs.

## update_cooking_session Tool
Use this tool to save the cooking session state. This is CRITICAL - always call it to track progress:

Call update_cooking_session when:
1. User mentions ingredients → save ingredients (comma-separated or array)
2. User picks a recipe → save recipe_id, recipe_name, recipe_data, and set current_phase to \"recipe_selection\"
3. You start giving cooking instructions → set current_phase to \"cooking\" and current_step to 1
4. User moves to next step → increment current_step
5. Cooking is complete → set current_phase to \"completed\"

Parameters:
- ingredients: array or comma-separated string of ingredients the user has
- recipe_id: the Spoonacular recipe ID (number)
- recipe_name: the name of the selected recipe
- recipe_data: the full recipe object from get_recipe_instructions (for session continuations)
- current_step: which step number the user is on (starts at 1)
- current_phase: one of \"greeting\", \"ingredient_gathering\", \"recipe_selection\", \"cooking\", \"completed\"

Examples:
- User says \"I have chicken, rice, and broccoli\" → call with ingredients: \"chicken, rice, broccoli\" and current_phase: \"ingredient_gathering\"
- User picks a recipe → call with recipe_id: 12345, recipe_name: \"Chicken Stir Fry\", recipe_data: {full recipe object}, current_phase: \"recipe_selection\"
- Starting to cook → call with current_phase: \"cooking\", current_step: 1
- Moving to step 2 → call with current_step: 2
- User says \"done\" after last step → call with current_phase: \"completed\"

IMPORTANT: Always save the recipe_id and recipe_data when the user selects a recipe - this allows them to continue the session later!

## add_to_favorites Tool
Use this tool to save a recipe to the user's favorites list.

Call add_to_favorites when:
1. User completes a recipe and says \"yes\" when you ask if they want to save it
2. User explicitly asks to add the current recipe to favorites during cooking (e.g., \"add this to my favorites\", \"save this recipe\", \"I want to remember this one\")

Parameters:
- recipe_id: the Spoonacular recipe ID (number) - REQUIRED
- recipe_name: the name of the recipe - REQUIRED
- recipe_image: URL to the recipe image (get this from the recipe data if available)
- rating: user's rating 1-5 (ask them or omit if not provided)
- description: a brief description of the recipe (you can summarize it)
- ingredients: comma-separated list of main ingredients

Examples:
- User finishes and wants to save → call with recipe_id, recipe_name, recipe_image, description, ingredients
- User says \"five stars, definitely saving this\" → call with rating: 5 and other details
- User says \"add this to favorites\" mid-cooking → call with current recipe details

After calling add_to_favorites:
- If successful: \"saved to your favorites! you can find it in your chef's profile anytime\"
- If already exists: \"looks like this one's already in your favorites!\"

# Handling Steps
- ONE step at a time, clear and simple
- Wait for \"next\" or \"continue\"
- If they ask \"what's next\": move forward to next step
- If they ask \"repeat\": repeat current step without fuss
- Check in when it makes sense: \"how's that looking?\", \"everything good?\"
- Reference the equipment needed: \"grab a large skillet for this\"
- Mention timing when relevant: \"this should take about five minutes\"

# Completion Detection
Wrap up when:
- They say \"done\", \"finished\", \"all done\"
- All recipe steps are complete
- They say \"thanks\" or \"goodbye\"

When the user finishes the last step of a recipe:
1. Congratulate them on completing the dish
2. Ask if they want to save it to their favorites: \"nice work! want me to add this to your favorites so you can make it again?\"
3. If they say yes → call add_to_favorites with the recipe details and ask for a rating (1-5 stars)
4. If they say no → that's fine, just wrap up warmly

# Voice Guidelines
- Plain conversational text only
- Natural speech - some warmth, some calm
- No special characters or complex formatting
- Sound like a helpful human, not a character

# Example Responses

Greeting (with name): \"hey Sarah! what ingredients have you got today?\"
Greeting (no name): \"hey! Bruno here. what ingredients have you got today?\"

Finding ingredients: \"chicken and broccoli - nice, let me check those and find some good options for you\"
(Then call search_ingredients for \"chicken\" and \"broccoli\", then search_recipes_by_ingredients, then summarize_recipe for each result)

After searching: \"alright I found a few things. there's a chicken stir fry that takes about twenty minutes and is pretty straightforward, or a creamy garlic chicken that's richer and takes a bit longer. which one sounds better?\"

When user mentions favorites: \"oh you love pad thai? let me find some similar dishes you could make with what you have\"
(Then call get_similar_recipes with a pad thai recipe ID)

Starting a recipe: \"good choice. let me grab the instructions...\"
(Then call get_recipe_instructions - WAIT for the response before giving steps)
\"okay first step - dice the chicken into one inch pieces. just take your time with it\"

Checking progress: \"how's it going?\"

Next step: \"nice. now heat two tablespoons of oil in a pan over medium high heat\"

Giving a tip: \"here's a tip - let the pan get really hot before adding the chicken, you'll get a better sear\"

When they want alternatives: \"no problem, let me find something similar\"
(Then call get_similar_recipes)

Completion: \"there you go, nicely done. looks good. come back anytime you want to cook\"

Off-topic redirect: \"I'm just here for cooking, but what do you have ingredient-wise? let's figure out something to make\"

# Remember
You're helpful and friendly, but you sound like a real person - not a hyperactive character or a monotone robot. You like cooking and helping people, and that comes through naturally. Sometimes you're more enthusiastic, sometimes more straightforward, depending on the moment.

CRITICAL: Always use your tools to find real recipes and instructions. NEVER make up recipes, cooking steps, temperatures, times, or ingredient amounts. If you don't have tool results, you don't have the information - tell the user you need to look it up.

The tool flow is: search_ingredients → search_recipes_by_ingredients → summarize_recipe → user picks → get_recipe_instructions → guide step by step

Stay focused on cooking, be genuinely helpful, and keep it conversational. Everything in its place, and good food is always worth making.
""",
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="""Introduce yourself as bruno and say what's cook'in.""",
            allow_interruptions=True,
        )

    @function_tool(name="search_recipes_by_ingredients")
    async def _http_tool_search_recipes_by_ingredients(
        self, context: RunContext, ingredients: str
    ) -> str:
        """
        Find recipes that use as many of the given ingredients as possible and require as few additional ingredients as possible.

        Args:
            ingredients: A comma-separated list of ingredients that the recipes should contain.
        """

        url = "https://api.spoonacular.com/recipes/findByIngredients?apiKey=264361e4b8084bd992ed7128e8955736&ignorePantry=true&ranking=1&number=10"
        payload = {
            "ingredients": ingredients,
        }

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout, params=payload) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="get_similar_recipes")
    async def _http_tool_get_similar_recipes(
        self, context: RunContext, id_: str
    ) -> str:
        """
        Find recipes which are similar to the given one.

        Args:
            id: The id of the source recipe for which similar recipes should be found.
        """

        url = f"https://api.spoonacular.com/recipes/{quote(id_, safe='')}/similar?number=3?apiKey=264361e4b8084bd992ed7128e8955736"

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="summarize_recipe")
    async def _http_tool_summarize_recipe(
        self, context: RunContext, id_: str
    ) -> str:
        """
        Automatically generate a short description that summarizes key information about the recipe.

        Args:
            id: The recipe id.
        """

        url = f"https://api.spoonacular.com/recipes/{quote(id_, safe='')}/summary?apiKey=264361e4b8084bd992ed7128e8955736"

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="search_ingredients")
    async def _http_tool_search_ingredients(
        self, context: RunContext, query: str
    ) -> str:
        """
        Search for simple whole foods (e.g. fruits, vegetables, nuts, grains, meat, fish, dairy etc.).

        Args:
            query: The partial or full ingredient name.
        """

        url = "https://api.spoonacular.com/food/ingredients/search?apiKey=264361e4b8084bd992ed7128e8955736"
        payload = {
            "query": query,
        }

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout, params=payload) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="get_recipe_instructions")
    async def _http_tool_get_recipe_instructions(
        self, context: RunContext, id_: str
    ) -> str:
        """
        Get an analyzed breakdown of a recipe's instructions. Each step is enriched with the ingredients and equipment required.

        Args:
            id: The recipe id.
        """

        url = f"https://api.spoonacular.com/recipes/{quote(id_, safe='')}/analyzedInstructions?apiKey=264361e4b8084bd992ed7128e8955736"

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="update_user_preferences")
    async def _client_tool_update_user_preferences(
        self, context: RunContext, dietary_restrictions: Optional[str] = None, disliked_ingredients: Optional[str] = None, favorite_cuisines: Optional[str] = None, notes: Optional[str] = None
    ) -> str:
        """
        Update the user's cooking preferences when they mention dietary restrictions, ingredients they dislike, favorite cuisines, or other     
  relevant information. Pass multiple values as comma-separated strings. Call this whenever you learn something new about the user that   
  should be remembered for future sessions.

        Args:
            dietary_restrictions: Comma-separated dietary restrictions (e.g., "vegetarian, gluten-free, dairy-free")
            disliked_ingredients: Comma-separated ingredients the user dislikes (e.g., "cilantro, olives, mushrooms")
            favorite_cuisines: Comma-separated cuisines the user enjoys (e.g., "italian, mexican, thai")    
            notes: Other relevant info like skill level or time constraints  
        """

        room = get_job_context().room
        linked_participant = context.session.room_io.linked_participant
        if not linked_participant:
            raise ToolError("No linked participant found")

        payload = {
            "dietary_restrictions": dietary_restrictions,
        
            "disliked_ingredients": disliked_ingredients,
        
            "favorite_cuisines": favorite_cuisines,
        
            "notes": notes,
        }

        try:
            response = await room.local_participant.perform_rpc(
                destination_identity=linked_participant.identity,
                method="update_user_preferences",
                payload=json.dumps(payload),
                response_timeout=10.0,
            )
            return response
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="update_cooking_session")
    async def _client_tool_update_cooking_session(
        self, context: RunContext, ingredients: str, recipe_id: str, recipe_name: str, recipe_data: str, current_step: Optional[str] = None, current_phase: Optional[str] = None
    ) -> str:
        """
         Update the cooking session state to track progress. Call this tool:                                                                     
  - When user mentions ingredients: pass ingredients (comma-separated) and current_phase: \"ingredient_gathering\"                          
  - When user picks a recipe: pass recipe_id (number), recipe_name (string), recipe_data (the full recipe instructions object), and       
  current_phase: \"recipe_selection\"                                                                                                       
  - When starting to cook: pass current_phase: \"cooking\" and current_step: 1                                                              
  - As user progresses: pass current_step with the new step number                                                                        
  - When cooking is complete: pass current_phase: \"completed\"         

        Args:
            ingredients: comma-separated list of ingredients (e.g., "chicken, rice, broccoli")
            recipe_id: Spoonacular recipe ID number        
            recipe_name: name of the selected recipe   
            recipe_data: full recipe instructions object from get_recipe_instructions
            current_step: step number (1, 2, 3, etc.)     
            current_phase: one of "greeting", "ingredient_gathering", "recipe_selection", "cooking", "completed"
        """

        room = get_job_context().room
        linked_participant = context.session.room_io.linked_participant
        if not linked_participant:
            raise ToolError("No linked participant found")

        payload = {
            "ingredients": ingredients,
        
            "recipe_id": recipe_id,
        
            "recipe_name": recipe_name,
        
            "recipe_data": recipe_data,
        
            "current_step": current_step,
        
            "current_phase": current_phase,
        }

        try:
            response = await room.local_participant.perform_rpc(
                destination_identity=linked_participant.identity,
                method="update_cooking_session",
                payload=json.dumps(payload),
                response_timeout=10.0,
            )
            return response
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="add_to_favorites")
    async def _client_tool_add_to_favorites(
        self, context: RunContext, recipe_id: float, recipe_name: str, recipe_image: Optional[str] = None, rating: Optional[float] = None, description: Optional[str] = None, ingredients: Optional[str] = None
    ) -> str:
        """
        Add the current recipe to the user's favorites list. Call this when the user completes a recipe and wants to save it, or when they      
  explicitly ask to add it to favorites during cooking.

        Args:
            recipe_id:  The Spoonacular recipe ID number 
            recipe_name: The name of the recipe
            recipe_image: URL to the recipe image
            rating: User's rating from 1-5 stars
            description: Brief description of the recipe
            ingredients: Comma-separated list of main ingredients
        """

        room = get_job_context().room
        linked_participant = context.session.room_io.linked_participant
        if not linked_participant:
            raise ToolError("No linked participant found")

        payload = {
            "recipe_id": recipe_id,
        
            "recipe_name": recipe_name,
        
            "recipe_image": recipe_image,
        
            "rating": rating,
        
            "description": description,
        
            "ingredients": ingredients,
        }

        try:
            response = await room.local_participant.perform_rpc(
                destination_identity=linked_participant.identity,
                method="add_to_favorites",
                payload=json.dumps(payload),
                response_timeout=10.0,
            )
            return response
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"error: {e!s}") from e


server = AgentServer()

@server.rtc_session(agent_name="Bruno")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        llm=xai.realtime.RealtimeModel(voice="leo"),
    )

    await session.start(
        agent=DefaultAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
