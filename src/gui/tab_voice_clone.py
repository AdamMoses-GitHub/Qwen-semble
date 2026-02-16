"""Voice cloning tab interface."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import numpy as np
import time

from core.audio_utils import save_audio, load_audio, get_audio_duration
from utils.error_handler import validate_audio_for_cloning, logger, show_error_dialog
from utils.threading_helpers import TTSWorker
from gui.components import AudioPlayerWidget, FilePickerWidget


class VoiceCloneTab(ctk.CTkFrame):
    """Voice cloning tab."""
    
    def __init__(self, parent, tts_engine, voice_library, config, narration_refresh_callback=None, saved_voices_refresh_callback=None, workspace_dir=None):
        """Initialize voice clone tab.
        
        Args:
            parent: Parent widget
            tts_engine: TTS engine instance
            voice_library: Voice library instance
            config: Configuration instance
            narration_refresh_callback: Callback to refresh narration tab voice list
            saved_voices_refresh_callback: Callback to refresh saved voices tab
            workspace_dir: Root workspace directory (None for legacy mode)
        """
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.voice_library = voice_library
        self.config = config
        self.narration_refresh_callback = narration_refresh_callback
        self.saved_voices_refresh_callback = saved_voices_refresh_callback
        self.workspace_dir = workspace_dir
        
        self.ref_audio_path = None
        self.current_voice_prompt = None
        self.template_test_audios = {}  # {index: (audio, sr)}
        self.test_audio = None
        self.test_sr = None
        self.current_worker = None
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        # Two column layout
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Left panel: Create Voice Model
        self._create_model_panel()
        
        # Right panel: Test & Save (split top/bottom)
        self._create_test_save_panel()
    
    def _create_model_panel(self) -> None:
        """Create voice model creation panel (left)."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)
        
        # Title
        title = ctk.CTkLabel(panel, text="📝 Create Voice Model", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, pady=(10, 20), sticky="w", padx=10)
        
        # Reference audio section
        audio_frame = ctk.CTkFrame(panel)
        audio_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        audio_frame.columnconfigure(0, weight=1)
        
        audio_label = ctk.CTkLabel(audio_frame, text="Reference Audio:", font=("Arial", 12, "bold"))
        audio_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # File picker
        audio_types = [
            ("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
            ("All files", "*.*")
        ]
        self.audio_picker = FilePickerWidget(
            audio_frame,
            label="Audio File:",
            filetypes=audio_types,
            callback=self._on_audio_selected
        )
        self.audio_picker.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Audio info and play button
        info_frame = ctk.CTkFrame(audio_frame)
        info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        self.audio_info_label = ctk.CTkLabel(info_frame, text="No audio selected", text_color="gray")
        self.audio_info_label.pack(side="left", padx=5)
        
        self.play_ref_button = ctk.CTkButton(
            info_frame,
            text="▶ Play",
            command=self._play_reference,
            state="disabled",
            width=80
        )
        self.play_ref_button.pack(side="right", padx=5)
        
        # Reference transcript section
        transcript_frame = ctk.CTkFrame(panel)
        transcript_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        transcript_frame.columnconfigure(0, weight=1)
        
        transcript_label = ctk.CTkLabel(transcript_frame, text="Reference Transcript:", font=("Arial", 12, "bold"))
        transcript_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.ref_transcript_text = ctk.CTkTextbox(transcript_frame, height=120)
        self.ref_transcript_text.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Load from file button
        load_transcript_btn = ctk.CTkButton(
            transcript_frame,
            text="📁 Load from Text File",
            command=self._load_transcript_from_file,
            width=150
        )
        load_transcript_btn.grid(row=2, column=0, pady=5)
        
        # Info text
        info_text = ctk.CTkLabel(
            panel,
            text="💡 Tip: Use 10-30 seconds of clear speech with matching transcript\nfor best voice cloning results.",
            font=("Arial", 10),
            text_color="gray",
            justify="left"
        )
        info_text.grid(row=3, column=0, sticky="n", padx=10, pady=10)
        
        # Create Model button
        self.create_model_button = ctk.CTkButton(
            panel,
            text="🎤 Create Voice Model",
            command=self._create_voice_model,
            height=50,
            font=("Arial", 16, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.create_model_button.grid(row=4, column=0, sticky="ew", padx=10, pady=20)
        
        # Progress bar
        self.model_progress_bar = ctk.CTkProgressBar(panel)
        self.model_progress_bar.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        self.model_progress_bar.set(0)
        
        self.model_progress_label = ctk.CTkLabel(panel, text="", font=("Arial", 10))
        self.model_progress_label.grid(row=6, column=0, pady=(0, 10))
    
    def _create_test_save_panel(self) -> None:
        """Create test and save panel (right, split top/bottom)."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        
        # Top: Test Voice Model
        self._create_test_panel(panel)
        
        # Bottom: Save Voice Model
        self._create_save_panel(panel)
    
    def _create_test_panel(self, parent) -> None:
        """Create test voice model section (top of right panel)."""
        panel = ctk.CTkFrame(parent)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 2))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        
        # Title
        title = ctk.CTkLabel(panel, text="🎧 Test Voice Model", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(10, 10), sticky="w", padx=10)
        
        # Test text area
        test_label = ctk.CTkLabel(panel, text="Test Text:", font=("Arial", 11, "bold"))
        test_label.grid(row=1, column=0, sticky="w", padx=10, pady=(5, 2))
        
        self.test_text = ctk.CTkTextbox(panel, height=100)
        self.test_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.test_text.insert("1.0", "Hello! This is a test of my cloned voice.")
        
        # Load test text button
        load_test_btn = ctk.CTkButton(
            panel,
            text="📁 Load from File",
            command=self._load_test_text_from_file,
            width=120
        )
        load_test_btn.grid(row=3, column=0, pady=5)
        
        # Generate test button
        self.generate_test_button = ctk.CTkButton(
            panel,
            text="🎙️ Generate Test Speech",
            command=self._generate_test_speech,
            height=40,
            font=("Arial", 13, "bold"),
            state="disabled"
        )
        self.generate_test_button.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        
        # Audio player
        self.test_audio_player = AudioPlayerWidget(panel)
        self.test_audio_player.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        
        # Template test buttons
        template_label = ctk.CTkLabel(panel, text="Template Tests:", font=("Arial", 11, "bold"))
        template_label.grid(row=6, column=0, sticky="w", padx=10, pady=(10, 5))
        
        template_frame = ctk.CTkFrame(panel)
        template_frame.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 10))
        template_frame.columnconfigure(0, weight=1)
        
        self.template_buttons = []
        for i in range(3):
            btn = ctk.CTkButton(
                template_frame,
                text=f"▶ Template Test {i+1}",
                command=lambda idx=i: self._play_template_test(idx),
                state="disabled",
                height=30
            )
            btn.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            self.template_buttons.append(btn)
    
    def _create_save_panel(self, parent) -> None:
        """Create save voice model section (bottom of right panel)."""
        panel = ctk.CTkFrame(parent)
        panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))
        panel.columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(panel, text="💾 Save Voice Model", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(10, 10), sticky="w", padx=10)
        
        # Voice name
        name_label = ctk.CTkLabel(panel, text="Voice Name:", font=("Arial", 11, "bold"))
        name_label.grid(row=1, column=0, sticky="w", padx=10, pady=(5, 2))
        
        self.voice_name_entry = ctk.CTkEntry(panel, placeholder_text="Enter voice name...")
        self.voice_name_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Tags
        tags_label = ctk.CTkLabel(panel, text="Tags (comma-separated):", font=("Arial", 11, "bold"))
        tags_label.grid(row=3, column=0, sticky="w", padx=10, pady=(10, 2))
        
        self.tags_entry = ctk.CTkEntry(panel, placeholder_text="e.g., male, clear, english")
        self.tags_entry.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        
        # Save button
        self.save_voice_button = ctk.CTkButton(
            panel,
            text="💾 Save Voice Model",
            command=self._save_voice_model,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="blue",
            hover_color="darkblue",
            state="disabled"
        )
        self.save_voice_button.grid(row=5, column=0, sticky="ew", padx=10, pady=(15, 10))
    
    def _on_audio_selected(self, filepath: str) -> None:
        """Handle audio file selection."""
        # Validate audio
        is_valid, error_msg = validate_audio_for_cloning(filepath)
        
        if not is_valid:
            messagebox.showerror("Invalid Audio", error_msg)
            self.audio_picker.clear()
            return
        
        self.ref_audio_path = filepath
        
        # Show audio info
        try:
            duration = get_audio_duration(filepath)
            self.audio_info_label.configure(text=f"Duration: {duration:.1f}s")
            self.play_ref_button.configure(state="normal")
        except Exception as e:
            logger.error(f"Error getting audio info: {e}")
    
    def _play_reference(self) -> None:
        """Play reference audio."""
        if self.ref_audio_path:
            try:
                audio, sr = load_audio(self.ref_audio_path)
                self.test_audio_player.load_audio(audio, sr)
                self.test_audio_player.play()
            except Exception as e:
                show_error_dialog(e, "playing reference audio", self)
    
    def _load_transcript_from_file(self) -> None:
        """Load transcript from text file."""
        filepath = filedialog.askopenfilename(
            title="Load Transcript",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.ref_transcript_text.delete("1.0", "end")
                self.ref_transcript_text.insert("1.0", text)
            except Exception as e:
                show_error_dialog(e, "loading transcript file", self)
    
    def _load_test_text_from_file(self) -> None:
        """Load test text from file."""
        filepath = filedialog.askopenfilename(
            title="Load Test Text",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.test_text.delete("1.0", "end")
                self.test_text.insert("1.0", text)
            except Exception as e:
                show_error_dialog(e, "loading test text file", self)
    
    def _create_voice_model(self) -> None:
        """Create voice model (voice clone prompt) and generate template tests."""
        logger.info("Creating voice model...")
        
        # Validate inputs
        if not self.ref_audio_path:
            messagebox.showerror("Missing Input", "Please select a reference audio file.")
            return
        
        ref_text = self.ref_transcript_text.get("1.0", "end-1c").strip()
        if not ref_text:
            messagebox.showerror("Missing Input", "Please provide reference transcript.")
            return
        
        # Disable UI
        self.create_model_button.configure(state="disabled", text="Creating Model...")
        self.model_progress_bar.set(0)
        self.model_progress_label.configure(text="Initializing...")
        
        # Load base model if needed
        if self.tts_engine.base_model is None:
            logger.info("Loading Base model...")
            self.model_progress_label.configure(text="Loading Base model...")
            try:
                model_size = self.config.get("model_size", "1.7B")
                self.tts_engine.load_base_model(model_size)
            except Exception as e:
                logger.error(f"Failed to load Base model: {e}")
                show_error_dialog(e, "loading Base model", self)
                self._reset_model_ui()
                return
        
        def create_task():
            """Background task to create voice model."""
            logger.info("Creating voice clone prompt...")
            
            # Create voice clone prompt
            voice_prompt = self.tts_engine.create_voice_clone_prompt(
                ref_audio=self.ref_audio_path,
                ref_text=ref_text,
                x_vector_only_mode=False
            )
            
            logger.info("Generating template test transcripts...")
            
            # Get template test transcripts from config
            template_texts = self.config.get("template_test_transcripts", [
                "I am a voice model. I was created using the magic of computing.",
                "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
                "I am a voice model. Row, row, row your boat, gently down the stream. Merrily, merrily, merrily, life is but a dream."
            ])
            
            # Generate all template tests
            template_audios = {}
            gen_params = self.config.get("generation_params", {})
            logger.debug(f"Using generation params: {gen_params}")
            
            for idx, text in enumerate(template_texts):
                logger.info(f"Generating template test {idx+1}/3...")
                wavs, sr = self.tts_engine.generate_voice_clone(
                    text=text,
                    language="Auto",
                    voice_clone_prompt=voice_prompt,
                    **gen_params
                )
                template_audios[idx] = (wavs[0], sr)
            
            return voice_prompt, template_audios
        
        def on_success(result):
            """Handle successful model creation."""
            logger.info("Voice model created successfully")
            self.current_voice_prompt, self.template_test_audios = result
            
            # Update UI
            self.model_progress_bar.set(1.0)
            self.model_progress_label.configure(text="✅ Voice model created!")
            
            # Enable test and save sections
            self.generate_test_button.configure(state="normal")
            for btn in self.template_buttons:
                btn.configure(state="normal")
            self.save_voice_button.configure(state="normal")
            
            self._reset_model_ui()
            messagebox.showinfo("Success", "Voice model created successfully!\n\nYou can now test it or save it to your library.")
        
        def on_error(error):
            """Handle error."""
            logger.error(f"Failed to create voice model: {error}")
            show_error_dialog(error, "creating voice model", self)
            self._reset_model_ui()
        
        # Run in background
        self.model_progress_bar.set(0.3)
        self.model_progress_label.configure(text="Creating voice model...")
        
        worker = TTSWorker(
            create_task,
            success_callback=lambda r: self.after(0, lambda: on_success(r)),
            error_callback=lambda e: self.after(0, lambda: on_error(e))
        )
        self.current_worker = worker
        worker.start()
    
    def _reset_model_ui(self) -> None:
        """Reset model creation UI."""
        self.create_model_button.configure(state="normal", text="🎤 Create Voice Model")
        self.model_progress_bar.set(0)
        self.model_progress_label.configure(text="")
        self.current_worker = None
    
    def _generate_test_speech(self) -> None:
        """Generate test speech with current voice model."""
        if not self.current_voice_prompt:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        test_text = self.test_text.get("1.0", "end-1c").strip()
        if not test_text:
            messagebox.showerror("Missing Input", "Please enter test text.")
            return
        
        logger.info("Generating test speech...")
        self.generate_test_button.configure(state="disabled", text="Generating...")
        
        def generate_task():
            """Background generation task."""
            gen_params = self.config.get("generation_params", {})
            wavs, sr = self.tts_engine.generate_voice_clone(
                text=test_text,
                language="Auto",
                voice_clone_prompt=self.current_voice_prompt,
                **gen_params
            )
            return wavs[0], sr
        
        def on_success(result):
            """Handle success."""
            self.test_audio, self.test_sr = result
            self.test_audio_player.load_audio(self.test_audio, self.test_sr)
            self.test_audio_player.play()
            self.generate_test_button.configure(state="normal", text="🎙️ Generate Test Speech")
            logger.info("Test speech generated successfully")
        
        def on_error(error):
            """Handle error."""
            show_error_dialog(error, "generating test speech", self)
            self.generate_test_button.configure(state="normal", text="🎙️ Generate Test Speech")
        
        worker = TTSWorker(
            generate_task,
            success_callback=lambda r: self.after(0, lambda: on_success(r)),
            error_callback=lambda e: self.after(0, lambda: on_error(e))
        )
        worker.start()
    
    def _play_template_test(self, index: int) -> None:
        """Play a template test audio."""
        if index in self.template_test_audios:
            audio, sr = self.template_test_audios[index]
            self.test_audio_player.load_audio(audio, sr)
            self.test_audio_player.play()
            logger.info(f"Playing template test {index+1}")
        else:
            logger.warning(f"Template test {index+1} not available")
    
    def _save_voice_model(self) -> None:
        """Save voice model to library."""
        if not self.current_voice_prompt:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        # Get name and tags
        name = self.voice_name_entry.get().strip()
        if not name:
            messagebox.showerror("Missing Input", "Please enter a voice name.")
            return
        
        tags_text = self.tags_entry.get().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
        
        try:
            # Save to library with template tests
            ref_text = self.ref_transcript_text.get("1.0", "end-1c").strip()
            
            voice_id = self.voice_library.save_cloned_voice(
                name=name,
                ref_audio_path=self.ref_audio_path,
                ref_text=ref_text,
                voice_clone_prompt=self.current_voice_prompt,
                tags=tags,
                language="Auto",
                template_test_audios=self.template_test_audios
            )
            
            messagebox.showinfo("Success", f"Voice '{name}' saved to library!")
            
            # Clear form
            self.voice_name_entry.delete(0, "end")
            self.tags_entry.delete(0, "end")
            
            # Refresh other tabs
            if self.narration_refresh_callback:
                self.narration_refresh_callback()
            if self.saved_voices_refresh_callback:
                self.saved_voices_refresh_callback()
            
            logger.info(f"Voice model saved: {name} ({voice_id})")
            
        except Exception as e:
            show_error_dialog(e, "saving voice model", self)
