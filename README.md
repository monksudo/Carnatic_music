# Holistic Carnatic Music Chart

A single-page visual reference (`index.html`) covering the core building blocks of Carnatic music, inspired by the popular "Carnatic Tala System" infographic.

## What's covered

| Concept | What you'll find |
|---|---|
| **Shruti** | 22 microtone distribution across the 7 swaras |
| **Swara** | 7 swaras → 16 swarasthanas (12 unique pitches), Prakriti vs Vikriti |
| **Raga** | Janaka (72 Melakarta) vs Janya, Chakra table, Audava/Shadava/Sampurna |
| **Gamaka** | Dasa Vidha (10 ornaments) with descriptions |
| **Bhava / Rasa** | Navarasa (9 emotions) mapped to representative ragas |
| **Laya** | Vilamba / Madhyama / Drta tempi and the 5 Kalas |
| **Tala** | Anga (Laghu / Drutam / Anudrutam), 5 Jathis × 7 Sapta Talas = 35-Tala scheme with akshara math, plus Carnatic ↔ Hindustani term mapping (Sam, Matra, Vibhag, Theka) |
| **Composition forms** | Geetham, Swarajati, Varnam, Kriti/Kirtana (Pallavi · Anupallavi · Charanam), Padam, Javali, Tillana, Ragamalika, Viruttam |
| **Manodharma / Performance** | Alapana, Tanam, Niraval, Kalpanaswaram, RTP (Ragam · Tanam · Pallavi) |
| **Mental model** | How all of the above combine into a complete performance |

## Viewing

Just open `index.html` in any browser — no build step or dependencies.

## Studio — local-AI SVG generator

This repo also hosts **Studio**, a separate subsystem under [`studio/`](studio/)
that generates layered, no-gradient, 3D-look SVGs (icons, papercraft clip art,
architecture diagrams) using a local LLM (Ollama by default), with a tagged,
searchable library and CLI / HTTP API / MCP-server access. See
[`studio/README.md`](studio/README.md) for full usage.
