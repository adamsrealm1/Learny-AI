# Learny AI

Learny AI is now a website with an animated HTML/CSS/JS frontend and a Python server backend.

The Python backend still keeps the original JSON brain:

```text
User asks in the browser
-> Python server checks data/knowledge.json
-> If found, Learny answers from JSON
-> If not found and GROQ_API_KEY is set, Learny calls Groq
-> Tries llama-3.1-8b-instant first
-> Tries openai/gpt-oss-20b if the first model fails
-> Saves learned answers into data/knowledge.json
-> If both models fail, returns the unknown message
```

## Run The Website With Wasmer

```powershell
wasmer run . --net --env PORT=8000
```

Open:

```text
http://127.0.0.1:8000
```

Do not launch `web/index.html` directly for normal use. The page can display from `file://`, but the chat needs the Wasmer-hosted Python API for the JSON brain and Groq learning.

Use another port:

```powershell
wasmer run . --net --env PORT=8080
```

Run without Groq calls:

```powershell
wasmer run . --net --env PORT=8000 --env GROQ_API_KEY=
```

## Run Directly With Python

This is only a faster local development shortcut. Wasmer uses the same Python server through `src/main.py`.

```powershell
python server.py
```

Open:

```text
http://127.0.0.1:8000
```

Use another Python-only port:

```powershell
python server.py --port 8080
```

Run Python directly without Groq calls:

```powershell
python server.py --offline
```

## Enable Groq Learning

Create a Groq API key at groq.com, then set it before starting the server:

```powershell
$env:GROQ_API_KEY = "your-key-here"
wasmer run . --net --env PORT=8000 --env GROQ_API_KEY=$env:GROQ_API_KEY
```

The browser never receives your key. Only the Python backend reads `GROQ_API_KEY`.

## Wasmer Deployment

This repo includes:

```text
wasmer.toml
app.yaml
src/main.py
```

The Wasmer entrypoint is `src/main.py`, which runs the same Python server as `server.py`.

The Wasmer package namespace is set to `adamsrealm1`:

```text
wasmer.toml -> [package].name
app.yaml -> package
```

Then deploy from the repo root:

```powershell
wasmer deploy --publish-package
```

For local Wasmer testing:

```powershell
wasmer run . --net --env PORT=8000
```

## Teach Learny Manually

Edit `data/knowledge.json`.

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

Rules:

- Keep valid JSON. JSON does not allow comments.
- Put question phrases inside the `questions` object.
- Each question can have one answer as a string.
- Each question can also have multiple answers as a list of strings.
- Empty questions and empty answers are rejected.
- If several questions match, Learny uses the longest matching question.

## Project Structure

```text
Learny AI/
  app.yaml                 # Wasmer app deployment config
  server.py                # Local web server launcher
  wasmer.toml              # Wasmer package config
  data/
    knowledge.json         # Manual and learned questions/answers
  learny/
    bot.py                 # JSON-first answer flow
    cli.py                 # Original command line app
    conversation.py        # In-memory follow-up context
    groq_client.py         # Standard-library Groq API client
    knowledge.py           # JSON loading and validation
    memory.py              # Writes learned answers back to JSON
    text.py                # Text cleanup and phrase matching
    web_server.py          # Python HTTP server and API routes
  src/
    main.py                # Wasmer entrypoint
  tests/
    test_learny.py         # Core Learny tests
    test_web_server.py     # Website API tests
  web/
    index.html             # Website markup
    styles.css             # Animated polished UI
    app.js                 # Browser API calls and chat behavior
    assets/
      learny-core.png      # Generated bitmap UI asset
```

## API Routes

```text
GET  /api/status
GET  /api/knowledge
POST /api/ask
```

`POST /api/ask` accepts:

```json
{
  "message": "hello",
  "sessionId": "optional-browser-session-id"
}
```

The server keeps follow-up context in memory per browser session.

## Tests

```powershell
python -m unittest discover -s tests -v
```
