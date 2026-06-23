# Learny AI

Learny AI is a polished Groq-powered chatbot with a Python backend, animated web interface, popup-based accounts, and account-based chat memory.

It keeps the main experience focused on conversation while account popups give each user a small personal space for synced chats, sessions, and profile state. On Wasmer, Learny stores durable account data in the app's attached MySQL database: accounts, secure password hashes, sessions, chats, messages, response timing, and account events. Local development still falls back to SQLite so the same backend can run without a cloud database.
