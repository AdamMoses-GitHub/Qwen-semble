"""Voice design tab interface."""

from typing import TYPE_CHECKING, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from core.audio_utils import save_audio
from utils.error_handler import logger, show_error_dialog
from utils.threading_helpers import TTSWorker
from gui.components import AudioPlayerWidget

if TYPE_CHECKING:
    from utils.workspace_manager import WorkspaceManager


class VoiceDesignTab(ctk.CTkFrame):
    """Voice design tab."""
    
    EXAMPLE_PROMPTS = [
        "Young female voice, cheerful and energetic, slightly high pitch",
        "Middle-aged male voice, authoritative news anchor tone, deep and confident",
        "Elderly female voice, warm grandmother tone, gentle and comforting",
        "Teen male voice, slightly shy and nervous, tenor range with occasional voice breaks",
        "Professional businesswoman voice, clear articulation, confident mid-range",
    ]
    
    def __init__(self, parent, tts_engine, voice_library, config, narration_refresh_callback=None, saved_voices_refresh_callback=None, workspace_mgr: Optional['WorkspaceManager'] = None):
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.voice_library = voice_library
        self.config = config
        self.narration_refresh_callback = narration_refresh_callback
        self.saved_voices_refresh_callback = saved_voices_refresh_callback
        self.workspace_mgr = workspace_mgr
        
        self.current_description = ""
        self.sample_audio = None
        self.sample_sr = None
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
        panel.rowconfigure(2, weight=1)
        
        # Title
        title = ctk.CTkLabel(panel, text="🎨 Create Voice Model", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, pady=(10, 20), sticky="w", padx=10)
        
        # Description section
        desc_label = ctk.CTkLabel(panel, text="Voice Description:", font=("Arial", 12, "bold"))
        desc_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.description_text = ctk.CTkTextbox(panel, height=150)
        self.description_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Load from file button
        load_desc_btn = ctk.CTkButton(
            panel,
            text="📁 Load from Text File",
            command=self._load_description_from_file,
            width=150
        )
        load_desc_btn.grid(row=3, column=0, pady=5)
        
        # Example prompts
        example_label = ctk.CTkLabel(panel, text="Example Descriptions:", font=("Arial", 11, "bold"))
        example_label.grid(row=4, column=0, sticky="w", padx=10, pady=(15, 5))
        
        example_frame = ctk.CTkScrollableFrame(panel, height=120)
        example_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        
        for prompt in self.EXAMPLE_PROMPTS:
            btn = ctk.CTkButton(
                example_frame,
                text=prompt,
                command=lambda p=prompt: self._use_example(p),
                anchor="w",
                height=25,
                font=("Arial", 10)
            )
            btn.pack(fill="x", pady=2)
        
        # Language selection
        lang_frame = ctk.CTkFrame(panel)
        lang_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        
        lang_label = ctk.CTkLabel(lang_frame, text="Language:", font=("Arial", 11, "bold"))
        lang_label.pack(side="left", padx=5)
        
        languages = ["Auto"] + self.tts_engine.LANGUAGES[1:]
        last_lang = self.config.get("last_used_language", "Auto")
        self.language_combo = ctk.CTkComboBox(lang_frame, values=languages, width=120)
        self.language_combo.set(last_lang)
        self.language_combo.pack(side="left", padx=5)
        
        # Info text
        info_text = ctk.CTkLabel(
            panel,
            text="💡 Tip: Be specific about gender, age, tone, pitch, and speaking style\nfor best voice design results.",
            font=("Arial", 10),
            text_color="gray",
            justify="left"
        )
        info_text.grid(row=7, column=0, sticky="n", padx=10, pady=10)
        
        # Create Model button
        self.create_model_button = ctk.CTkButton(
            panel,
            text="🎨 Create Voice Model",
            command=self._create_voice_model,
            height=50,
            font=("Arial", 16, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.create_model_button.grid(row=8, column=0, sticky="ew", padx=10, pady=20)
        
        # Progress bar
        self.model_progress_bar = ctk.CTkProgressBar(panel)
        self.model_progress_bar.grid(row=9, column=0, sticky="ew", padx=10, pady=5)
        self.model_progress_bar.set(0)
        
        self.model_progress_label = ctk.CTkLabel(panel, text="", font=("Arial", 10))
        self.model_progress_label.grid(row=10, column=0, pady=(0, 10))
    
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
        self.test_text.insert("1.0", "Hello! This is a test of my designed voice.")
        
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
        
        self.tags_entry = ctk.CTkEntry(panel, placeholder_text="e.g., female, professional, clear")
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
    
    def _use_example(self, prompt: str) -> None:
        """Use example prompt."""
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", prompt)
    
    def _load_description_from_file(self) -> None:
        """Load description from text file."""
        filepath = filedialog.askopenfilename(
            title="Load Description",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.description_text.delete("1.0", "end")
                self.description_text.insert("1.0", text)
            except Exception as e:
                show_error_dialog(e, "loading description file", self)
    
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
        """Create voice model (designed voice) and generate template tests."""
        logger.info("Creating designed voice model...")
        
        # Validate inputs
        description = self.description_text.get("1.0", "end-1c").strip()
        if not description:
            messagebox.showerror("Missing Input", "Please provide a voice description.")
            return
        
        self.current_description = description
        language = self.language_combo.get()
        self.config.set("last_used_language", language)
        
        # Disable UI
        self.create_model_button.configure(state="disabled", text="Creating Model...")
        self.model_progress_bar.set(0)
        self.model_progress_label.configure(text="Initializing...")
        
        # Load voice design model if needed
        if self.tts_engine.voice_design_model is None:
            logger.info("Loading VoiceDesign model...")
            self.model_progress_label.configure(text="Loading VoiceDesign model...")
            try:
                model_size = self.config.get("model_size", "1.7B")
                self.tts_engine.load_voice_design_model(model_size)
            except Exception as e:
                logger.error(f"Failed to load VoiceDesign model: {e}")
                show_error_dialog(e, "loading VoiceDesign model", self)
                self._reset_model_ui()
                return
        
        def create_task():
            """Background task to create voice model."""
            logger.info("Generating sample audio with voice design...")
            
            # Get generation parameters from config
            gen_params = self.config.get("generation_params", {})
            logger.debug(f"Using generation params: {gen_params}")
            
            # Generate a sample with the description
            sample_text = "Hello, this is a voice sample created from the design description."
            wavs, sr = self.tts_engine.generate_voice_design(
                text=sample_text,
                language=language,
                instruct=description,
                **gen_params
            )
            sample_audio = wavs[0]
            
            logger.info("Generating template test transcripts...")
            
            # Get template test transcripts from config
            template_texts = self.config.get("template_test_transcripts", [
                "I am a voice model. I was created using the magic of computing.",
                "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
                "I am a voice model. Row, row, row your boat, gently down the stream. Merrily, merrily, merrily, life is but a dream."
            ])
            
            # Generate all template tests
            template_audios = {}
            for idx, text in enumerate(template_texts):
                logger.info(f"Generating template test {idx+1}/3...")
                wavs, sr = self.tts_engine.generate_voice_design(
                    text=text,
                    language=language,
                    instruct=description,
                    **gen_params
                )
                template_audios[idx] = (wavs[0], sr)
            
            return sample_audio, sr, template_audios
        
        def on_success(result):
            """Handle successful model creation."""
            logger.info("Voice model created successfully")
            self.sample_audio, self.sample_sr, self.template_test_audios = result
            
            # Update UI
            self.model_progress_bar.set(1.0)
            self.model_progress_label.configure(text="✅ Voice model created!")
            
            # Enable test and save sections
            self.generate_test_button.configure(state="normal")
            for btn in self.template_buttons:
                btn.configure(state="normal")
            self.save_voice_button.configure(state="normal")
            
            # Auto-play sample
            self.test_audio_player.load_audio(self.sample_audio, self.sample_sr)
            self.test_audio_player.play()
            
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
        self.create_model_button.configure(state="normal", text="🎨 Create Voice Model")
        self.model_progress_bar.set(0)
        self.model_progress_label.configure(text="")
        self.current_worker = None
    
    def _generate_test_speech(self) -> None:
        """Generate test speech with current voice model."""
        if not self.current_description:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        test_text = self.test_text.get("1.0", "end-1c").strip()
        if not test_text:
            messagebox.showerror("Missing Input", "Please enter test text.")
            return
        
        logger.info("Generating test speech...")
        self.generate_test_button.configure(state="disabled", text="Generating...")
        
        language = self.language_combo.get()
        
        def generate_task():
            """Background generation task."""
            gen_params = self.config.get("generation_params", {})
            wavs, sr = self.tts_engine.generate_voice_design(
                text=test_text,
                language=language,
                instruct=self.current_description,
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
        if self.sample_audio is None or not self.current_description:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        if self.sample_sr is None:
            messagebox.showerror("Error", "Invalid sample audio data.")
            return
        
        # Get name and tags
        name = self.voice_name_entry.get().strip()
        if not name:
            messagebox.showerror("Missing Input", "Please enter a voice name.")
            return
        
        tags_text = self.tags_entry.get().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
        
        try:
            # Save sample audio temporarily
            if self.workspace_mgr:
                temp_dir = self.workspace_mgr.get_temp_dir()
            else:
                temp_dir = Path("output/temp")
            temp_path = temp_dir / f"voice_design_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            save_audio(self.sample_audio, self.sample_sr, str(temp_path))
            
            # Save to library with template tests
            language = self.language_combo.get()
            
            voice_id = self.voice_library.save_designed_voice(
                name=name,
                description=self.current_description,
                sample_audio_path=temp_path,
                tags=tags,
                language=language,
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
