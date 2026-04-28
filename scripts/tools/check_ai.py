from core.services.ai_engine import ai_engine
print(f"AIEngine attributes: {dir(ai_engine)}")
try:
    print(f"Has parse_structured_data: {hasattr(ai_engine, 'parse_structured_data')}")
except Exception as e:
    print(f"Error checking attribute: {e}")
