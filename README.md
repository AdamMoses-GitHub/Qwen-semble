# Qwen-semble - TTS Voice Studio

*Because manually recording audiobooks is like writing code in assembly – technically possible, but why would you?*

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.12+-brightgreen)

<!-- ![App Screenshot](INSERT_IMAGE_URL_HERE) -->

A powerful desktop application for **voice cloning**, **voice design**, and **multi-voice narration** powered by Alibaba's Qwen3-TTS models. Clone any voice from a short audio sample, create custom voices from text descriptions, or generate professional narrations with multiple voices.

<!-- ![App Screenshot](INSERT_IMAGE_URL_HERE) -->

A powerful desktop application for **voice cloning**, **voice design**, and **multi-voice narration** powered by Alibaba's Qwen3-TTS models. Clone any voice from a short audio sample, create custom voices from text descriptions, or generate professional narrations with multiple voices.

**🔗 Repository**: https://github.com/AdamMoses-GitHub/Qwen-semble

---

## About

### The Problem
Recording narrations, audiobooks, or multi-voice content is time-consuming and expensive. You need voice actors, recording equipment, studios, and hours of post-production. Consistency across recording sessions is nearly impossible.

### The Solution
Qwen-semble lets you clone any voice from a 3-60 second sample, design custom voices from text descriptions, and generate professional multi-voice narrations – all on your local machine with state-of-the-art AI models.

---

## What It Does

### The Main Features

🎙️ **Voice Cloning** - Clone any voice from a short audio sample  
🎨 **Voice Design** - Create custom voices from natural language descriptions  
📖 **Multi-Voice Narration** - Generate narrations with multiple distinct voices  
💾 **Voice Library** - Save and organize your cloned and designed voices  
⚙️ **Flexible Configuration** - CPU or GPU, multiple model sizes, advanced tuning

### The Nerdy Stuff

✨ **State-of-the-Art Models** - Powered by Qwen3-TTS (Alibaba Cloud)  
🚀 **GPU Acceleration** - CUDA support with FlashAttention optimization  
🎯 **Zero-Dependency Voice Clone** - X-Vector mode requires no transcript  
🌍 **Multilingual** - 11 languages including Chinese, English, Japanese, Korean  
💻 **100% Local** - All processing happens on your machine, private by design

---

## Quick Start

### TL;DR Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/Qwen-semble.git
cd Qwen-semble

# GPU users (Windows):
install-gpu.bat

# CPU users (Windows):
install-cpu.bat

# Run it
python src/main.py
```

**📖 Full Installation Guide**: See [INSTALL.md](INSTALL.md) for detailed instructions, troubleshooting, and platform-specific setup.

**First launch downloads ~7GB of AI models** (one-time, takes 10-30 min depending on internet speed)

---

## Tech Stack

| Component | Purpose | Why This One |
|-----------|---------|--------------|
| **Qwen3-TTS** | Voice synthesis engine | State-of-the-art quality, multilingual, local processing |
| **PyTorch** | Deep learning framework | Industry standard, CUDA support, model compatibility |
| **CustomTkinter** | GUI framework | Modern UI, cross-platform, Python-native |
| **Transformers** | Model loading & inference | HuggingFace ecosystem, easy model management |
| **SoundFile/SoundDevice** | Audio I/O | Format support, low-latency playback |

---

## System Requirements

**Minimum (CPU Mode)**:
- Python 3.12+
- 8GB RAM
- 10GB disk space
- Any modern CPU

**Recommended (GPU Mode)**:
- Python 3.12+
- 16GB RAM
- NVIDIA GPU with 8GB+ VRAM
- CUDA 12.1+
- 15GB disk space

**Supported OS**: Windows (tested), Linux, macOS

---

## Usage

For complete usage instructions, workflows, and best practices, see **[USAGE.md](USAGE.md)**.

### Quick Examples

**Clone a voice:**
1. Voice Clone tab → Select audio file (3-60 sec)
2. Enter transcript of what was said
3. Type new text → Generate

**Design a voice:**
1. Voice Design tab → Describe voice: "Young male, confident, slightly deep"
2. Enter test text → Generate Voice

**Multi-voice narration:**
1. Narration tab → Load transcript with `[Speaker]` tags
2. Select "annotated" mode → Parse
3. Generate Narration

---

## Documentation

- **[INSTALL.md](INSTALL.md)** - Complete installation guide
- **[USAGE.md](USAGE.md)** - User guide, workflows, best practices
- **[LICENSE](LICENSE)** - MIT License

---

## Contributing

Contributions welcome! Areas where you can help:

- 📄 Add DOCX/PDF transcript support
- 💾 Voice profile export/import
- 🎵 MP3 export support
- 🎤 Whisper integration for auto-transcription
- ⚡ Batch processing for multiple files
- 🔊 Real-time streaming generation

---

## License

MIT License - See [LICENSE](LICENSE) for details.

Copyright © 2026 Adam Moses

---

## Acknowledgments

- **[Qwen Team](https://github.com/QwenLM/Qwen3-TTS)** at Alibaba Cloud for the incredible Qwen3-TTS models
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** for the modern GUI framework
- **[HuggingFace](https://huggingface.co/)** for model hosting and transformers library

---

## Support

**Need help?**
- 📖 Read [USAGE.md](USAGE.md) for tutorials
- 🐛 [Open an issue](https://github.com/yourusername/Qwen-semble/issues)
- 💬 Check existing issues for solutions

---

<sub>Keywords: voice cloning, text-to-speech, TTS, voice synthesis, voice design, multi-voice narration, audiobook generation, Qwen3-TTS, speech generation, voice AI, local TTS, CUDA acceleration, Python TTS, voice library, speaker cloning, custom voice, narration generator, audio synthesis, deep learning voice, AI voice studio</sub>

