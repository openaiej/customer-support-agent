"""
tools.py - 레스토랑 봇 AI 에이전트가 사용하는 함수형 도구 모음

Restaurant Bot Agent Tools - 식당 봇 에이전트가 호출할 수 있는 function tools
- Menu Tools: 메뉴 정보, 재료, 알레르기 조회
- Order Tools: 주문 접수, 주문 확인
- Reservation Tools: 예약 가능 여부 확인, 테이블 예약
"""

import streamlit as st
from agents import function_tool, AgentHooks, Agent, Tool, RunContextWrapper
from models import UserAccountContext
import random
from datetime import datetime, timedelta


# =============================================================================
# 샘플 메뉴 데이터 (실제 운영 시 DB/API로 교체)
# =============================================================================
MENU_ITEMS = {
    "파스타 알프레도": {
        "price": 18000,
        "ingredients": ["파스타", "크림", "파르메산", "버터", "마늘"],
        "allergens": ["우유", "계란", "글루텐"],
        "description": "부드러운 크림 소스의 클래식 파스타",
    },
    "스테이크": {
        "price": 35000,
        "ingredients": ["소고기", "소금", "후추", "버터", "로즈마리"],
        "allergens": ["없음"],
        "description": "미디엄 레어 추천, 200g 안심 스테이크",
    },
    "시저 샐러드": {
        "price": 12000,
        "ingredients": ["로메인", "시저 드레싱", "파르메산", "크루통", "레몬"],
        "allergens": ["우유", "계란", "글루텐", "어류(앵초비)"],
        "description": "클래식 시저 드레싱의 신선한 샐러드",
    },
    "연어 그릴": {
        "price": 28000,
        "ingredients": ["노르웨이 연어", "레몬", "다일", "올리브오일"],
        "allergens": ["어류"],
        "description": "그릴에 구운 노르웨이 연어 필렛",
    },
    "비건 부들볶음": {
        "price": 15000,
        "ingredients": ["부들", "두부", "야채", "간장", "참기름"],
        "allergens": ["대두"],
        "description": "채식 메뉴, 글루텐 프리",
    },
}


# =============================================================================
# MENU TOOLS - 메뉴 도구 (Menu Agent용)
# =============================================================================


@function_tool
def get_menu_info(
    context: UserAccountContext, category: str = "all"
) -> str:
    """
    메뉴 항목과 가격, 설명을 조회합니다.
    Look up menu items with prices and descriptions.

    Args:
        category: 메뉴 카테고리 (all, main, salad, pasta 등) / Menu category
    """
    lines = ["📋 오늘의 메뉴\n"]
    for name, info in MENU_ITEMS.items():
        lines.append(f"• {name}: ₩{info['price']:,} - {info['description']}")
    return "\n".join(lines)


@function_tool
def check_ingredients(
    context: UserAccountContext, dish_name: str
) -> str:
    """
    특정 요리의 재료 목록을 조회합니다.
    Look up ingredients for a specific dish.

    Args:
        dish_name: 요리명 / Name of the dish
    """
    for name, info in MENU_ITEMS.items():
        if dish_name in name or name in dish_name:
            ingredients = ", ".join(info["ingredients"])
            return f"🍽️ {name} 재료:\n{ingredients}"
    return f"'{dish_name}' 메뉴를 찾을 수 없어요. 다른 메뉴명으로 문의해주세요."


