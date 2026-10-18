"""Red-Flag Screener: fixed safety rules run FIRST, every time.

If anything looks like an emergency it says "Go to the ER now" / "Call 911"
and the Coordinator stops. No AI decides this; rules/red_flags.yaml does.
Also speaks the Chat Protocol, so anyone on ASI:One can use it alone.
"""
import yaml
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

from common.chat import ack, say, text_of
from common.config import BACKEND_ROOT, PORTS, READMES, require_seed
from common.models import ScreenRequest, ScreenResult
from common.safety import first_matching_rule
from common.tracing import carry, case_span, init_sentry

init_sentry("red_flag")
RULES = yaml.safe_load((BACKEND_ROOT / "rules" / "red_flags.yaml").read_text())["rules"]

agent = Agent(
    name="billo-red-flag-screener",
    seed=require_seed("red_flag"),
    port=PORTS["red_flag"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "red_flag.md"),
    description="Emergency check for symptoms before choosing where to get care. Says Call 911 when needed.",
)


def screen(text: str) -> ScreenResult:
    rule = first_matching_rule(text, RULES)
    if rule:
        return ScreenResult(case_id="", emergency=True, rule_id=rule["id"], message=rule["say"])
    return ScreenResult(case_id="", emergency=False, message="No emergency signs found.")


@agent.on_message(model=ScreenRequest, replies=ScreenResult)
async def on_screen(ctx: Context, sender: str, req: ScreenRequest):
    with case_span(req, op="agent.red_flag", name="screen"):
        res = screen(req.text)
        res.case_id = req.case_id
        res.trace = carry()
        # Keep logs operational only: the case identifier and screening result are health data.
        ctx.logger.info("red-flag screen completed")
        await ctx.send(sender, res)


chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ack(ctx, sender, msg)
    res = screen(text_of(msg))
    await say(ctx, sender, res.message if res.emergency else
              "I found no emergency signs in what you wrote. If things get worse, call 911.")


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
