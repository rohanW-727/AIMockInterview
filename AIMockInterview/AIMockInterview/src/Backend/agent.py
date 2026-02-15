import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, JobContext
from livekit.plugins import silero, openai
from intro_agent import IntroAgent

load_dotenv(".env.local")
logger = logging.getLogger(__name__)

END_OF_TURN_SILENCE = 2.0


async def entrypoint(ctx: JobContext):
    logger.info(f"[entrypoint] joined room: {ctx.room.name}")
    await ctx.connect()

    session = AgentSession(
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy", speed=1.15),
        vad=silero.VAD.load(
            min_silence_duration=1.0,  # CHANGED: Reduced from 2.0 for faster turn detection
            min_speech_duration=0.05,  # CHANGED: Reduced from 0.08
            padding_duration=0.2,      # CHANGED: Reduced from 0.3
        ),
        min_endpointing_delay=0.8,  # NEW: Faster turn completion
        preemptive_generation=True,  # NEW: Start generating while user is still speaking
    )

    await session.start(room=ctx.room, agent=IntroAgent())
    await session.wait_for_disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))