@function_tool
def check_allergens(
    context: UserAccountContext, dish_name: str = "", allergen: str = ""
) -> str:
    """
    요리별 알레르기 정보를 조회하거나, 특정 알레르기 유발 식품이 포함된 메뉴를 확인합니다.
    Look up allergen info by dish, or find dishes containing a specific allergen.

    Args:
        dish_name: 요리명 (특정 메뉴 조회 시) / Dish name for specific menu lookup
        allergen: 알레르기 유발 식품 (우유, 계란, 글루텐, 견과류, 갑각류, 어류, 대두 등)
                 Allergen to check (dairy, egg, gluten, nuts, shellfish, fish, soy)
    """
    allergen_map = {
        "우유": "우유", "dairy": "우유", "milk": "우유",
        "계란": "계란", "egg": "계란", "eggs": "계란",
        "글루텐": "글루텐", "gluten": "글루텐",
        "견과류": "견과류", "nuts": "견과류",
        "갑각류": "갑각류", "shellfish": "갑각류",
        "어류": "어류", "fish": "어류",
        "대두": "대두", "soy": "대두",
    }

    if dish_name:
        for name, info in MENU_ITEMS.items():
            if dish_name in name or name in dish_name:
                allergens = ", ".join(info["allergens"])
                return f"⚠️ {name} 알레르기 정보:\n{allergens}"
        return f"'{dish_name}' 메뉴를 찾을 수 없어요."

    if allergen:
        norm = allergen_map.get(allergen.lower(), allergen)
        safe = []
        contains = []
        for name, info in MENU_ITEMS.items():
            if norm in info["allergens"] or any(norm in a for a in info["allergens"]):
                contains.append(name)
            else:
                safe.append(name)
        result = [f"🔍 '{allergen}' 검색 결과\n"]
        if contains:
            result.append(f"❌ 포함: {', '.join(contains)}")
        if safe:
            result.append(f"✅ 해당 없음 (선택 가능): {', '.join(safe)}")
        return "\n".join(result)

    lines = ["⚠️ 전체 메뉴 알레르기 정보\n"]
    for name, info in MENU_ITEMS.items():
        lines.append(f"• {name}: {', '.join(info['allergens'])}")
    return "\n".join(lines)


# =============================================================================
# ORDER TOOLS - 주문 도구 (Order Agent용)
# =============================================================================


@function_tool
def place_order(
    context: UserAccountContext,
    items: str,
    order_type: str = "dine_in",
    special_requests: str = "",
) -> str:
    """
    주문을 접수합니다. (매장식/포장/배달)
    Place an order (dine-in, takeout, or delivery).

    Args:
        items: 주문 품목 (예: "파스타 알프레도 1, 시저 샐러드 2")
              Order items
        order_type: 주문 유형 (dine_in, takeout, delivery)
        special_requests: 특별 요청 (덜 맵게, 아이스 없이 등)
                         Special requests
    """
    order_id = f"ORD-{random.randint(1000, 9999)}"
    wait_mins = random.randint(15, 25)
    order_type_ko = {"dine_in": "매장 식사", "takeout": "포장", "delivery": "배달"}.get(
        order_type, order_type
    )

    return f"""
✅ 주문 접수 완료
🔢 주문번호: {order_id}
📋 주문: {items}
🍽️ 유형: {order_type_ko}
⏱️ 예상 대기: {wait_mins}분
{f'📝 특별 요청: {special_requests}' if special_requests else ''}
    """.strip()


@function_tool
def confirm_order(context: UserAccountContext, order_id: str) -> str:
    """
    주문 내용을 확인합니다.
    Confirm order details and status.

    Args:
        order_id: 주문번호 / Order ID
    """
    statuses = ["조리 중", "준비 완료", "서빙 완료"]
    status = random.choice(statuses)
    return f"""
📦 주문 확인
🔢 주문번호: {order_id}
🏷️ 상태: {status}
    """.strip()


# =============================================================================
# RESERVATION TOOLS - 예약 도구 (Reservation Agent용)
# =============================================================================


@function_tool
def check_availability(
    context: UserAccountContext, date: str, time: str, party_size: int = 2
) -> str:
    """
    요청한 날짜·시간의 예약 가능 여부를 확인합니다.
    Check table availability for the requested date and time.

    Args:
        date: 예약 희망일 (YYYY-MM-DD 또는 "오늘", "내일")
              Desired date
        time: 예약 희망 시간 (예: "18:00", "저녁 7시")
              Desired time
        party_size: 인원 수 / Number of guests
    """
    # 데모용: 랜덤으로 가능/불가 반환
    available = random.choice([True, True, False])
    if available:
        return f"""
✅ 예약 가능해요
📅 {date} {time}
👥 {party_size}명
원하시면 바로 예약 잡아드릴게요.
        """.strip()
    return f"""
❌ 해당 시간 예약이 마감되었어요
📅 {date} {time}
👥 {party_size}명
다른 시간대를 알려주시면 확인해드릴게요.
        """.strip()


