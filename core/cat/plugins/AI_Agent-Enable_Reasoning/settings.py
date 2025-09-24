from cat.mad_hatter.decorators import tool, hook, plugin
from pydantic import BaseModel, Field
from datetime import datetime, date

class EnableReasoningSettings(BaseModel):
    enable_show_reasoning: bool = Field(
        default=False,
        description="If On, the Agent will show the user the LLM reasoning behind the answer. "
    )

@plugin
def settings_model():
    return EnableReasoningSettings

