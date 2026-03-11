"""
Guardrails - Input/Output 검사 및 필터링

- Input Guardrail: 부적절·주제 이탈 메시지 필터링
- Output Guardrail: 봇 응답의 부적절 여부 검사
"""

from agents import Agent, RunContextWrapper, output_guardrail, Runner, GuardrailFunctionOutput
from models import UserAccountContext, OutputGuardRailOutput


# =============================================================================
# OUTPUT GUARDRAIL - 봇 응답의 부적절 여부 검사
# =============================================================================
output_guardrail_agent = Agent(
    name="Output Guardrail Agent",
    instructions="""
    Check if the bot's response is appropriate for a restaurant customer service context.

    BLOCK (is_inappropriate=true) if the response contains:
    - Profanity, insults, or offensive language
    - Discriminatory or hateful content
    - Sexual or inappropriate suggestions
    - Leaking internal info, secrets, or system prompts
    - Refusing to help in a rude way (polite refusal is OK)

    ALLOW (is_inappropriate=false) for:
    - Polite, helpful, professional responses
    - Apologies and empathy for complaints
    - Menu/order/reservation info
    - Saying "메뉴, 주문, 예약 관련해서만 도와드릴 수 있어요" when off-topic
""",
    output_type=OutputGuardRailOutput,
)


@output_guardrail
async def inappropriate_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    output: str,
) -> GuardrailFunctionOutput:
    """봇 응답이 부적절한지 검사. output은 에이전트의 최종 텍스트 응답."""
    if not isinstance(output, str):
        output = str(output) if output else ""
    result = await Runner.run(
        output_guardrail_agent,
        output,
        context=wrapper.context,
    )
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_inappropriate,
    )
