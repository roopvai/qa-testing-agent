
import base64
import json
from playwright.sync_api import sync_playwright
import boto3
from src.config import get_secret
from src.schemas import AgentAction
from src.prompts import AGENT_SYSTEM

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=get_secret("AWS_REGION"),
    aws_access_key_id=get_secret("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=get_secret("AWS_SECRET_ACCESS_KEY"),
)

def decide_next_action(image_path: str, goal: str, history: list) -> AgentAction:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    history_text = "\n".join(
        f"Step {i+1}: {h['action']} on '{h['target_text']}' -> {h['step_result']}"
        for i, h in enumerate(history)
    ) or "No steps taken yet."

    prompt = (
        f"Testing goal: {goal}\n\n"
        f"History so far:\n{history_text}\n\n"
        f"Here is the current screenshot. Decide the next single action."
    )

    system = AGENT_SYSTEM.format(schema=AgentAction.model_json_schema())

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 800,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }

    response = bedrock.invoke_model(modelId=get_secret("BEDROCK_MODEL_ID"), body=json.dumps(body))
    result = json.loads(response["body"].read())
    raw = result["content"][0]["text"].strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return AgentAction(**json.loads(raw))
    except json.JSONDecodeError:
        print(f"WARNING: Claude returned non-JSON output, treating as finish. Raw output was:\n{raw}")
        return AgentAction(
            action="finish",
            target_text=None,
            value=None,
            reasoning=f"Could not parse model output as JSON — stopping safely. Raw: {raw[:200]}",
            step_result=None,
        )


def execute_action(page, frame, action: AgentAction) -> str:
    try:
        if action.action == "click":
            frame.get_by_text(action.target_text, exact=False).first.click(timeout=8000)
            return "Clicked successfully."

        elif action.action == "type":
            frame.get_by_text(action.target_text, exact=False).first.click(timeout=8000)
            page.keyboard.type(action.value or "")
            return f"Typed '{action.value}'."

        elif action.action == "upload_file":
            file_input = frame.locator("input[type='file']").first
            file_input.set_input_files(action.value, timeout=8000)
            return f"Uploaded file: {action.value}"

        elif action.action == "wait":
            page.wait_for_timeout(3000)
            return "Waited 3 seconds."

        elif action.action == "finish":
            return "Agent finished."

    except Exception as e:
        return f"FAILED: {e}"


def run_agent(url: str, goal: str, max_steps: int = 6):
    history = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)

        streamlit_frame = page.frame_locator("iframe[src*='streamlit.app']").first

        try:
            streamlit_frame.get_by_text("AI Test Case", exact=False).first.wait_for(timeout=30000)
        except Exception as e:
            yield {"type": "warning", "message": f"Target app may not have loaded — {e}"}

        for step in range(1, max_steps + 1):
            screenshot_path = f"step_{step}.png"
            page.screenshot(path=screenshot_path)

            action = decide_next_action(screenshot_path, goal, history)

            if action.action == "finish":
                action.step_result = "Agent decided to finish."
                history.append(action.model_dump())
                yield {
                    "type": "step", "step": step, "screenshot": screenshot_path,
                    "action": action.action, "target": action.target_text,
                    "reasoning": action.reasoning, "result": action.step_result,
                }
                break

            result = execute_action(page, streamlit_frame, action)
            action.step_result = result
            history.append(action.model_dump())

            yield {
                "type": "step", "step": step, "screenshot": screenshot_path,
                "action": action.action, "target": action.target_text,
                "reasoning": action.reasoning, "result": result,
            }

            page.wait_for_timeout(1500)

        browser.close()

    yield {"type": "done", "history": history}