# Sprecher PRODUCT.md

## Product Purpose

Sprecher is a unified TTS/STT web service that combines Kokoro ONNX (54 fast voices), Qwen3-TTS (voice cloning/design), and Whisper (transcription) into one service. Theme: **"Build for bots"** — AI agents use REST API/MCP, humans use beautiful web UI.

## Users

- **AI Agents (primary)**: Hermes-style agents that interact via REST API or MCP server for voice synthesis and transcription. They need frictionless API access, clear response formats, reliable behavior.
- **Human Operators (secondary)**: Single-user local deployment on Mac/Linux server. Access web UI for voice library management, job monitoring, document narration. Tech-savvy but not necessarily developers.

## Tone

**Professional but approachable.** "Build for bots" suggests technical competence, but "for humans too" suggests warmth. Clean, focused, no fluff. Like a well-crafted developer tool that happens to have a beautiful UI.

**Personality:** Capable, precise, quietly confident. The UI should feel like a premium developer tool — not flashy, but unmistakably quality. Like the difference between a toy terminal and a real development environment.

## Anti-references

- No childish gradients or "AI company" aesthetics (glowy purples, starfields)
- No corporate SaaS dashboard look (generic cards, flat blue accents)
- No retro "radio broadcaster" or "radio tower" clichés
- No "neon cyberpunk" for the sake of it
- No overwhelming dark theme with high-chroma neons

## Strategic Principles

1. **Bot-first, human-second** — API is primary. UI is polish.
2. **Zero friction for agents** — Auth when needed, clear errors, consistent response formats.
3. **Single-user local** — No multi-tenancy concerns, no external DB needed.
4. **Progressive complexity** — Basic TTS works immediately, advanced features (cloning, narration) available but not required.
5. **Local GPU optional** — Kokoro works on CPU (fast), Qwen needs GPU.

## Register

**Product** — Design serves the product. This is a tool with a job to do.
