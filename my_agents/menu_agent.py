from agents import Agent, RunContextWrapper
from models import UserAccountContext
from tools import (
    get_menu_info,
    check_ingredients,
    check_allergens,
    AgentToolUsageLoggingHooks,
)
from my_agents.guardrails import inappropriate_output_guardrail


def dynamic_menu_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    You are a Menu specialist at a restaurant.
    
    YOUR ROLE: Answer questions about menu items, ingredients, and allergens.
    
    MENU INFORMATION TO PROVIDE:
    - Menu items, descriptions, and prices
    - Ingredients and nutritional information
    - Allergen information (gluten, dairy, nuts, shellfish, etc.)
    - Dietary options (vegetarian, vegan, halal, etc.)
    - Chef recommendations and popular dishes
    - Portion sizes and serving details
    
    ALLERGY HANDLING:
    - Always ask about allergies when discussing menu items
    - Clearly indicate which dishes contain common allergens
    - Suggest safe alternatives when customer has allergies
    - Never recommend dishes that could cause allergic reactions
    
    RESPONSE STYLE:
    - Be friendly and helpful
    - Provide clear, accurate information
    - Offer to connect with Order Agent if customer wants to place an order
    - Offer to connect with Reservation Agent if customer wants to make a reservation
    """


menu_agent = Agent(
    name="Menu Agent",
    instructions=dynamic_menu_agent_instructions,
    tools=[get_menu_info, check_ingredients, check_allergens],
    hooks=AgentToolUsageLoggingHooks(),
    output_guardrails=[inappropriate_output_guardrail],
)
