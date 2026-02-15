# Usage Guide

Complete guide to using Qwen-semble TTS Voice Studio for voice cloning, voice design, and multi-voice narration.

## Table of Contents

- [First Launch](#first-launch)
- [Interface Overview](#interface-overview)
- [Voice Cloning](#voice-cloning)
- [Voice Design](#voice-design)
- [Multi-Voice Narration](#multi-voice-narration)
- [Voice Library Management](#voice-library-management)
- [Configuration & Settings](#configuration--settings)
- [Output Files](#output-files)
- [Best Practices](#best-practices)
- [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)

---

## First Launch

### Starting the Application

```bash
python src/main.py
```

Or double-click **`run.bat`** (Windows)

### First Run Setup

On first launch:

1. **Model Download** (~7GB, one-time only):
   - Application downloads Qwen3-TTS models from HuggingFace
   - Progress shown in terminal/console
   - Takes 10-30 minutes depending on internet speed
   - Models cached in: `~/.cache/huggingface/hub/`

2. **Model Loading**:
   - Application loads CustomVoice model into memory
   - Takes 30-120 seconds depending on device
   - GPU: faster, CPU: slower but works

3. **Main Window Opens**:
   - All tabs are now active and ready to use

### Initial Configuration (Recommended)

1. **Go to Settings Tab**

2. **Select Device**:
   - **GPU** (if you have NVIDIA GPU) - Fast, recommended
   - **CPU** (fallback) - Slower but always works

3. **Choose Model Size**:
   - **1.7B** - Best quality (default), needs 8GB+ VRAM
   - **0.6B** - Faster generation, needs 4GB+ VRAM

4. **Optional: Add HuggingFace Token** (if models fail to download):
   - Get free token: https://huggingface.co/settings/tokens
   - Paste into "Token" field
   - Click "Save Token"

---

## Interface Overview

### Tabs

1. **Voice Clone** - Clone voices from audio samples
2. **Voice Design** - Create custom voices from descriptions
3. **Narration** - Generate multi-voice narrations
4. **Settings** - Configure application, models, and generation parameters

### Status Indicators

- **Progress Bars** - Show generation/loading progress
- **Status Messages** - Show current operation
- **Audio Player** - Play generated audio inline
- **Log Output** - Detailed logs in `output/logs/app.log`

---

## Voice Cloning

### When to Use Voice Cloning

- Clone a specific person's voice from a sample
- Recreate historical voices from recordings
- Generate speech in a specific accent or style
- Create consistent voice across multiple projects

### Workflow

#### Step 1: Select Reference Audio

1. Click **"Browse..."** in Voice Clone tab
2. Select audio file (3-60 seconds recommended)
3. **Supported formats**: WAV, MP3, FLAC, OGG, M4A
4. Audio info displays: duration, format

**Best Practices**:
- ✅ 10-30 seconds is ideal
- ✅ Clear speech, minimal background noise
- ✅ Single speaker only
- ✅ Sample rate 16kHz or higher
- ❌ Avoid music, overlapping speech, or heavy noise

#### Step 2: Enter Reference Transcript

1. Type exactly what is said in the reference audio
2. Punctuation and capitalization matter for quality
3. **Or**: Enable "X-Vector Only Mode" (checkbox)
   - Skips transcript requirement
   - Lower quality but faster
   - Good for simple voice matching

**Example**:
```
"Hello, my name is John. I'm recording this sample for voice cloning."
```

#### Step 3: Enter Generation Text

1. Type the text you want spoken in the cloned voice
2. Select target **Language** (or "Auto" for detection)
3. Length: 10-500 words (longer = slower)

**Example Use Case**:
```
You have a 15-second Obama speech clip. You enter the transcript of that clip, 
then generate new text like "Welcome to my podcast where we discuss technology 
and innovation." The output sounds like Obama saying your custom text.
```

#### Step 4: Generate Speech

1. Click **"Generate Speech"** button
2. Wait for generation (10-60 seconds)
3. Progress bar shows status
4. **Time estimates**:
   - GPU (1.7B): 5-15 seconds for 50 words
   - GPU (0.6B): 2-8 seconds for 50 words
   - CPU (1.7B): 30-90 seconds for 50 words
   - CPU (0.6B): 15-45 seconds for 50 words

#### Step 5: Review & Save

1. Click **"▶ Play Result"** to listen
2. Iterate if needed (adjust text, try different reference audio)
3. **Save Options**:
   - **"Save Audio"** - Export as WAV file
   - **"Save to Voice Library"** - Reuse voice later

### Saving to Voice Library

When you click "Save to Voice Library":

1. **Enter Voice Name**: e.g., "Obama Voice", "Customer Service Rep"
2. **Add Tags** (optional): e.g., "male", "political", "formal"
3. Click **"Save"**

**What Gets Saved**:
- Voice clone prompt (the AI's understanding of the voice)
- Reference audio file
- Reference transcript
- Metadata (name, tags, language)

**Where It's Saved**:
- Files: `output/cloned_voices/cloned_XXX.wav` + `cloned_XXX_prompt.pkl`
- Metadata: `config/voice_library.json`

**Reusing Saved Voices**:
- In Narration tab, saved voices appear in dropdown as `[Library] VoiceName`
- Select them like preset voices
- Generation uses saved voice prompt (no need to re-clone)

---

## Voice Design

### When to Use Voice Design

- Create a voice from scratch without a reference sample
- Experiment with voice characteristics
- Generate voices for fictional characters
- Quick prototyping of voice concepts

### Workflow

#### Step 1: Describe the Voice

Write a natural language description in the text box.

**Description Format**:
```
[Age & Gender], [Personality/Tone], [Technical Characteristics]
```

**Examples**:

```
Young female voice, cheerful and energetic, slightly high pitch
```

```
Middle-aged male voice, authoritative news anchor tone, deep and confident
```

```
Elderly female voice, warm grandmother tone, gentle and comforting
```

```
Teen male voice, slightly shy and nervous, tenor range with occasional voice breaks
```

**Tips**:
- Be specific: age, gender, tone, pitch, pace
- Describe personality: cheerful, serious, warm, cold, energetic
- Mention technical traits: deep, high-pitched, raspy, smooth, fast, slow
- Use reference professions: news anchor, teacher, therapist
- Click **"Load Example Prompt"** for inspiration

#### Step 2: Enter Test Text

1. Type text to test the voice (50-200 words recommended)
2. Select **Language** (or "Auto")

**Example**:
```
Hello, this is a test of the voice design feature. I'm demonstrating 
how the designed voice sounds with different types of sentences.
```

#### Step 3: Generate Voice

1. Click **"Generate Voice"**
2. Wait for generation (10-60 seconds)
3. Listen to result

#### Step 4: Iterate

Voice design is iterative:

1. Listen to result
2. Adjust description:
   - Too monotone? Add "expressive" or "dynamic"
   - Too aggressive? Add "gentle" or "calm"
   - Wrong pitch? Specify "alto", "tenor", "bass"
3. Regenerate
4. Repeat until satisfied

#### Step 5: Save to Library

Once you're happy:

1. Click **"Save to Library"**
2. Enter name and tags
3. Voice is saved for reuse in Narration tab

**Note**: Designed voices regenerate from description each time in narration (may vary slightly between generations).

---

## Multi-Voice Narration

### When to Use Narration

- Audiobook generation with narrator + character voices
- Podcast/dialogue content with multiple speakers
- Educational content with teacher + student
- Interviews, scripts, or plays

### Three Narration Modes

| Mode | Use Case | Input Format |
|------|----------|--------------|
| **Single Voice** | One narrator for entire transcript | Plain text |
| **Manual** | Assign voices to individual sentences | Plain text, manual assignment |
| **Annotated** | Multiple speakers with tags in transcript | `[Speaker] Text` format |

---

### Mode 1: Single Voice Narration

**Use Case**: Audiobook, article, or content with one consistent voice

#### Workflow

1. **Load/Paste Transcript**:
   - Click "Load Transcript File (.txt)" OR
   - Paste text directly into text box

2. **Select Mode**: "**single**"

3. **Choose Voice**:
   - Select from dropdown:
     - Preset voices (Ryan, Vivian, Serena, etc.)
     - `[Library]` voices (your saved voices)

4. **Parse Transcript**:
   - Click "Parse Transcript"
   - Shows statistics: word count, sentence count

5. **Generate Narration**:
   - Click "Generate Narration"
   - Progress bar shows sentence-by-sentence progress
   - Can cancel mid-generation if needed

6. **Output**:
   - Merged audio saved to: `output/narrations/narration_YYYYMMDD_HHMMSS/narration_full.wav`

**Example**:
```
The quick brown fox jumps over the lazy dog. This is a sample transcript 
for testing single voice narration. All text will be spoken by one voice.
The application automatically splits into sentences and generates each 
segment before merging them into a single audio file.
```

---

### Mode 2: Manual Multi-Voice Narration

**Use Case**: Want precise control over which voice says which sentence

#### Workflow

1. **Load Transcript** (plain text without speaker tags)

2. **Select Mode**: "**manual**"

3. **Parse Transcript**:
   - Click "Parse Transcript"
   - Transcript splits into individual sentences
   - Right panel shows sentence list (up to 50 visible)

4. **Assign Voices**:
   - Each sentence has a dropdown
   - Select voice for each sentence:
     - Preset voices: Ryan, Vivian, etc.
     - Library voices: [Library] VoiceName
   - **Tip**: Can assign same voice to multiple sentences

5. **Generate Narration**:
   - Click "Generate Narration"
   - Each sentence generates with assigned voice

**Example Transcript**:
```
Welcome to our podcast.
Today we're discussing voice cloning technology.
It's truly fascinating how far this field has come.
Let's dive into the details.
```

**Manual Assignment**:
- Sentence 1: Ryan (host voice)
- Sentence 2: Ryan
- Sentence 3: Vivian (guest voice)
- Sentence 4: Ryan

---

### Mode 3: Annotated Format Narration

**Use Case**: Script with clear speakers, dialogue, interviews, plays

#### Workflow

1. **Prepare Annotated Transcript**:

Format:
```
[SpeakerName] Dialogue text here.
[AnotherSpeaker] Their response.
```

**Example**:
```
[Ryan] Hello everyone, welcome to the show.
[Vivian] Thanks for having me, Ryan. Great to be here.
[Ryan] Today we're talking about voice cloning. What's your take on this technology?
[Vivian] I think it's revolutionary. The ability to clone any voice opens up so many possibilities.
[Ryan] Absolutely. Let's explore some use cases.
```

**Speaker Name Rules**:
- Use speaker names that match preset voices (Ryan, Vivian, Serena, etc.) OR
- Use names of voices in your library (must match exactly) OR
- Use any name and manually map later

2. **Load Transcript**

3. **Select Mode**: "**annotated**"

4. **Parse Transcript**:
   - Click "Parse Transcript"
   - Application auto-detects speakers
   - Shows: "Detected speakers: Ryan, Vivian"

5. **Verify Voice Mapping**:
   - Application auto-maps names to voices:
     - "Ryan" → preset voice "Ryan"
     - "CustomVoiceName" → [Library] CustomVoiceName
   - If name not found, shows error

6. **Generate Narration**:
   - Click "Generate Narration"
   - Each line generates with assigned speaker's voice

**Pro Tip**: Use preset speaker names in your transcript for automatic mapping:
- Ryan, Aiden (English male)
- Vivian, Serena (Chinese female)
- Ono_Anna (Japanese female)
- Sohee (Korean female)
- Dylan (Beijing Chinese male)
- Eric (Sichuan Chinese male)
- Uncle_Fu (older Chinese male)

---

### Available Preset Voices

| Name | Description | Language |
|------|-------------|----------|
| **Ryan** | Dynamic male, rhythmic drive | English |
| **Aiden** | Sunny American male, clear | English |
| **Vivian** | Bright young female | Chinese |
| **Serena** | Warm gentle female | Chinese |
| **Dylan** | Youthful Beijing male | Chinese (Beijing) |
| **Eric** | Lively Chengdu male | Chinese (Sichuan) |
| **Uncle_Fu** | Seasoned male, low & mellow | Chinese |
| **Ono_Anna** | Playful female, light | Japanese |
| **Sohee** | Warm female, rich emotion | Korean |

**Plus**: All your saved cloned and designed voices appear as `[Library] VoiceName`

---

## Voice Library Management

### Viewing Saved Voices

- Voice Clone tab: "Library" section shows cloned voices
- Voice Design tab: "Designed Voices" section shows designed voices
- Both appear in Narration tab dropdown as `[Library] Name`

### Managing Voices

**Play Sample**: Click "▶" button to preview voice

**Load Voice**: 
- Click "Load" to reuse in current tab
- For cloned voices: loads reference audio and prompt
- For designed voices: loads description

**Delete Voice**:
- Click "Delete" (⚠️ permanent!)
- Removes files and metadata

**Refresh Library**: Click "Refresh Library" button to reload list

### Voice Library Files

**Cloned Voices**:
```
output/cloned_voices/
├── cloned_001.wav         (reference audio)
├── cloned_001_prompt.pkl  (voice characteristics)
├── cloned_002.wav
└── cloned_002_prompt.pkl
```

**Designed Voices**:
```
output/designed_voices/
├── designed_001.wav       (sample audio)
└── designed_002.wav
```

**Metadata**:
```
config/voice_library.json  (names, tags, paths)
```

---

## Configuration & Settings

### Settings Tab Overview

Access via the "Settings" tab in the main window.

### Device Selection

**Options**:
- **CPU** - Works on any computer, slower
- **cuda:0** - NVIDIA GPU (if available), faster

**When to use CPU**:
- No NVIDIA GPU available
- GPU memory issues (CUDA OOM errors)
- Testing/debugging

**When to use GPU**:
- Have NVIDIA GPU with 8GB+ VRAM
- Want faster generation (5-10x speedup)
- Processing large batches

**Reload Required**: Click "Reload Models" after changing

### Model Size

**Options**:
- **1.7B** - Best quality, needs 8GB+ VRAM (GPU) or 16GB+ RAM (CPU)
- **0.6B** - Faster, needs 4GB+ VRAM (GPU) or 8GB+ RAM (CPU)

**Trade-offs**:
- 1.7B: Better voice quality, more natural, but slower
- 0.6B: Faster generation (2x), slightly lower quality

**Reload Required**: Click "Reload Models" after changing

### Flash Attention

**Option**: Enable/Disable checkbox

**What it does**:
- Optimizes GPU memory usage (20-30% improvement)
- Slightly faster generation on supported GPUs

**Requirements**:
- Must be installed (`pip install flash-attn`)
- Only works on GPU with compute capability 7.5+ (RTX 20 series and newer)

**If disabled**: Uses standard attention (works everywhere)

### Generation Parameters

**max_new_tokens** (1024-4096):
- Maximum audio tokens to generate
- Higher = longer output possible
- Default: 2048 (good for most cases)

**Temperature** (0.1-1.5):
- Controls randomness/creativity
- Low (0.5): More consistent, robotic
- High (1.0): More expressive, varied
- Default: 0.7

**Top P** (0.5-1.0):
- Nucleus sampling parameter
- Lower = more focused/predictable
- Higher = more diverse
- Default: 0.9

### HuggingFace Authentication

**When needed**:
- First model download
- Some models require authentication
- Private/gated models

**Setup**:
1. Get token: https://huggingface.co/settings/tokens
2. Paste in "Token" field
3. Click "Validate Token" (optional check)
4. Click "Save Token"

**Token storage**: Securely stored in `~/.cache/huggingface/token`

---

## Output Files

### Directory Structure

```
output/
├── cloned_voices/
│   ├── cloned_001.wav
│   └── cloned_001_prompt.pkl
├── designed_voices/
│   └── designed_001.wav
├── narrations/
│   └── narration_20260215_103045/
│       └── narration_full.wav
├── temp/
│   └── [temporary files, auto-cleaned]
└── logs/
    └── app.log
```

### Narration Output

**Location**: `output/narrations/narration_YYYYMMDD_HHMMSS/`

**Files**:
- `narration_full.wav` - Complete merged audio

**Format**: WAV, 12kHz sample rate, mono

### Logs

**Location**: `output/logs/app.log`

**Contents**:
- Application startup/shutdown events
- Model loading progress
- Generation operations
- Errors and warnings

**Use for troubleshooting**: Check logs if app crashes or behaves unexpectedly

---

## Best Practices

### Voice Cloning Best Practices

✅ **DO**:
- Use 10-30 second samples (sweet spot)
- Ensure clear, high-quality audio
- Match reference language to generation language
- Provide accurate transcripts (word-for-word)
- Use isolated speech (one person, minimal background noise)

❌ **DON'T**:
- Use samples with music or heavy background noise
- Use samples with multiple overlapping speakers
- Expect perfect cloning from 1-2 second samples
- Generate very long text (>500 words) in one go

### Voice Design Best Practices

✅ **DO**:
- Be specific with descriptions
- Iterate and refine based on results
- Use example prompts as inspiration
- Mention age, gender, tone, pitch
- Test with varied text to hear consistency

❌ **DON'T**:
- Use vague descriptions like "nice voice"
- Expect identical results between generations
- Describe visual characteristics (face, appearance)

### Narration Best Practices

✅ **DO**:
- Break long transcripts into chapters/sections
- Use annotated format for clear dialogue
- Proofread transcripts (punctuation matters!)
- Test with short sample before full generation
- Save intermediate progress

❌ **DON'T**:
- Generate 50+ minute narrations in one session (risk of crash)
- Use special characters in speaker names
- Mix languages heavily in one narration
- Skip sentence parsing review

---

## Performance Tips

### Speed Up Generation

1. **Use GPU instead of CPU** (5-10x faster)
2. **Use 0.6B model** instead of 1.7B (2x faster)
3. **Break long text into chunks** (parallel processing possible)
4. **Close other GPU applications** (games, video editing)
5. **Install Flash Attention** (20-30% speedup on GPU)

### Reduce Memory Usage

1. **Use CPU mode** (uses RAM instead of VRAM)
2. **Use 0.6B model** (smaller memory footprint)
3. **Close other applications** (web browsers, etc.)
4. **One model at a time** (don't load multiple models)

### Improve Quality

1. **Use 1.7B model** (better than 0.6B)
2. **Use GPU** (better precision than CPU)
3. **Higher quality reference audio** (16kHz+ sample rate)
4. **Accurate transcripts** (for voice cloning)
5. **Detailed descriptions** (for voice design)

---

## Troubleshooting

### Generation Issues

**Problem**: "Generation failed" error

**Solutions**:
1. Check text length (try shorter text)
2. Check special characters (remove emojis, symbols)
3. Verify model is loaded (Settings tab)
4. Check logs: `output/logs/app.log`
5. Try different voice
6. Restart application

**Problem**: Audio is clipped/cut off

**Solution**: Increase `max_new_tokens` in Settings (try 3072 or 4096)

**Problem**: Voice doesn't match reference

**Solutions**:
1. Use longer reference audio (20-30 seconds)
2. Provide accurate transcript
3. Disable X-Vector mode (provide transcript)
4. Use cleaner reference audio
5. Try regenerating (some randomness)

### Performance Issues

**Problem**: Generation takes forever (>5 minutes)

**Solutions**:
1. Switch from CPU to GPU (if available)
2. Use 0.6B model instead of 1.7B
3. Reduce text length
4. Check CPU/GPU usage (close other apps)
5. Reduce batch size (split narration)

**Problem**: Application freezes during generation

**Solutions**:
1. Check Task Manager/Activity Monitor (is it actually frozen or just slow?)
2. Wait longer (first generation can take time)
3. Check logs for errors
4. Restart application
5. Try CPU mode if GPU mode freezes

### Audio Issues

**Problem**: No sound when playing audio

**Solutions**:
1. Check system volume
2. Check application isn't muted
3. Try saving audio and playing externally
4. Check audio output device in system settings

**Problem**: Audio is distorted or robotic

**Solutions**:
1. Lower temperature in Settings (try 0.5)
2. Use 1.7B model instead of 0.6B
3. Provide better reference audio (for cloning)
4. Refine voice description (for design)
5. Check sample rate of output (should be 12kHz)

### Error Messages

**"CUDA out of memory"**:
- Switch to 0.6B model
- Switch to CPU mode
- Close other GPU applications
- Reduce max_new_tokens

**"Model not found"**:
- Check internet connection
- Add HuggingFace token in Settings
- Manually download: `huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`

**"Audio file not supported"**:
- Convert to WAV, MP3, or FLAC
- Check sample rate (needs 16kHz+)
- Check file isn't corrupted

**"Voice not found in library"**:
- Refresh voice list (Settings tab)
- Check `config/voice_library.json` file exists
- Verify voice files in `output/cloned_voices/` or `output/designed_voices/`

---

## Advanced Usage

### Batch Processing (Manual)

To process multiple transcripts:

1. Generate each narration separately
2. Save output files with descriptive names
3. Merge externally with audio editing software (Audacity, etc.)

### Exporting Voices

To backup or share voices:

1. Copy entire `output/cloned_voices/` or `output/designed_voices/` folder
2. Copy `config/voice_library.json`
3. On new installation: paste folders and JSON file in same locations

### Custom Generation Parameters

Edit `config/app_config.json` directly for advanced control:

```json
{
  "generation_params": {
    "max_new_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "do_sample": true,
    "repetition_penalty": 1.0
  }
}
```

**Restart application** after editing.

---

## Support

**Need more help?**

1. Check [INSTALL.md](INSTALL.md) for installation issues
2. Review logs: `output/logs/app.log`
3. Search existing issues on GitHub
4. Open new issue with:
   - Error message
   - Log excerpt
   - Steps to reproduce
   - System info (OS, GPU, Python version)

---

**Happy voice generating! 🎙️**
