import dotenv

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import streamlit as st
from agents import (
    Runner,
    SQLiteSession,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
)
from models import UserAccountContext
from my_agents.triage_agent import triage_agent

#client = OpenAI()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"]) #스트림릿 베포를 위해해

user_account_ctx = UserAccountContext(
    customer_id=1,
    name="nico",
    tier="basic",
)


if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "restaurant-bot-memory.db",
    )
session = st.session_state["session"]

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent


async def paint_history():
    messages = await session.get_items()
    
    # 채팅 기록이 없을 때만 인사 및 소개 표시
    if not messages:
        with st.chat_message("ai"):
            st.write("안녕하세요! 👋 저는 레스토랑 고객 지원 봇이에요.")
            st.write("")
            st.write("**무엇을 도와드릴까요?**")
            st.write("")
            st.write("아래 버튼을 누르거나 직접 질문해 주세요!")
    
    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))


async def run_agent(message):
    with st.chat_message("ai"):
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        try:

            stream = Runner.run_streamed(
                st.session_state["agent"],
                message,
                session=session,
                context=user_account_ctx,
            )

            async for event in stream.stream_events():
                if event.type == "raw_response_event":

                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response.replace("$", "\$"))

                elif event.type == "agent_updated_stream_event":

                    if st.session_state["agent"].name != event.new_agent.name:
                        
                        st.write(f"🤖 {st.session_state['agent'].name} → {event.new_agent.name}로 연결됨")

                        st.session_state["agent"] = event.new_agent

                        text_placeholder = st.empty()

                        st.session_state["text_placeholder"] = text_placeholder
                        response = ""

        except InputGuardrailTripwireTriggered:
            st.write("메뉴, 주문, 예약, 불만 관련해서만 도와드릴 수 있어요.")
        except OutputGuardrailTripwireTriggered:
            st.write("죄송해요, 적절한 응답을 찾지 못했어요. 다시 시도해주세요.")


asyncio.run(paint_history())

if "pending_message" in st.session_state:
    message = st.session_state.pop("pending_message")
    with st.chat_message("human"):
        st.write(message)
    asyncio.run(run_agent(message))

# 입력란 (채팅 아래, 항상 맨 아래에 표시)
QUICK_QUESTIONS = [
    ("📋 메뉴 추천해주세요", "메뉴 추천해주세요"),
    ("🍽️ 주문하고 싶어요", "주문하고 싶어요"),
    ("📅 예약 가능해요?", "예약 가능해요?"),
    ("😤 환불 요청해요", "환불 요청해요"),
    ("🥜 알레르기 있는데요", "견과류 알레르기 있는데 어떤 메뉴 먹을 수 있어요?"),
    ("📦 주문 확인해주세요", "주문 확인해주세요"),
    ("🕐 영업시간이요", "영업시간이 어떻게 되나요?"),
    ("❌ 주문 잘못 왔어요", "주문이 잘못 왔어요"),
]

message = None
with st.expander("📌 자주 하는 질문", expanded=False):
    cols = st.columns(2)
    for i, (label, q) in enumerate(QUICK_QUESTIONS):
        if cols[i % 2].button(label, key=f"quick_q_{i}"):
            message = q
            break

chat_msg = st.chat_input("메뉴·주문·예약·불만 문의해주세요")
if message is None:
    message = chat_msg

if message:
    st.session_state["pending_message"] = message
    st.rerun()


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))