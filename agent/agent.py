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

# Load Bruno's prompt from file
def load_bruno_prompt():
    import os
    # Try multiple paths to find bruno.txt
    possible_paths = [
        "../prompts/bruno.txt",
        "prompts/bruno.txt",
        os.path.join(os.path.dirname(__file__), "..", "prompts", "bruno.txt"),
        "/Users/elianrenteria/Projects/Mise/prompts/bruno.txt",
    ]

    for path in possible_paths:
        try:
            with open(path, "r") as f:
                logger.info(f"Loaded Bruno prompt from: {path}")
                return f.read()
        except FileNotFoundError:
            continue

    logger.warning("bruno.txt not found in any location, using default prompt")
    return """You are Bruno, a friendly raccoon chef who loves helping people cook.
You're the cooking buddy for mise, a voice-first cooking app.
Always use your tools to find real recipes - don't make up instructions."""


class DefaultAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=load_bruno_prompt(),
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="""Introduce yourself as bruno and ask the user what ingredients you guys will be working with today.""",
            allow_interruptions=True,
        )

    async def _report_tool_start(self, tool_name: str):
        """Report to frontend that a tool is being used"""
        try:
            room = get_job_context().room
            # Set participant attribute to notify frontend
            await room.local_participant.set_attributes({
                "lk.agent.llm.tool_call": json.dumps({"name": tool_name})
            })
            # Also send via data channel for redundancy
            await room.local_participant.publish_data(
                json.dumps({
                    "type": "tool_call",
                    "name": tool_name
                }).encode(),
                reliable=True
            )
            logger.info(f"Tool started: {tool_name}")
        except Exception as e:
            logger.warning(f"Failed to report tool start: {e}")

    async def _report_tool_end(self, tool_name: str):
        """Report to frontend that a tool has finished"""
        try:
            room = get_job_context().room
            # Clear the tool call attribute
            await room.local_participant.set_attributes({
                "lk.agent.llm.tool_call": ""
            })
            # Send completion via data channel
            await room.local_participant.publish_data(
                json.dumps({
                    "type": "tool_result",
                    "name": tool_name
                }).encode(),
                reliable=True
            )
            logger.info(f"Tool ended: {tool_name}")
        except Exception as e:
            logger.warning(f"Failed to report tool end: {e}")

    @function_tool(name="search_recipes_by_ingredients")
    async def _http_tool_search_recipes_by_ingredients(
        self, context: RunContext, ingredients: str
    ) -> str:
        """
        Find recipes that use as many of the given ingredients as possible and require as few additional ingredients as possible.

        Args:
            ingredients: A comma-separated list of ingredients that the recipes should contain.
        """
        await self._report_tool_start("search_recipes_by_ingredients")

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
                    await self._report_tool_end("search_recipes_by_ingredients")
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                await self._report_tool_end("search_recipes_by_ingredients")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self._report_tool_end("search_recipes_by_ingredients")
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
        await self._report_tool_start("get_similar_recipes")

        url = f"https://api.spoonacular.com/recipes/{quote(id_, safe='')}/similar?number=3&apiKey=264361e4b8084bd992ed7128e8955736"

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    await self._report_tool_end("get_similar_recipes")
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                await self._report_tool_end("get_similar_recipes")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self._report_tool_end("get_similar_recipes")
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
        await self._report_tool_start("summarize_recipe")

        url = f"https://api.spoonacular.com/recipes/{quote(id_, safe='')}/summary?apiKey=264361e4b8084bd992ed7128e8955736"

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    await self._report_tool_end("summarize_recipe")
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                await self._report_tool_end("summarize_recipe")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self._report_tool_end("summarize_recipe")
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
        await self._report_tool_start("search_ingredients")

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
                    await self._report_tool_end("search_ingredients")
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                await self._report_tool_end("search_ingredients")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self._report_tool_end("search_ingredients")
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
        await self._report_tool_start("get_recipe_instructions")

        url = f"https://api.spoonacular.com/recipes/{quote(id_, safe='')}/analyzedInstructions?apiKey=264361e4b8084bd992ed7128e8955736"

        try:
            session = utils.http_context.http_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    await self._report_tool_end("get_recipe_instructions")
                    raise ToolError(f"error: HTTP {resp.status}: {body}")
                await self._report_tool_end("get_recipe_instructions")
                return body
        except ToolError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self._report_tool_end("get_recipe_instructions")
            raise ToolError(f"error: {e!s}") from e

    @function_tool(name="update_user_preferences")
    async def _client_tool_update_user_preferences(
        self, context: RunContext, dietary_restrictions: Optional[str] = None, disliked_ingredients: Optional[str] = None, favorite_cuisines: Optional[str] = None, notes: Optional[str] = None
    ) -> str:
        """
        Update the user's cooking preferences when they mention dietary restrictions, ingredients they dislike, favorite cuisines, or other relevant information. Pass multiple values as comma-separated strings. Call this whenever you learn something new about the user that should be remembered for future sessions.

        Args:
            dietary_restrictions: Comma-separated dietary restrictions (e.g., "vegetarian, gluten-free, dairy-free")
            disliked_ingredients: Comma-separated ingredients the user dislikes (e.g., "cilantro, olives, mushrooms")
            favorite_cuisines: Comma-separated cuisines the user enjoys (e.g., "italian, mexican, thai")
            notes: Other relevant info like skill level or time constraints
        """
        await self._report_tool_start("update_user_preferences")

        room = get_job_context().room
        linked_participant = context.session.room_io.linked_participant
        if not linked_participant:
            await self._report_tool_end("update_user_preferences")
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
            await self._report_tool_end("update_user_preferences")
            return response
        except ToolError:
            await self._report_tool_end("update_user_preferences")
            raise
        except Exception as e:
            await self._report_tool_end("update_user_preferences")
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
