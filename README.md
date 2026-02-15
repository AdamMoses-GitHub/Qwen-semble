# Qwen-semble - TTS Voice Studio

A powerful desktop application for voice cloning, voice design, and multi-voice transcript narration powered by Qwen3-TTS models.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.12+-brightgreen)

## Features

### 🎙️ Voice Cloning
- Clone any voice from a 3-60 second audio sample
- Save cloned voices to a persistent library for reuse
- X-Vector mode for quick cloning without transcripts
- Support for multiple audio formats (WAV, MP3, FLAC, OGG, M4A)

### 🎨 Voice Design
- Create custom voices from natural language descriptions
- Example: "Young female voice, cheerful and energetic, slightly high pitch"
- Test voices with custom text before saving
- Save designed voices to library with metadata

### 📖 Multi-Voice Narration
- Generate narrations from plain text transcripts
- Three voice assignment modes:
  - **Single Voice**: One voice narrates entire transcript
  - **Manual Multi-Voice**: Assign voices to individual sentences
  - **Annotated Format**: Use `[Speaker: Name]` tags in transcript
- Automatic speaker detection from annotations
- Merge segments into single audio file or save separately
- Progress tracking with cancellation support

### 💾 Voice Library
- Persistent storage for cloned and designed voices
- Name and tag voices for easy organization
- Load, play, and delete voices
- Export/import voice profiles (planned)

### ⚙️ Advanced Configuration
- CPU or GPU execution (CUDA support)
- Model size selection (0.6B or 1.7B parameters)
- FlashAttention 2 for GPU memory optimization
- Customizable generation parameters (temperature, top_p, max_tokens)
- HuggingFace token management for model downloads
- Light/Dark/System theme support

## Requirements

- **Python**: 3.12 or higher
- **Operating System**: Windows (tested), Linux, macOS (should work)
- **Hardware**:
  - **CPU Mode**: Any modern CPU with 8GB+ RAM
  - **GPU Mode**: NVIDIA GPU with 8GB+ VRAM (16GB+ recommended for 1.7B model)
  - **Storage**: 10GB+ free space for models and outputs

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Qwen-semble.git
cd Qwen-semble
```

### 2. Create Virtual Environment (Recommended)

```bash
# Using conda
conda create -n qwen-tts python=3.12 -y
conda activate qwen-tts

# Or using venv
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies

**Option A: GPU Version (Recommended for NVIDIA GPUs with CUDA 12.1+)**

Windows:
```bash
# Run automated installer
install-gpu.bat
```

Manual installation:
```bash
# Step 1: Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Step 2: Install other dependencies
pip install -r requirements-gpu.txt

# Step 3 (Optional): Install Flash Attention for better GPU performance
pip install flash-attn --no-build-isolation
```

**Option B: CPU Version (No GPU required)**

Windows:
```bash
# Run automated installer
install-cpu.bat
```

Manual installation:
```bash
pip install -r requirements-cpu.txt
```

**Verify CUDA is available (GPU version only):**
```bash
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
```

## Quick Start

### Running the Application

```bash
python src/main.py
```

On first launch, the application will:
1. Download required Qwen3-TTS models from HuggingFace (~7GB for 1.7B model)
2. Initialize the TTS engine
3. Open the main window

### First-Time Setup

1. **Configure Device** (Settings tab):
   - Select GPU if available, or CPU for compatibility
   - Choose model size (1.7B for best quality, 0.6B for speed)

2. **(Optional) Add HuggingFace Token** (Settings tab):
   - Required for downloading models on first run
   - Get token at: https://huggingface.co/settings/tokens
   - Paste token and click "Save Token"

## Usage Guide

### Voice Cloning

1. **Select Reference Audio**:
   - Click "Browse..." to select an audio file (3-60 seconds recommended)
   - Supported formats: WAV, MP3, FLAC, OGG, M4A

2. **Enter Reference Transcript**:
   - Type what is said in the reference audio
   - Or enable "X-Vector Only Mode" to skip (lower quality)

3. **Enter Text to Generate**:
   - Type the text you want spoken in the cloned voice
   - Select target language (or "Auto")

4. **Generate**:
   - Click "Generate Speech"
   - Wait for processing (may take 10-60 seconds)
   - Listen to result with "Play Result" button

5. **Save** (optional):
   - "Save Audio" - Export as WAV file
   - "Save to Voice Library" - Reuse voice later with custom name/tags

### Voice Design

1. **Describe Voice**:
   - Write a natural language description of the voice you want
   - Click "Load Example Prompt" for inspiration

2. **Enter Test Text**:
   - Provide sample text to test the designed voice
   - Select language

3. **Generate Voice**:
   - Click "Generate Voice"
   - Listen to result and iterate on description if needed

4. **Save to Library**:
   - Save successful designs for reuse

