import streamlit as st
from agents import (
    Agent,
    RunContextWrapper,
    input_guardrail,
    Runner,
    GuardrailFunctionOutput,
    handoff,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from models import UserAccountContext, InputGuardRailOutput, HandoffData
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent
from my_agents.complaints_agent import complaints_agent
from my_agents.guardrails import inappropriate_output_guardrail


# =============================================================================
# INPUT GUARDRAIL - 부적절·주제 이탈 메시지 필터링
# =============================================================================
input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    Check the user's message. Return is_off_topic (bool), is_inappropriate (bool), reason (str).

    1. OFF-TOPIC: Does it pertain to restaurant services?
       - ALLOW: Menu, Order, Reservation, Complaints (불만·항의·서비스 불만족)
       - BLOCK: Politics, religion, homework, coding, unrelated requests

    2. INAPPROPRIATE: Is it offensive or harmful?
       - BLOCK: Profanity, insults, hate speech, sexual content, harassment, threats
       - ALLOW: Legitimate complaints (e.g. "음식이 맛없었어요", "서비스가 별로예요")

    For small talk or greetings: is_off_topic=false, is_inappropriate=false.
    Legitimate complaints: ON-TOPIC, NOT inappropriate.
""",
    output_type=InputGuardRailOutput,
)


@input_guardrail
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str,
):
    result = await Runner.run(
        input_guardrail_agent,
        input,
        context=wrapper.context,
    )
    out = result.final_output
    return GuardrailFunctionOutput(
        output_info=out,
        tripwire_triggered=out.is_off_topic or out.is_inappropriate,
    )


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}


    You are the host at a cozy restaurant. You welcome guests warmly and naturally guide them to the right help.
    Use the customer's name when appropriate: {wrapper.context.name}.
    
    YOUR ROLE: Like a restaurant host, you sense what the guest needs and smoothly hand off to the right person—no corporate or call-center tone.
    
    WHEN TO HAND OFF:
    
    📋 MENU (메뉴·재료·알레르기) - Hand off when guests ask about:
    - Dishes, ingredients, allergens
    - "이 요리 뭐 들어가요?", "글루텐 프리 있어요?", "견과류 알레르기 있는데", "추천 메뉴 있어요?"
    
    🍽️ ORDER (주문) - Hand off when guests want to:
    - Place or confirm orders
    - "이거 주문할게요", "버거 두 개요", "주문 확인해주세요"
    
    📅 RESERVATION (예약) - Hand off when guests want to:
    - Book a table, check availability
    - "예약하고 싶어요", "4명 자리 있어요?", "토요일 예약 가능해요?"
    
    😤 COMPLAINTS (불만·항의) - Hand off when guests express dissatisfaction:
    - Food quality, wrong order, long wait, bad service
    - "음식이 맛없었어요", "주문이 잘못 왔어요", "서비스가 별로예요", "환불해주세요"
    
    TONE & FLOW:
    - Talk like a friendly host, not a call center agent
    - Use natural phrases: "메뉴 궁금하시면 바로 안내해드릴게요", "주문 받아드릴게요", "예약 도와드릴게요", "불편하신 점 말씀해주시면 도와드릴게요"
    - Avoid: "연결해드리겠습니다", "상담원", "담당자와 연결"
    - If unclear, ask one or two casual questions before handing off
    - For multiple needs, handle the main one first
    - Complaints: Hand off quickly with empathy—"불편을 드려 죄송해요. 바로 담당자가 도와드릴게요"
    """


def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData,
):

    with st.sidebar:
        st.write(
            f"""
            Handing off to {input_data.to_agent_name}
            Reason: {input_data.reason}
            Issue Type: {input_data.issue_type}
            Description: {input_data.issue_description}
        """
        )


def make_handoff(agent):

    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[
        off_topic_guardrail,
    ],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
        make_handoff(complaints_agent),
    ],
    output_guardrails=[inappropriate_output_guardrail],
)