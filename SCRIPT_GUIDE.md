# Script Preparation Guide

How to format scripts for Qwen-semble's Narration tab — covering all parsing modes, speaker annotations, and per-segment style/emotion overrides.

---

## Table of Contents

- [Choosing a Parsing Mode](#choosing-a-parsing-mode)
- [Mode: Single Voice](#mode-single-voice)
- [Mode: Paragraphs](#mode-paragraphs)
- [Mode: Manual Segments](#mode-manual-segments)
- [Mode: Annotated (Multi-Speaker)](#mode-annotated-multi-speaker)
- [Style & Emotion Tags](#style--emotion-tags)
- [Combining Speakers and Styles](#combining-speakers-and-styles)
- [How Styles Affect Each Voice Type](#how-styles-affect-each-voice-type)
- [Tips and Limitations](#tips-and-limitations)

---

## Choosing a Parsing Mode

| Mode | Use when… | Speaker control |
|---|---|---|
| **Single** | One voice reads the whole script | Assigned via UI dropdown |
| **Paragraphs** | One voice, auto-split on blank lines | Assigned via UI dropdown |
| **Manual** | Multiple voices, you assign per-block | You pick a voice for each block |
| **Annotated** | Multiple speakers, names written in the script | Resolved from voice library by name |

---

## Mode: Single Voice

Paste any text. The entire thing is synthesised as one segment using the voice you select in the UI.

Style tags are still honoured at the very beginning of the text if you want to set a mood for the whole piece.

```
[style: warm and contemplative]
The forest was silent after the storm had passed. Somewhere in the distance,
a branch cracked and fell. She did not flinch.
```

---

## Mode: Paragraphs

The script is split automatically wherever there is a blank line. Each paragraph becomes one segment. All segments use the same voice. Voices are assigned via the UI.

Useful for long monologues where you want the ability to re-generate individual paragraphs independently.

```
It was a cold morning in November when the call finally came.

She had been waiting three years for this. Three years of silence,
of wondering, of almost giving up.

She pressed the green button and brought the phone to her ear.
```

Each blank-line-separated block is its own segment in the results panel.

---

## Mode: Manual Segments

The script is split on blank lines exactly like Paragraphs mode, but **no voice is pre-assigned**. After parsing, the UI shows each block as a segment card and you manually pick a voice for each one from the voice library.

```
[style: excited and breathless]
The package arrived at noon — two days early. She tore it open on the doorstep.

[style: calm, measured]
Inside was a single folded piece of paper and a small brass key.

[style: whispered, ominous]
The note read: "Do not use this before midnight."
```

Style tags are stripped from the spoken text automatically and stored separately — the model never reads out the tag text itself.

---

## Mode: Annotated (Multi-Speaker)

Speaker names are written directly in the script. Each named line starts a new segment attributed to that speaker. After parsing, Qwen-semble maps speaker names to voices in your library.

### Supported annotation formats

All four of these are equivalent and can be mixed in the same script:

```
[Speaker: Alice] Good morning. Did you sleep well?

[Bob] Not really. I kept thinking about what you said yesterday.

(Alice) Well, you probably should have.

Bob: I know. I know.
```

> **Rule:** The annotation must appear at the very start of the line. Everything after it on that line, and any continuation lines that follow (until the next annotation), is treated as the spoken text for that speaker.

### Multi-line dialogue

Continuation lines (no annotation) are appended to the current speaker's segment:

```
Alice: It started simply enough —
a missed call, an unanswered letter,
a door left open just a crack.

Bob: And yet here we are.
```

Alice gets three lines joined into one segment. Bob gets one.

### Speaker name matching

Speaker names in the script are matched **case-sensitively** to voice names in your library. Make sure the name in the script exactly matches the voice name you saved (e.g. `Alice`, not `alice` or `ALICE`), or use the Speaker Assignment panel to map them after parsing.

---

## Style & Emotion Tags

A style tag overrides the delivery of a single segment. It is written as the very first thing in any paragraph or segment:

```
[style: <your direction here>] The spoken text follows here.
```

All three keywords are equivalent — use whichever reads most naturally for you:

```
[style: ...]
[emotion: ...]
[instruct: ...]
```

### Examples

```
[emotion: laughing, barely holding it together]
I swear, I told him not to open the box. I told him!

[style: cold and detached]
There were no survivors.

[instruct: trembling, on the verge of tears]
I just wanted to say goodbye properly. That's all.

[emotion: sarcastic and dismissive]
Oh sure, great plan. Nothing could possibly go wrong.

[style: hushed, reverent — as if in a cathedral]
She placed the letter on the altar and stepped back.
```

### What you can write as the direction

Write it as a natural English description of how the line should be delivered. There is no fixed vocabulary — the model interprets it as free text. Some useful patterns:

| Category | Example values |
|---|---|
| **Emotion** | `angry`, `joyful`, `melancholic`, `terrified`, `tender`, `bitter` |
| **Energy / tempo** | `barely above a whisper`, `excited and fast-paced`, `slow and deliberate` |
| **Physical state** | `laughing`, `crying`, `breathless`, `exhausted` |
| **Stance/attitude** | `sarcastic`, `disinterested`, `conspiratorial`, `triumphant` |
| **Combined** | `warm and slightly amused`, `cold, professional, barely concealing fury` |

Keep directions concise — one to two clauses is more reliable than a paragraph.

### Tag placement rules

- The tag must be at the **very start** of the segment text (before any spoken words).
- Only **one** tag per segment. If you need different emotions in the same paragraph, split it into two paragraphs with a blank line.
- The tag text is **never spoken** — it is stripped before synthesis.

---

## Combining Speakers and Styles

In Annotated mode, place the style tag immediately after the speaker annotation on the same line:

```
[Speaker: Alice] [style: warm and teasing] You're late. Again.

[Speaker: Bob] [emotion: sheepish] The bus was...

[Speaker: Alice] [style: deadpan] Don't.
```

In Manual mode, put the style tag at the very start of the block:

```
[emotion: urgent, conspiratorial]
Alice: Meet me at the corner of Fifth and Maple.
Don't tell anyone you're coming.

[style: casual, unbothered]
Bob: Sure. Want me to bring coffee?
```

---

## Combining Speakers and Styles — Full Example

Below is a complete annotated script ready to paste:

```
[Speaker: Narrator] [style: quiet, like a bedtime story]
It was the kind of evening that made you believe anything was possible.
The city hummed with a low, distant energy.

[Speaker: Elena] [emotion: excited, hushed]
I found it. The address. It's real — it actually exists.

[Speaker: Marcus] [style: skeptical, arms folded]
You've said that before. Three times, in fact.

[Speaker: Elena] [emotion: indignant]
This time I have proof. Look at this.

[Speaker: Marcus] [style: long pause, then quietly stunned]
That can't be right.

[Speaker: Narrator] [style: contemplative, fading]
But it was. And neither of them would ever be quite the same again.
```

---

## How Styles Affect Each Voice Type

The style tag works differently depending on which kind of voice is assigned to the segment.

### Designed voices (VoiceDesign model)

The style is combined with the voice's saved description and passed as the `instruct` field — the model's primary mechanism for controlling delivery. This gives the **most reliable** emotion/style results.

The combination is: `<your style tag>. <saved voice description>`

So a segment tagged `[emotion: angry]` with a voice described as `"warm, middle-aged male narrator"` is sent as:

> `angry. warm, middle-aged male narrator`

### Cloned voices (Base model)

The Base model has no `instruct` field. Instead, the style is prepended to the spoken text as a parenthetical hint the model can follow:

> `(angry) The spoken text goes here.`

This approach generally works but is less consistent than the VoiceDesign path. For highly expressive delivery (strong laughter, sobbing, shouting), a Designed voice will produce more predictable results.

---

## Tips and Limitations

**Keep segments reasonably short.** Very long segments (>200 words) can drift in tone. If the style matters throughout a long passage, break it into shorter paragraphs.

**One style per segment.** If a line transitions from sad to angry mid-sentence, split it into two segments — one with each style.

**Style cannot override the cloned voice's base character.** If a cloned voice sounds inherently calm, asking it to `[style: screaming rage]` will move it in that direction but not all the way there. Designed voices generally have a wider range.

**Speaker names are literal strings.** `Bob` and `bob` are different speakers. Check capitalisation matches your voice library.

**The UI Style field overrides the inline tag.** Each segment in the results panel has a **Style** text field. If you type something there and re-generate the segment, that value takes precedence over whatever was in the original script tag.

**Blank lines are structural.** In Manual, Paragraphs, and Annotated modes, a blank line always ends the current segment. Do not use blank lines within dialogue you want to stay together as one segment.
