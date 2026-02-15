# Qwen-semble Installation Guide

## Quick Installation (Windows)

### Prerequisites

1. **Python 3.12+**: Download from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   
2. **For GPU Version**:
   - NVIDIA GPU with 8GB+ VRAM (16GB recommended)
   - CUDA 12.1+ drivers: https://developer.nvidia.com/cuda-downloads
   - Visual Studio Build Tools (for Flash Attention): https://visualstudio.microsoft.com/visual-cpp-build-tools/

### Automated Installation

#### GPU Version (Recommended for NVIDIA GPU users)

1. Open PowerShell or Command Prompt
2. Navigate to Qwen-semble folder:
   ```
   cd path\to\Qwen-semble
   ```
3. Run the GPU installer:
   ```
   install-gpu.bat
   ```
   
This will automatically:
- Install PyTorch with CUDA 12.1 support
- Install all dependencies
- Install Flash Attention (optional, may skip if it fails)

#### CPU Version (No GPU required)

1. Open PowerShell or Command Prompt
2. Navigate to Qwen-semble folder:
   ```
   cd path\to\Qwen-semble
   ```
3. Run the CPU installer:
   ```
   install-cpu.bat
   ```

### Manual Installation

#### For GPU Users

**Step 1**: Create Virtual Environment (optional but recommended)
```
python -m venv venv
venv\Scripts\activate
```

**Step 2**: Install PyTorch with CUDA support
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Step 3**: Install application requirements
```
pip install -r requirements-gpu.txt
```

**Step 4**: Verify CUDA is available
```
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
```
Should print: `CUDA Available: True`

**Step 5** (Optional): Install Flash Attention
```
pip install flash-attn --no-build-isolation
```
⚠️ This may take 10-20 minutes and requires MSVC compiler. Skip if it fails.

#### For CPU Users

**Step 1**: Create Virtual Environment (optional but recommended)
```
python -m venv venv
venv\Scripts\activate
```

**Step 2**: Install dependencies
```
pip install -r requirements-cpu.txt
```

## Running the Application

```
python src\main.py
```

Or simply double-click **`run.bat`** in the Qwen-semble folder.

## First Launch

1. **Model Download**: The application will download ~7GB of models from HuggingFace. This happens only once and may take 10-30 minutes depending on your internet speed.

2. **Device Selection**: Go to Settings tab:
   - **GPU users**: Select your CUDA device (e.g., "cuda:0")
   - **CPU users**: Select "cpu"
   
3. **Model Size**: Choose based on your hardware:
   - **1.7B model**: Better quality, requires 8GB+ VRAM or 16GB+ RAM
   - **0.6B model**: Faster, works with less resources

4. **HuggingFace Token** (optional): Some models may require authentication:
   - Get token at: https://huggingface.co/settings/tokens
   - Enter in Settings tab and click "Save Token"

## Troubleshooting Installation

### "Python not found"
- Reinstall Python and check "Add Python to PATH"
- Or use full path: `C:\Python312\python.exe` instead of `python`

### "pip not found"
- Run: `python -m ensurepip --upgrade`

### "torch installation failed" or "Could not find CUDA"
**For GPU version:**
- Verify CUDA drivers: `nvidia-smi` in command prompt
- Try CUDA 11.8 if 12.1 fails:
  ```
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```
- Or install CPU version instead: `pip install -r requirements-cpu.txt`

### "Microsoft Visual C++ 14.0 required"
- Install Microsoft C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Select "Desktop development with C++" workload
- Or try pre-built wheels: `pip install --only-binary :all: soundfile sounddevice`

### "flash-attn installation failed"
- This is optional. Skip it and the app will work fine without FlashAttention 2.

## Updating

To update to a newer version:

```
cd Qwen-semble
git pull
venv\Scripts\activate
# For GPU version:
pip install -r requirements-gpu.txt --upgrade
# For CPU version:
pip install -r requirements-cpu.txt --upgrade
```

## Uninstalling

1. Delete the Qwen-semble folder
2. Models are cached in `C:\Users\YourName\.cache\huggingface\` - delete if needed

That's it! You're ready to use Qwen-semble.
