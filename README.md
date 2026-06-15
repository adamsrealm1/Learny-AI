# Learny AI

Learny is a Python chatbot with no database and no local server.

It only knows what is stored in `data/knowledge.json`. It first answers from that file. If it does not know an answer and `GROQ_API_KEY` is set, it asks Groq, saves the answer into `data/knowledge.json`, and responds with that learned answer.

Groq learning uses:

1. `llama-3.1-8b-instant`
2. `openai/gpt-oss-20b` if the first model fails
3. The normal unknown message if both fail

## Run Learny

```powershell
python main.py
```

Ask one question and exit:

```powershell
python main.py --once "hello"
```

Run the self-checks:

```powershell
python -m unittest discover -s tests -v
```

## Enable Groq Learning

Create a Groq API key at groq.com, then set it in PowerShell:

```powershell
$env:GROQ_API_KEY = "your-key-here"
python main.py
```

With the key set, unknown questions are sent to Groq. Learny asks Groq for an answer, saves it locally, and then uses the saved JSON answer next time. If both Groq models fail, Learny returns the normal unknown message and does not save anything.

To force local-only mode even when `GROQ_API_KEY` exists:

```powershell
python main.py --offline
```

## Teach Learny

Edit `data/knowledge.json`.

Learny looks for a question phrase from the JSON inside whatever you type. If it finds one, it returns one exact answer from that JSON entry.

Example:

```json
{
  "questions": {
    "hello": [
      "Hello.",
      "Hi."
    ],
    "what is your name": "My name is Learny."
  }
}
```

With that knowledge, these messages would match:

- `hello`
- `can you say hello`
- `WHAT IS YOUR NAME?`

If an entry has more than one answer, Learny randomly picks one with Python's standard `random` module.

When Groq learns a new answer, it stores the answer as a list so you can manually add more answers later.

Follow-up questions are handled with temporary in-memory conversation context. For example, if you ask about France and then ask `what is its capital`, Learny asks Groq to rewrite that follow-up as a standalone question before saving it. The saved JSON should look like `what is the capital of France`, not `what is its capital`.

## Project Structure

```text
Learny AI/
  main.py                  # Main launcher
  README.md                # How the project works
  pyproject.toml           # Project metadata
  data/
    knowledge.json         # Manual questions and answers
  learny/
    __init__.py            # Package exports
    __main__.py            # Allows: python -m learny
    bot.py                 # Learny response logic
    cli.py                 # Command line interface
    conversation.py        # In-memory context for follow-up questions
    groq_client.py         # Standard-library Groq API client
    knowledge.py           # JSON loading and validation
    memory.py              # Saves learned answers back to JSON
    text.py                # Text cleanup and phrase matching
  tests/
    test_learny.py         # Local behavior tests
```

## JSON Rules

- Keep valid JSON. JSON does not allow comments.
- Put question phrases inside the `questions` object.
- Each question can have one answer as a string.
- Each question can also have multiple answers as a list of strings.
- Empty questions and empty answers are rejected.
- If several questions match, Learny uses the longest matching question.
