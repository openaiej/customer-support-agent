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


asyncio.run(paint_history())


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


# 퀵 메뉴를 채팅 입력창 바로 위에 고정 (스크롤해도 항상 보임)
st.markdown("""
<style>
    /* 채팅 입력창 공간 확보 */
    .block-container {
        padding-bottom: 100px !important;
    }
    /* 퀵 메뉴: 스크롤 시 화면 하단에 고정 (채팅 입력창 바로 위) */
    [data-testid="stExpander"] {
        position: sticky !important;
        bottom: 70px !important;
        z-index: 999 !important;
        background: var(--background-color, #ffffff) !important;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.08) !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# 자주 하는 질문 (접었다 펼치기 가능)
with st.expander("📌 자주 하는 질문", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📋 메뉴 추천해주세요", use_container_width=True, key="faq_menu"):
            st.session_state["faq_message"] = "메뉴 추천해주세요"
    with col2:
        if st.button("🍽️ 주문하고 싶어요", use_container_width=True, key="faq_order"):
            st.session_state["faq_message"] = "주문하고 싶어요"
    with col3:
        if st.button("📅 예약 가능해요?", use_container_width=True, key="faq_reserve"):
            st.session_state["faq_message"] = "예약 가능해요?"
    with col4:
        if st.button("😤 환불 요청해요", use_container_width=True, key="faq_refund"):
            st.session_state["faq_message"] = "환불 요청해요"

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        if st.button("🥜 알레르기 있는데요", use_container_width=True, key="faq_allergy"):
            st.session_state["faq_message"] = "견과류 알레르기 있는데 어떤 메뉴 먹을 수 있어요?"
    with col6:
        if st.button("📦 주문 확인해주세요", use_container_width=True, key="faq_confirm"):
            st.session_state["faq_message"] = "주문 확인해주세요"
    with col7:
        if st.button("🕐 영업시간이요", use_container_width=True, key="faq_hours"):
            st.session_state["faq_message"] = "영업시간이 어떻게 되나요?"
    with col8:
        if st.button("❌ 주문 잘못 왔어요", use_container_width=True, key="faq_wrong"):
            st.session_state["faq_message"] = "주문이 잘못 왔어요"

st.write("")  # 간격

message = st.chat_input(
    "메뉴·주문·예약·불만 문의해주세요",
)

# 버튼 클릭 또는 직접 입력 처리
message = message or st.session_state.pop("faq_message", None)

if message:
    with st.chat_message("human"):
        st.write(message)
    asyncio.run(run_agent(message))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))