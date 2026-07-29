from pydantic import BaseModel
from typing import Literal, Optional

class AgentAction(BaseModel):
    action: Literal["click", "type", "upload_file", "wait", "finish"]
    target_text: Optional[str] = None   # visible text/label of the element to act on
    value: Optional[str] = None          # text to type, or file path to upload
    reasoning: str
    step_result: Optional[str] = None    # filled in after execution: what happened