@function_tool
def make_reservation(
    context: UserAccountContext,
    date: str,
    time: str,
    party_size: int,
    guest_name: str = "",
    contact: str = "",
    special_requests: str = "",
) -> str:
    """
    테이블 예약을 완료합니다.
    Complete a table reservation.

    Args:
        date: 예약일 / Reservation date
        time: 예약 시간 / Reservation time
        party_size: 인원 수 / Number of guests
        guest_name: 예약자명 (고객이 직접 입력한 경우에만 사용)
        contact: 연락처 (전화 또는 이메일)
        special_requests: 특별 요청 (생일, 유아용 의자 등)
    """
    res_id = f"RES-{random.randint(1000, 9999)}"
    name = guest_name or "고객"
    contact_info = contact or (context.email or "미등록")

    return f"""
✅ 예약 완료
🔢 예약번호: {res_id}
📅 {date} {time}
👥 {party_size}명
👤 예약자: {name}
📞 연락처: {contact_info}
{f'📝 특별 요청: {special_requests}' if special_requests else ''}
※ 15분 이상 지연 시 예약이 취소될 수 있어요.
    """.strip()


# =============================================================================
# COMPLAINTS TOOLS - 불만 처리 도구 (Complaints Agent용)
# =============================================================================


@function_tool
def log_complaint(
    context: UserAccountContext,
    complaint_type: str,
    description: str,
    order_id: str = "",
) -> str:
    """
    고객 불만을 기록합니다.
    Log a customer complaint for tracking and follow-up.

    Args:
        complaint_type: 불만 유형 (food_quality, wait_time, wrong_order, service, cleanliness, other)
        description: 불만 상세 설명
        order_id: 관련 주문번호 (있을 경우)
    """
    complaint_id = f"CMP-{random.randint(1000, 9999)}"
    return f"""
📋 불만 접수 완료
🔢 접수번호: {complaint_id}
📂 유형: {complaint_type}
📝 내용: {description}
{f'📦 관련 주문: {order_id}' if order_id else ''}
담당자가 확인 후 연락드릴게요.
    """.strip()


@function_tool
def offer_compensation(
    context: UserAccountContext,
    compensation_type: str,
    value: str = "",
    reason: str = "",
) -> str:
    """
    고객에게 보상(할인, 무료 메뉴 등)을 제안합니다.
    Offer compensation (discount, free item, etc.) to the customer.

    Args:
        compensation_type: 보상 유형 (discount_next_visit, free_dessert, free_drink, refund, replacement)
        value: 보상 내용 (예: "20%", "디저트 1인분")
        reason: 보상 사유
    """
    code = f"COMP-{random.randint(10000, 99999)}"
    return f"""
🎁 보상 제안
📋 유형: {compensation_type}
💰 내용: {value or '담당자 확인 후 안내'}
📝 사유: {reason or '서비스 불편에 대한 사과'}
🔑 사용 코드: {code}
다음 방문 시 매장에 보여주시면 적용해드릴게요.
    """.strip()


@function_tool
def escalate_complaint(
    context: UserAccountContext,
    reason: str,
    urgency: str = "normal",
) -> str:
    """
    심각한 불만을 매니저/관리자에게 에스컬레이션합니다.
    Escalate a serious complaint to manager/supervisor.

    Args:
        reason: 에스컬레이션 사유
        urgency: 긴급도 (low, normal, high, critical)
    """
    ticket_id = f"ESC-{random.randint(1000, 9999)}"
    return f"""
⬆️ 매니저 연결 요청
🔢 티켓: {ticket_id}
📝 사유: {reason}
⚡ 긴급도: {urgency}
매니저가 30분 이내 연락드릴 예정이에요.
    """.strip()


# =============================================================================
# AgentToolUsageLoggingHooks - 에이전트 도구 사용 로깅 훅
# =============================================================================
class AgentToolUsageLoggingHooks(AgentHooks):
    """에이전트 도구 사용·handoff 시 Streamlit 사이드바에 로그를 출력하는 훅"""

    async def on_tool_start(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        tool: Tool,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** starting tool: `{tool.name}`")

    async def on_tool_end(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        tool: Tool,
        result: str,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** used tool: `{tool.name}`")
            st.code(result)

    async def on_handoff(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        source: Agent[UserAccountContext],
    ):
        with st.sidebar:
            st.write(f"🔄 Handoff: **{source.name}** → **{agent.name}**")

    async def on_start(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
    ):
        with st.sidebar:
            st.write(f"🚀 **{agent.name}** activated")

    async def on_end(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        output,
    ):
        with st.sidebar:
            st.write(f"🏁 **{agent.name}** completed")