### Multi-Voice Narration

#### Single Voice Mode

1. Load transcript (.txt file) or paste text
2. Select "single" mode
3. Choose voice from dropdown
4. Click "Parse Transcript"
5. Click "Generate Narration"

#### Manual Multi-Voice Mode

1. Load transcript
2. Select "manual" mode
3. Click "Parse Transcript" - transcript splits into sentences
4. Assign voice to each sentence in right panel
5. Click "Generate Narration"

#### Annotated Format Mode

1. Prepare transcript with speaker tags:
   ```
   [Ryan] Hello, how are you today?
   [Vivian] I'm doing great, thanks for asking!
   [Ryan] That's wonderful to hear.
   ```

2. Load transcript
3. Select "annotated" mode
4. Click "Parse Transcript" - speakers auto-detected
5. Click "Generate Narration"

Generated narrations are saved to `output/narrations/narration_YYYYMMDD_HHMMSS/`

## Configuration

### Config Files

- `config/app_config.json` - Application settings
- `config/voice_library.json` - Saved voices metadata

### Output Directory Structure

```
output/
├── cloned_voices/          # Saved cloned voices
├── designed_voices/        # Saved designed voices
├── narrations/            # Generated narrations
│   └── narration_YYYYMMDD_HHMMSS/
│       └── narration_full.wav
├── temp/                  # Temporary files
└── logs/                  # Application logs
    └── app.log
```

## Troubleshooting

### Models Won't Download

**Problem**: "Failed to download model" error

**Solutions**:
- Check internet connection
- Add HuggingFace token in Settings if model requires authentication
- Try again - sometimes HuggingFace servers are temporarily unavailable

### GPU Out of Memory

**Problem**: "CUDA out of memory" error

**Solutions**:
1. Switch to CPU mode in Settings (slower but works)
2. Use 0.6B model instead of 1.7B
3. Close other GPU-using applications
4. Reduce text length for generation

### Audio File Not Supported

**Problem**: "Unsupported audio format" error

**Solutions**:
- Convert audio to WAV, MP3, or FLAC format
- Ensure sample rate is at least 16kHz
- Check that audio is between 1-120 seconds

### Generation is Slow

**Problem**: Audio generation takes minutes

**Expected Behavior**:
- **GPU (1.7B model)**: 2-10 seconds for short text
- **GPU (0.6B model)**: 1-5 seconds for short text
- **CPU (1.7B model)**: 30-120 seconds for short text
- **CPU (0.6B model)**: 15-60 seconds for short text

**Solutions**:
- Use GPU if available
- Use 0.6B model for faster generation
- Check no other processes are using GPU/CPU

### Application Crashes on Startup

**Problem**: Application closes immediately or shows errors

**Solutions**:
1. Check Python version (requires 3.12+):
   ```bash
   python --version
   ```

2. Reinstall dependencies:
   ```bash
   # For GPU version:
   pip install -r requirements-gpu.txt --force-reinstall
   # For CPU version:
   pip install -r requirements-cpu.txt --force-reinstall
   ```

3. Check logs:
   ```
   output/logs/app.log
   ```

4. Try CPU mode by editing `config/app_config.json`:
   ```json
   {
     "device": "cpu",
     ...
   }
   ```

## Supported Languages

- Chinese (including dialects: Beijing, Sichuan)
- English
- Japanese
- Korean
- German
- French
- Russian
- Portuguese
- Spanish
- Italian

## Models Used

- **Qwen3-TTS-12Hz-1.7B-CustomVoice** - Preset speaker voices
- **Qwen3-TTS-12Hz-1.7B-VoiceDesign** - Voice creation from descriptions
- **Qwen3-TTS-12Hz-1.7B-Base** - Voice cloning
- **Qwen3-TTS-Tokenizer-12Hz** - Audio encoding/decoding

Models are automatically downloaded from HuggingFace on first use.

## Contributing

Contributions are welcome! Areas for improvement:

- [ ] Add support for DOCX/PDF transcript formats
- [ ] Implement voice profile export/import
- [ ] Add audio format conversion (MP3 export)
- [ ] Integration with Whisper for auto-transcription
- [ ] Batch processing for multiple transcripts
- [ ] Real-time streaming generation
- [ ] Speaker diarization for automatic voice assignment

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Qwen Team** at Alibaba Cloud for the amazing [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) models
- **CustomTkinter** for the modern GUI framework
- **HuggingFace** for model hosting and transformers library

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing issues for solutions
- Review documentation at [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)

## Changelog

### Version 1.0.0 (2026-02-14)
- Initial release
- Voice cloning with library management
- Voice design from text descriptions
- Multi-voice narration (single, manual, annotated modes)
- CPU/GPU support with model size selection
- CustomTkinter modern GUI
- Comprehensive settings and configuration
