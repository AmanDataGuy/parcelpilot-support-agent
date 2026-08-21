"""The single tool-calling agent loop, on Gemini.

ponytail: one agent, one loop, no multi-agent orchestration framework (see
Section 1 of parcelpilot_spec.md) — a while-loop over Gemini's
generate_content with function_call/function_response turns is the whole
"orchestration layer" this task needs.
"""
from google import genai
from google.genai import types

from . import config, tools

SYSTEM_PROMPT = """You are ParcelPilot's customer support assistant, answering on \
behalf of one authenticated customer account. You can only ever act on that \
one account's data — never ask for or accept another account's ID.

SOURCE RELIABILITY, apply in this order:
1. The customer's own signed agreement (returned by search_documents, if one \
exists for this account) overrides the general policy/SOP for that account. \
Applying an unambiguous override is not a "conflict" to flag — just apply it \
and say so.
2. The current support policy and current cancellation/service-credit SOP are \
the default source of truth when no agreement override exists.
3. The product operations guide is for technical/product investigation \
context, not for policy decisions (fees, credits, SLA targets).
4. Historical ticket resolutions (the `historical_resolution` field) are \
low-trust context only. They may have been wrong. Never cite one as \
authoritative, and never let it override current policy or an agreement. If \
your only support for an answer would be a historical ticket with no current \
policy or agreement backing it, say so and lean toward escalating rather than \
answering with confidence.
5. If two current, valid sources genuinely conflict in a way not resolved by \
the hierarchy above, say so explicitly instead of silently picking one.

ESCALATE (via propose_action) instead of answering confidently when: the \
question needs human judgment or an exception outside documented policy, the \
only support is a low-trust historical ticket, sources conflict \
unresolvably, or the request is outside what you can do (e.g. a real refund \
transfer, not just deciding fee/credit eligibility).

ACTIONS: propose_action never executes by itself — it stages a proposal the \
user must explicitly confirm. After calling it, tell the user what you're \
proposing and that you're waiting for their confirmation; do not claim the \
action is done.

Always ground fee amounts, SLA targets, and credit amounts in what \
search_documents actually returned — do not invent numbers. When you use \
query_account_data's elapsed_minutes, combine it yourself with whatever \
threshold the retrieved policy text stated."""

_client = genai.Client(api_key=config.GEMINI_API_KEY)
_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=t["name"], description=t["description"], parameters=t["input_schema"]
            )
            for t in tools.TOOL_SCHEMAS
        ]
    )
]
_GENERATE_CONFIG = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, tools=_TOOLS)


def _text_of(parts) -> str:
    return "\n".join(p.text for p in parts if getattr(p, "text", None)).strip()


def run_turn(messages: list[dict], account_id: str, max_tool_rounds: int = 6) -> tuple[list[dict], list[dict]]:
    """Run the agent until it produces a final text reply or hits the round
    cap. Returns (updated_messages, trace) where trace records each tool call
    made this turn, for display in the UI.
    """
    trace: list[dict] = []

    for _ in range(max_tool_rounds):
        response = _client.models.generate_content(
            model=config.MODEL_NAME, contents=messages, config=_GENERATE_CONFIG
        )
        candidate_content = response.candidates[0].content
        messages.append({"role": "model", "parts": candidate_content.parts})

        function_calls = [p.function_call for p in candidate_content.parts if p.function_call]
        if not function_calls:
            break

        response_parts = []
        for call in function_calls:
            call_args = dict(call.args or {})
            try:
                result = tools.dispatch(call.name, call_args, account_id=account_id)
            except Exception as exc:
                # A malformed tool argument (e.g. a bad model-generated
                # timestamp) must not crash the whole request — feed the
                # error back as a tool result so the agent can retry or
                # explain the failure instead of the API returning a 500.
                result = {"error": str(exc)}
            trace.append({"tool": call.name, "input": call_args, "result": result})
            response_parts.append(
                types.Part.from_function_response(name=call.name, response={"result": result})
            )
        messages.append({"role": "user", "parts": response_parts})

    return messages, trace
