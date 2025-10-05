from sqlalchemy import Column, Integer, String
from app.database import Base

class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, index=True)
    openrouter_api_key = Column(String, nullable=True)
    preferred_model = Column(String, default="anthropic/claude-3.5-sonnet")
    browserless_api_key = Column(String, nullable=True)