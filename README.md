# Autonomous QA Testing Agent

An AI agent that autonomously tests a live web application by actually using it — driving a real browser, deciding its own next actions from what it sees on screen, and reporting what it did. Built as a natural extension of my [AI Test Case & Quality Risk Generator](https://github.com/roopvai/srs-test-agent): that project generates test coverage from requirements, this one executes it.

**[Live Demo](https://app-testing-agent.streamlit.app/)** · **[Report a bug](https://github.com/roopvai/qa-testing-agent/issues)**

---

## How it works

```
Target URL + testing goal (e.g. "upload this file and confirm it processes")
        |
        v
Playwright launches a real headless browser, navigates to the target
        |
        v
   Agent loop (repeats until goal is met or max steps reached)
        |
        +--> Screenshot the current page state
        +--> Send screenshot + goal + action history to Claude (vision, via Bedrock)
        +--> Claude returns a single structured next action (JSON, schema-validated)
        +--> Playwright executes that action (click, type, upload file, wait, finish)
        +--> Result recorded, loop continues
        |
        v
Full run history -> downloadable Markdown QA report with reasoning per step
```

**Why structured JSON actions instead of free-text instructions?** The same lesson from my SRS project: an LLM's prose description of what it would do isn't something code can act on reliably. Forcing a schema-validated action (`click`, `type`, `upload_file`, `wait`, `finish`) with a specific target and reasoning turns "the model has an opinion" into "the model issues a command the browser can actually execute."

**Why let the agent decide when it's done, rather than a fixed script?** A hardcoded test script only knows how to check for the outcome it was told to expect. Here, Claude evaluates the actual screenshot at each step and decides for itself whether the goal was met — in testing, it correctly recognized "Found 49 requirements" appearing on screen as goal completion, without that exact string being hardcoded anywhere in the stopping logic.

## Stack

| Layer | Technology |
|---|---|
| Browser automation | Playwright (Python) |
| Reasoning / vision | Amazon Bedrock (Claude) |
| Action schema validation | Pydantic |
| UI | Streamlit |
| Hosting | Streamlit Community Cloud |

## Real debugging challenges solved along the way

This project surfaced a distinct set of problems from a typical API-only GenAI app, since it involves actually controlling a browser against a real, evolving web page:

- **Streamlit Cloud's iframe wrapping.** Deployed Streamlit apps render inside an iframe within Streamlit Cloud's own outer chrome (fork button, viewer controls). Playwright's default locators only search the top-level page, so every selector silently found nothing until I diagnosed the iframe structure directly and switched to `frame_locator` to target the app's actual content frame.
- **Cold-start timing.** Free-tier cloud apps can take 20-60+ seconds to wake up from sleep. A fixed wait timeout is a guess; I replaced it with active polling — repeatedly checking for real page content (not just a fixed delay) before starting the agent loop.
- **Deploying Playwright itself to the cloud.** Unlike a pure API-calling app, this one needs an actual browser binary. Streamlit Cloud's default environment doesn't include one — solved with a `packages.txt` for system-level dependencies plus a runtime `playwright install chromium` step at app startup.
- **Graceful handling of malformed model output.** Occasionally Claude's JSON response gets truncated mid-object (usually when its reasoning ran long against the token limit). Rather than let this crash the whole run, the agent catches the parse failure and falls back to a safe `finish` action — the run completes cleanly and the raw output is preserved for debugging, instead of the entire app crashing on one bad response.

## Sample output

[`/samples`](./samples) contains a full run report generated against my SRS Test Agent project — uploading a sample requirements document and confirming successful processing, entirely autonomously.

## Getting started

### Prerequisites
- Python 3.11
- An AWS account with Amazon Bedrock model access enabled

### Setup

```bash
git clone https://github.com/roopvai/qa-testing-agent.git
cd qa-testing-agent
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Create a `.env` file:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

### Run locally

```bash
streamlit run app.py
```

Open `http://localhost:8501`, enter a target URL and testing goal, optionally upload a file the goal references, and click **Run Agent**.

## Project structure

```
qa-testing-agent/
├── app.py                  # Streamlit UI, drives the agent as a live generator
├── src/
│   ├── agent.py             # Core agent loop: screenshot -> reason -> act -> repeat
│   ├── schemas.py           # Pydantic schema for structured agent actions
│   ├── prompts.py           # System prompt enforcing structured JSON output
│   ├── vision_agent.py      # Standalone Claude vision call (early prototype/testbed)
│   └── config.py            # Local .env / Streamlit Cloud secrets bridge
├── samples/                 # Sample run report
├── packages.txt             # System-level dependencies for Playwright on Streamlit Cloud
└── requirements.txt
```

## Known limitations & next steps

- **Only confirms task completion, doesn't yet hunt for bugs.** The agent currently verifies a goal was reached; a more complete QA tool would also actively probe for broken states — error messages, unexpected layouts, failed validations — rather than only checking the happy path.
- **Tested primarily against one well-behaved target app.** Next step: run it against a deliberately trickier target (e.g. a public QA practice sandbox) to validate it generalizes beyond an app it was built alongside.
- **No retry/self-correction when an action fails.** If a click or upload fails, the agent currently just logs the failure and lets the next reasoning step decide what to do — a more robust version would have explicit retry logic with a different strategy on failure.
- **Sequential, single-session runs only.** No batch mode yet for running multiple goals or multiple target apps in one session.

## License

MIT

