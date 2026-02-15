# Installation Guide

Complete installation instructions for Qwen-semble TTS Voice Studio.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Installation (Windows)](#quick-installation-windows)
- [Manual Installation](#manual-installation)
- [Verification](#verification)
- [First Launch](#first-launch)
- [Troubleshooting Installation](#troubleshooting-installation)
- [Updating](#updating)
- [Uninstalling](#uninstalling)

---

## Prerequisites

### Required

1. **Python 3.12 or higher**
   - Download from: https://www.python.org/downloads/
   - ✅ **Important**: Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **8GB+ RAM** (16GB+ recommended)

3. **10GB+ free disk space** (for models and outputs)

### For GPU Version (Optional but Recommended)

1. **NVIDIA GPU** with 8GB+ VRAM (16GB+ recommended for 1.7B model)

2. **CUDA 12.1 or higher**
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Verify: `nvidia-smi`

3. **Visual Studio Build Tools** (for Flash Attention on Windows)
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "Desktop development with C++" workload

---

## Quick Installation (Windows)

### Option A: GPU Version (Recommended for NVIDIA GPU Users)

1. **Clone or download** the repository:
   ```bash
   git clone https://github.com/yourusername/Qwen-semble.git
   cd Qwen-semble
   ```

2. **Run the GPU installer**:
   ```bash
   install-gpu.bat
   ```

This automated script will:
- ✅ Install PyTorch with CUDA 12.1 support
- ✅ Install all application dependencies
- ✅ Install Flash Attention (optional, may skip if compilation fails)

**Total time**: 5-15 minutes depending on internet speed

### Option B: CPU Version (No GPU Required)

1. **Clone or download** the repository:
   ```bash
   git clone https://github.com/yourusername/Qwen-semble.git
   cd Qwen-semble
   ```

2. **Run the CPU installer**:
   ```bash
   install-cpu.bat
   ```

This automated script will:
- ✅ Install PyTorch (CPU version)
- ✅ Install all application dependencies

**Total time**: 2-5 minutes

---

## Manual Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/Qwen-semble.git
cd Qwen-semble
```

### Step 2: Create Virtual Environment (Recommended)

**Using venv:**
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

**Using conda:**
```bash
conda create -n qwen-tts python=3.12 -y
conda activate qwen-tts
```

### Step 3: Install Dependencies

#### For GPU Users

**3a. Install PyTorch with CUDA support:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**3b. Install application requirements:**
```bash
pip install -r requirements-gpu.txt
```

**3c. (Optional) Install Flash Attention:**
```bash
pip install flash-attn --no-build-isolation
```

⚠️ **Note**: Flash Attention installation may take 10-20 minutes and requires MSVC compiler. If it fails, the application will still work but may be slightly slower.

#### For CPU Users

```bash
pip install -r requirements-cpu.txt
```

---

## Verification

### Verify Python Installation

```bash
python --version
# Should show: Python 3.12.x or higher
```

### Verify Dependencies

```bash
python -c "import customtkinter, qwen_tts, transformers; print('✅ All packages available')"
```

### Verify CUDA (GPU version only)

```bash
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Expected output:
```
CUDA Available: True
GPU: NVIDIA GeForce RTX 3090
```

If CUDA shows `False`, you may need to:
- Reinstall CUDA drivers
- Reinstall PyTorch with CUDA support
- Check GPU is not disabled in BIOS

---

## First Launch

### Running the Application

```bash
python src/main.py
```

Or double-click **`run.bat`** (Windows)

### What Happens on First Launch

1. **Application starts** - You'll see the splash screen

2. **Models download automatically** (~7GB for 1.7B model):
   - `Qwen3-TTS-12Hz-1.7B-CustomVoice`
   - `Qwen3-TTS-Tokenizer-12Hz`
   - Downloaded to: `~/.cache/huggingface/`
   - **This may take 10-30 minutes** depending on internet speed
   - Only happens once, models are cached

3. **TTS Engine initializes**:
   - Loads model into memory (GPU or CPU)
   - May take 1-2 minutes

4. **Main window opens**:
   - All tabs are now active and ready to use

### Optional First-Time Setup

1. **Go to Settings tab**

2. **Configure Device**:
   - Select GPU if available (faster)
   - Or select CPU (slower but compatible)

3. **Choose Model Size**:
   - `1.7B` for best quality (default)
   - `0.6B` for faster generation

4. **(Optional) Add HuggingFace Token**:
   - Required only if models fail to download
   - Get free token at: https://huggingface.co/settings/tokens
   - Paste in "HuggingFace Authentication" section
   - Click "Save Token"

---

## Troubleshooting Installation

### "Python not found" Error

**Problem**: Running install script shows "Python not found"

**Solution**:
1. Install Python 3.12+ from https://www.python.org/
2. **Re-run installer** and check "Add Python to PATH"
3. Restart Command Prompt/Terminal
4. Verify: `python --version`

### "pip not found" Error

**Solution**:
```bash
python -m ensurepip --upgrade
```

### PyTorch Installation Fails

**Problem**: Error installing torch with CUDA

**Solution 1** - Use CPU version:
```bash
pip install -r requirements-cpu.txt
```

**Solution 2** - Install PyTorch separately:
```bash
# Visit https://pytorch.org/get-started/locally/
# Select your OS, pip, Python, and CUDA version
# Copy and run the provided command
```

### Flash Attention Build Fails

**Problem**: `flash-attn` installation fails with compiler errors

**Solution**: **Skip it - it's optional!**
- Flash Attention provides ~20% speed improvement on GPU
- The application works perfectly without it
- Error is expected if you don't have MSVC compiler

### Models Won't Download

**Problem**: "Failed to download model" on first launch

**Solutions**:
1. **Check internet connection**
2. **Check firewall** - allow Python to access internet
3. **Check disk space** - need 10GB+ free
4. **Add HuggingFace token**:
   - Settings tab → HuggingFace Authentication
   - Get token at: https://huggingface.co/settings/tokens
   - Save token and restart app
5. **Manual download**:
   ```bash
   huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
   ```

### "CUDA out of memory" on Launch

**Problem**: GPU runs out of memory when loading model

**Solutions**:
1. **Close other GPU applications** (games, video editing, etc.)
2. **Switch to 0.6B model** (Settings → Model Size → 0.6B)
3. **Switch to CPU mode** (Settings → Device → CPU)
4. **Check GPU VRAM**: You need 8GB+ for 1.7B model

### Permission Denied Errors (Linux/macOS)

**Problem**: Cannot write to directories

**Solution**:
```bash
# Make sure you own the directory
sudo chown -R $USER:$USER ~/Qwen-semble

# Or install to user directory
python -m pip install --user -r requirements-cpu.txt
```

---

## Updating

To update Qwen-semble to a newer version:

```bash
cd Qwen-semble
git pull

# Reactivate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Update dependencies
# For GPU:
pip install -r requirements-gpu.txt --upgrade
# For CPU:
pip install -r requirements-cpu.txt --upgrade
```

---

## Uninstalling

### Remove Application

```bash
# Deactivate virtual environment first
deactivate  # or conda deactivate

# Delete the application directory
rm -rf Qwen-semble  # Linux/macOS
# or manually delete folder on Windows
```

### Remove Downloaded Models (Optional)

Models are cached in your home directory and can be reused by other apps:

**Windows:**
```
C:\Users\YourName\.cache\huggingface\hub\
```

**Linux/macOS:**
```
~/.cache/huggingface/hub/
```

To remove (frees ~7-14GB):
```bash
rm -rf ~/.cache/huggingface/hub/models--Qwen*
```

---

## Next Steps

✅ Installation complete! 

**Next:**
- Read [USAGE.md](USAGE.md) for detailed usage instructions
- Try voice cloning in the "Voice Clone" tab
- Experiment with voice design in the "Voice Design" tab
- Create your first narration in the "Narration" tab

**Need Help?**
- Check [USAGE.md](USAGE.md) for tutorials
- Review application logs: `output/logs/app.log`
- Open an issue on GitHub
