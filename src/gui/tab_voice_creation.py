"""Unified voice creation tab interface - supports both cloning and design."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import numpy as np

from core.audio_utils import save_audio, load_audio, get_audio_duration
from utils.error_handler import validate_audio_for_cloning, logger, show_error_dialog
from utils.threading_helpers import TTSWorker
from gui.components import AudioPlayerWidget, FilePickerWidget


class VoiceCreationTab(ctk.CTkFrame):
    """Unified voice creation tab supporting both clone and design modes."""
    
    def __init__(self, parent, tts_engine, voice_library, config, narration_refresh_callback=None, saved_voices_refresh_callback=None, workspace_dir=None):
        """Initialize voice creation tab.
        
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
        
        # Mode state
        self.current_mode = "clone"  # "clone" or "design"
        
        # Clone mode state
        self.ref_audio_path = None
        self.current_voice_prompt = None
        
        # Design mode state
        self.current_description = ""
        self.sample_audio = None
        self.sample_sr = None
        
        # Shared state
        self.template_test_audios = {}  # {index: (audio, sr)}
        self.custom_test_audios = []  # [{"text": str, "audio_path": str, "audio": np.array, "sr": int}]
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
        
        # Left panel: Mode selector + dynamic content
        self._create_mode_panel()
        
        # Right panel: Test & Save (split top/bottom) - shared across modes
        self._create_test_save_panel()
    
    def _create_mode_panel(self) -> None:
        """Create left panel with mode selector and dynamic content."""
        self.mode_panel = ctk.CTkFrame(self)
        self.mode_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.mode_panel.columnconfigure(0, weight=1)
        self.mode_panel.rowconfigure(1, weight=1)  # Dynamic content area expands
        
        # Mode selector at top
        selector_frame = ctk.CTkFrame(self.mode_panel)
        selector_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        selector_frame.columnconfigure(0, weight=1)
        
        selector_label = ctk.CTkLabel(selector_frame, text="Voice Creation Mode:", font=("Arial", 12, "bold"))
        selector_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2))
        
        self.mode_selector = ctk.CTkSegmentedButton(
            selector_frame,
            values=["Clone", "Design"],
            command=self._on_mode_changed,
            font=("Arial", 12, "bold"),
            height=35
        )
        self.mode_selector.set("Clone")
        self.mode_selector.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 5))
        
        # Info label about mode switching
        mode_info = ctk.CTkLabel(
            selector_frame,
            text="💡 Your test text and audio are preserved when switching modes",
            font=("Arial", 9),
            text_color="gray"
        )
        mode_info.grid(row=2, column=0, sticky="w", padx=5, pady=(2, 5))
        
        # Dynamic content container (rebuilt when mode changes)
        # Set minimum height to prevent layout jumping
        self.dynamic_content_frame = ctk.CTkFrame(self.mode_panel, height=600)
        self.dynamic_content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.dynamic_content_frame.columnconfigure(0, weight=1)
        self.dynamic_content_frame.rowconfigure(0, weight=1)
        self.dynamic_content_frame.grid_propagate(False)  # Maintain minimum height
        
        # Build initial mode UI (clone)
        self._build_current_mode_ui()
    
    def _on_mode_changed(self, value: str) -> None:
        """Handle mode selector change."""
        new_mode = value.lower()
        
        # Check if there's unsaved work
        if self._has_unsaved_work():
            mode_name = self.current_mode.capitalize()
            what_will_be_lost = "voice model" if self.current_mode == "clone" else "designed voice and description"
            
            result = messagebox.askyesno(
                "Switch Mode?",
                f"You have an unsaved {what_will_be_lost} in {mode_name} mode.\n\n"
                f"Switching to {value} mode will clear:\n"
                f"• Your current voice model\n"
                f"• Template test audio files\n\n"
                f"Your test text and audio will be preserved.\n\n"
                f"Do you want to continue?",
                icon='warning'
            )
            if not result:
                # Revert selector
                self.mode_selector.set(self.current_mode.capitalize())
                return
        
        # Switch mode
        logger.info(f"Switching voice creation mode: {self.current_mode} -> {new_mode}")
        self.current_mode = new_mode
        
        # Disable mode selector during transition
        self.mode_selector.configure(state="disabled")
        
        # Reset state for current mode
        self._reset_mode_state()
        
        # Force layout update before rebuilding
        self.update_idletasks()
        
        # Rebuild UI
        self._build_current_mode_ui()
        
        # Re-enable mode selector after transition
        self.after(100, lambda: self.mode_selector.configure(state="normal"))
    
    def _has_unsaved_work(self) -> bool:
        """Check if there's unsaved work in current mode."""
        if self.current_mode == "clone":
            return self.current_voice_prompt is not None
        else:  # design
            return self.sample_audio is not None and self.current_description != ""
    
    def _reset_mode_state(self) -> None:
        """Reset state when switching modes."""
        # Reset clone state
        self.ref_audio_path = None
        self.current_voice_prompt = None
        
        # Reset design state
        self.current_description = ""
        self.sample_audio = None
        self.sample_sr = None
        
        # Reset shared state (but preserve test_audio if user wants to keep testing)
        self.template_test_audios = {}
        self.custom_test_audios = []
        # Note: test_audio and test_sr are preserved so user doesn't lose their test audio
        
        # Reset UI state
        self.generate_test_button.configure(state="disabled")
        self.save_voice_button.configure(state="disabled")
        
        # Rebuild test audio list (will be empty after reset)
        self._rebuild_test_audio_list()
        
        # Stop any running workers
        if self.current_worker:
            self.current_worker = None
    
    def _build_current_mode_ui(self) -> None:
        """Build UI for current mode."""
        # Clear existing content with smooth transition
        for widget in self.dynamic_content_frame.winfo_children():
            widget.destroy()
        
        # Force update to clear destroyed widgets
        self.dynamic_content_frame.update_idletasks()
        
        # Build mode-specific UI
        if self.current_mode == "clone":
            self._build_clone_ui()
        else:  # design
            self._build_design_ui()
        
        # Force layout update after building
        self.dynamic_content_frame.update_idletasks()
    
    def _build_clone_ui(self) -> None:
        """Build UI for clone mode."""
        panel = ctk.CTkFrame(self.dynamic_content_frame)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panel.columnconfigure(0, weight=1)
        # Don't set row weight to prevent content jumping - let natural flow work
        
        # Title
        title = ctk.CTkLabel(panel, text="📝 Clone Voice from Audio", font=("Arial", 18, "bold"))
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
        info_frame.columnconfigure(0, weight=1)
        
        self.audio_info_label = ctk.CTkLabel(info_frame, text="No audio selected", text_color="gray")
        self.audio_info_label.grid(row=0, column=0, sticky="w", padx=5)
        
        self.play_ref_button = ctk.CTkButton(
            info_frame,
            text="▶ Play",
            command=self._play_reference,
            state="disabled",
            width=80
        )
        self.play_ref_button.grid(row=0, column=1, padx=5)
        
        # Reference transcript section
        transcript_frame = ctk.CTkFrame(panel)
        transcript_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        transcript_frame.columnconfigure(0, weight=1)
        
        transcript_label = ctk.CTkLabel(transcript_frame, text="Reference Transcript:", font=("Arial", 12, "bold"))
        transcript_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.ref_transcript_text = ctk.CTkTextbox(transcript_frame, height=120)
        self.ref_transcript_text.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        load_transcript_btn = ctk.CTkButton(
            transcript_frame,
            text="📁 Load from Text File",
            command=self._load_transcript_from_file,
            width=150
        )
        load_transcript_btn.grid(row=2, column=0, pady=5)
        
        # Info tip
        info_tip = ctk.CTkLabel(
            panel,
            text="💡 Tip: Use 10-30 seconds of clear speech with matching transcript\nfor best voice cloning results.",
            font=("Arial", 10),
            text_color="gray",
            justify="left"
        )
        info_tip.grid(row=3, column=0, sticky="nw", padx=10, pady=10)
        
        # Progress indicators
        self.model_progress_bar = ctk.CTkProgressBar(panel)
        self.model_progress_bar.grid(row=4, column=0, sticky="ew", padx=10, pady=(5, 2))
        self.model_progress_bar.set(0)
        
        self.model_progress_label = ctk.CTkLabel(panel, text="", font=("Arial", 10))
        self.model_progress_label.grid(row=5, column=0, padx=10, pady=(0, 5))
        
        # Create model button
        self.create_model_button = ctk.CTkButton(
            panel,
            text="🎤 Create Voice Model",
            command=self._create_voice_model,
            height=50,
            font=("Arial", 14, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.create_model_button.grid(row=6, column=0, sticky="ew", padx=10, pady=(10, 10))
    
    def _build_design_ui(self) -> None:
        """Build UI for design mode."""
        panel = ctk.CTkFrame(self.dynamic_content_frame)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panel.columnconfigure(0, weight=1)
        # Don't set row weight to prevent content jumping - let natural flow work
        
        # Title
        title = ctk.CTkLabel(panel, text="🎨 Design Voice from Description", font=("Arial", 18, "bold"))
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
        
        # Load example descriptions from config
        example_descriptions = self.config.get("example_voice_descriptions", [
            "Young Asian female voice, calm and professional, software engineer tone with clear articulation",
            "Elderly African American male voice, wise and warm, deep storyteller quality with gravitas",
            "Middle-aged British female voice, authoritative broadcaster tone, crisp BBC news presenter style"
        ])  # Fallback defaults (full list is in config)
        
        for prompt in example_descriptions:
            btn = ctk.CTkButton(
                example_frame,
                text=prompt,
                command=lambda p=prompt: self._use_example(p),
                anchor="w",
                height=30,
                width=600  # Set minimum width for readability
            )
            btn.pack(padx=5, pady=2)  # No fill="x" to allow horizontal scrolling
        
        # Language selection
        lang_frame = ctk.CTkFrame(panel)
        lang_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        lang_frame.columnconfigure(0, weight=1)
        
        lang_label = ctk.CTkLabel(lang_frame, text="Language:", font=("Arial", 11, "bold"))
        lang_label.grid(row=0, column=0, sticky="w", padx=5)
        
        languages = ["Auto", "English", "Chinese", "Japanese", "Korean", "French", "German", "Spanish"]
        self.language_combo = ctk.CTkComboBox(lang_frame, values=languages, width=120)
        self.language_combo.set(self.config.get("last_used_language", "Auto"))
        self.language_combo.grid(row=0, column=1, padx=5)
        
        # Info tip
        info_tip = ctk.CTkLabel(
            panel,
            text="💡 Tip: Be specific about gender, age, tone, pitch, and speaking style\nfor best voice design results.",
            font=("Arial", 10),
            text_color="gray",
            justify="left"
        )
        info_tip.grid(row=7, column=0, sticky="nw", padx=10, pady=10)
        
        # Progress indicators
        self.model_progress_bar = ctk.CTkProgressBar(panel)
        self.model_progress_bar.grid(row=8, column=0, sticky="ew", padx=10, pady=(5, 2))
        self.model_progress_bar.set(0)
        
        self.model_progress_label = ctk.CTkLabel(panel, text="", font=("Arial", 10))
        self.model_progress_label.grid(row=9, column=0, padx=10, pady=(0, 5))
        
        # Create model button
        self.create_model_button = ctk.CTkButton(
            panel,
            text="🎨 Create Voice Model",
            command=self._create_voice_model,
            height=50,
            font=("Arial", 14, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.create_model_button.grid(row=10, column=0, sticky="ew", padx=10, pady=(10, 10))
    
    def _create_test_save_panel(self) -> None:
        """Create test and save panel (right side, shared across modes)."""
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=3)  # Test panel larger
        right_panel.rowconfigure(1, weight=2)  # Save panel smaller
        
        # Test panel (top)
        self._create_test_panel(right_panel)
        
        # Save panel (bottom)
        self._create_save_panel(right_panel)
    
    def _create_test_panel(self, parent) -> None:
        """Create test voice model section (top of right panel)."""
        panel = ctk.CTkFrame(parent)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 2))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(7, weight=1)  # Test audio list expands
        
        # Title
        title = ctk.CTkLabel(panel, text="🎧 Test Voice Model", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(10, 5), sticky="w", padx=10)
        
        # Test text
        test_label = ctk.CTkLabel(panel, text="Test Text:", font=("Arial", 11, "bold"))
        test_label.grid(row=1, column=0, sticky="w", padx=10, pady=(5, 2))
        
        self.test_text = ctk.CTkTextbox(panel, height=100)
        self.test_text.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        self.test_text.insert("1.0", "Hello! This is a test of the voice model.")
        
        # Load test text button
        load_test_btn = ctk.CTkButton(
            panel,
            text="📁 Load from File",
            command=self._load_test_text_from_file,
            width=120
        )
        load_test_btn.grid(row=3, column=0, pady=5)
        
        # Add test button (renamed from Generate)
        self.generate_test_button = ctk.CTkButton(
            panel,
            text="Add Test Speech",
            command=self._generate_test_speech,
            height=40,
            font=("Arial", 13, "bold"),
            state="disabled"
        )
        self.generate_test_button.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        
        # Visual divider
        divider = ctk.CTkFrame(panel, height=2, fg_color="gray40")
        divider.grid(row=5, column=0, sticky="ew", padx=10, pady=(15, 10))
        
        # Test Audio section
        test_audio_label = ctk.CTkLabel(panel, text="Test Audio:", font=("Arial", 11, "bold"))
        test_audio_label.grid(row=6, column=0, sticky="w", padx=10, pady=(5, 5))
        
        # Scrollable frame for test audio list
        self.test_audio_scroll = ctk.CTkScrollableFrame(panel, height=200)
        self.test_audio_scroll.grid(row=7, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.test_audio_scroll.columnconfigure(0, weight=1)
    
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
    
    def _rebuild_test_audio_list(self) -> None:
        """Rebuild the test audio list with templates and custom tests."""
        # Clear existing rows
        for widget in self.test_audio_scroll.winfo_children():
            widget.destroy()
        
        # Get template texts from config
        template_texts = self.config.get("template_test_transcripts", [
            "I am a voice model. I was created using the magic of computing.",
            "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
            "I am a voice model. Row, row, row your boat, gently down the stream. Merrily, merrily, merrily, life is but a dream."
        ])
        
        row = 0
        
        # Add template tests first
        for idx in sorted(self.template_test_audios.keys()):
            template_text = template_texts[idx] if idx < len(template_texts) else f"Template Test {idx+1}"
            preview_text = template_text[:50] + "..." if len(template_text) > 50 else template_text
            
            test_frame = ctk.CTkFrame(self.test_audio_scroll)
            test_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
            test_frame.columnconfigure(0, weight=1)
            
            label = ctk.CTkLabel(
                test_frame,
                text=f"Template: {preview_text}",
                anchor="w"
            )
            label.pack(side="left", padx=5, fill="x", expand=True)
            
            play_btn = ctk.CTkButton(
                test_frame,
                text="▶ Play",
                command=lambda i=idx: self._play_test_audio(i, is_template=True),
                width=80
            )
            play_btn.pack(side="right", padx=5)
            
            row += 1
        
        # Add custom tests
        for idx, custom_test in enumerate(self.custom_test_audios):
            test_text = custom_test["text"]
            preview_text = test_text[:50] + "..." if len(test_text) > 50 else test_text
            
            test_frame = ctk.CTkFrame(self.test_audio_scroll)
            test_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
            test_frame.columnconfigure(0, weight=1)
            
            label = ctk.CTkLabel(
                test_frame,
                text=f"Custom: {preview_text}",
                anchor="w"
            )
            label.pack(side="left", padx=5, fill="x", expand=True)
            
            play_btn = ctk.CTkButton(
                test_frame,
                text="▶ Play",
                command=lambda i=idx: self._play_test_audio(i, is_template=False),
                width=80
            )
            play_btn.pack(side="right", padx=5)
            
            row += 1
    
    def _play_test_audio(self, index: int, is_template: bool) -> None:
        """Play a test audio from the list.
        
        Args:
            index: Index of the test
            is_template: True for template test, False for custom test
        """
        try:
            from core.audio_utils import AudioPlayer
            
            if is_template:
                if index in self.template_test_audios:
                    audio, sr = self.template_test_audios[index]
                    # Create temporary player for playback
                    player = AudioPlayer()
                    player.play(audio, sr)
                    logger.info(f"Playing template test {index+1}")
                else:
                    logger.warning(f"Template test {index+1} not available")
            else:
                if index < len(self.custom_test_audios):
                    custom_test = self.custom_test_audios[index]
                    audio = custom_test["audio"]
                    sr = custom_test["sr"]
                    # Create temporary player for playback
                    player = AudioPlayer()
                    player.play(audio, sr)
                    logger.info(f"Playing custom test: {custom_test['text'][:50]}...")
                else:
                    logger.warning(f"Custom test {index+1} not available")
        except Exception as e:
            logger.error(f"Failed to play test audio: {e}")
    
    # ========== Clone Mode Methods ==========
    
    def _on_audio_selected(self, filepath: str) -> None:
        """Handle audio file selection (clone mode)."""
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
        """Play reference audio (clone mode)."""
        if self.ref_audio_path:
            try:
                from core.audio_utils import AudioPlayer
                audio, sr = load_audio(self.ref_audio_path)
                player = AudioPlayer()
                player.play(audio, sr)
            except Exception as e:
                show_error_dialog(e, "playing reference audio", self)
    
    def _load_transcript_from_file(self) -> None:
        """Load transcript from text file (clone mode)."""
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
    
    # ========== Design Mode Methods ==========
    
    def _use_example(self, prompt: str) -> None:
        """Use example prompt (design mode)."""
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", prompt)
    
    def _load_description_from_file(self) -> None:
        """Load description from text file (design mode)."""
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
    
    # ========== Shared Methods ==========
    
    def _load_test_text_from_file(self) -> None:
        """Load test text from file (shared)."""
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
        """Create voice model (branches based on current mode)."""
        if self.current_mode == "clone":
            self._create_clone_model()
        else:  # design
            self._create_design_model()
    
    def _create_clone_model(self) -> None:
        """Create voice model via cloning."""
        logger.info("Creating cloned voice model...")
        
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
                ref_text=ref_text
            )
            
            logger.info("Generating template test transcripts...")
            
            # Get template test transcripts from config
            template_texts = self.config.get("template_test_transcripts", [
                "I am a voice model. I was created using the magic of computing.",
                "I am a voice model. A. B. C. D. E. 1. 2. 3. 4. 5",
                "Row, row, row your boat, gently down the stream."
            ])
            
            # Generate template tests
            template_audios = {}
            gen_params = self.config.get("generation_params", {})
            logger.debug(f"Using generation params: {gen_params}")
            
            for idx, text in enumerate(template_texts):
                logger.info(f"Generating template test {idx+1}/{len(template_texts)}...")
                wavs, sr = self.tts_engine.generate_voice_clone(
                    text=text,
                    language="Auto",
                    voice_clone_prompt=voice_prompt,
                    **gen_params
                )
                template_audios[idx] = (wavs[0], sr)
            
            return voice_prompt, template_audios
        
        def on_success(result):
            """Handle success."""
            self.current_voice_prompt, self.template_test_audios = result
            
            # Enable test and save buttons
            self.generate_test_button.configure(state="normal")
            self.save_voice_button.configure(state="normal")
            
            # Rebuild test audio list to show templates
            self._rebuild_test_audio_list()
            
            # Reset UI
            self._reset_model_ui()
            
            logger.info("Voice model created successfully")
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
    
    def _create_design_model(self) -> None:
        """Create voice model via design."""
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
                "Row, row, row your boat, gently down the stream."
            ])
            
            # Generate template tests
            template_audios = {}
            for idx, text in enumerate(template_texts):
                logger.info(f"Generating template test {idx+1}/{len(template_texts)}...")
                wavs, sr = self.tts_engine.generate_voice_design(
                    text=text,
                    language=language,
                    instruct=description,
                    **gen_params
                )
                template_audios[idx] = (wavs[0], sr)
            
            return sample_audio, sr, template_audios
        
        def on_success(result):
            """Handle success."""
            self.sample_audio, self.sample_sr, self.template_test_audios = result
            
            # Enable test and save buttons
            self.generate_test_button.configure(state="normal")
            self.save_voice_button.configure(state="normal")
            
            # Rebuild test audio list to show templates
            self._rebuild_test_audio_list()
            
            # Reset UI
            self._reset_model_ui()
            
            logger.info("Voice model created successfully")
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
        if self.current_mode == "clone":
            self.create_model_button.configure(state="normal", text="🎤 Create Voice Model")
        else:  # design
            self.create_model_button.configure(state="normal", text="🎨 Create Voice Model")
        self.model_progress_bar.set(0)
        self.model_progress_label.configure(text="")
        self.current_worker = None
    
    def _generate_test_speech(self) -> None:
        """Generate test speech with current voice model (branches by mode)."""
        test_text = self.test_text.get("1.0", "end-1c").strip()
        if not test_text:
            messagebox.showerror("Missing Input", "Please enter test text.")
            return
        
        if self.current_mode == "clone":
            self._generate_clone_test(test_text)
        else:  # design
            self._generate_design_test(test_text)
    
    def _generate_clone_test(self, test_text: str) -> None:
        """Generate test speech for cloned voice."""
        if not self.current_voice_prompt:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        logger.info("Generating test speech with cloned voice...")
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
            self.generate_test_button.configure(state="normal", text="Add Test Speech")
            # Save custom test if text is unique
            self._save_custom_test(test_text, self.test_audio, self.test_sr)
            logger.info("Test speech generated successfully")
        
        def on_error(error):
            """Handle error."""
            show_error_dialog(error, "generating test speech", self)
            self.generate_test_button.configure(state="normal", text="Add Test Speech")
        
        worker = TTSWorker(
            generate_task,
            success_callback=lambda r: self.after(0, lambda: on_success(r)),
            error_callback=lambda e: self.after(0, lambda: on_error(e))
        )
        worker.start()
    
    def _generate_design_test(self, test_text: str) -> None:
        """Generate test speech for designed voice."""
        if not self.current_description:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        logger.info("Generating test speech with designed voice...")
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
            self.generate_test_button.configure(state="normal", text="Add Test Speech")
            # Save custom test if text is unique
            self._save_custom_test(test_text, self.test_audio, self.test_sr)
            logger.info("Test speech generated successfully")
        
        def on_error(error):
            """Handle error."""
            show_error_dialog(error, "generating test speech", self)
            self.generate_test_button.configure(state="normal", text="Add Test Speech")
        
        worker = TTSWorker(
            generate_task,
            success_callback=lambda r: self.after(0, lambda: on_success(r)),
            error_callback=lambda e: self.after(0, lambda: on_error(e))
        )
        worker.start()
    
    def _save_custom_test(self, test_text: str, audio: np.ndarray, sample_rate: int) -> None:
        """Save custom test audio if text is unique.
        
        Args:
            test_text: The test text used
            audio: Generated audio data
            sample_rate: Audio sample rate
        """
        # Check if this text already exists
        for existing in self.custom_test_audios:
            if existing["text"] == test_text:
                logger.debug(f"Custom test text already exists, skipping save: {test_text[:50]}...")
                return
        
        try:
            # Save audio to temp file
            if self.workspace_dir:
                temp_dir = self.workspace_dir / "temp"
            else:
                temp_dir = Path("output/temp")
            
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            audio_path = temp_dir / f"custom_test_{timestamp}.wav"
            
            save_audio(audio, sample_rate, str(audio_path))
            
            # Add to custom tests list
            self.custom_test_audios.append({
                "text": test_text,
                "audio_path": str(audio_path),
                "audio": audio,
                "sr": sample_rate
            })
            
            logger.info(f"Saved custom test audio ({len(self.custom_test_audios)} total): {test_text[:50]}...")
            
            # Rebuild the test audio list to show the new custom test
            self._rebuild_test_audio_list()
            
        except Exception as e:
            logger.error(f"Failed to save custom test audio: {e}")
    
    def _save_voice_model(self) -> None:
        """Save voice model to library (branches by mode)."""
        # Get name and tags
        name = self.voice_name_entry.get().strip()
        if not name:
            messagebox.showerror("Missing Input", "Please enter a voice name.")
            return
        
        tags_text = self.tags_entry.get().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
        
        if self.current_mode == "clone":
            self._save_clone_model(name, tags)
        else:  # design
            self._save_design_model(name, tags)
    
    def _save_clone_model(self, name: str, tags: list) -> None:
        """Save cloned voice model."""
        if not self.current_voice_prompt:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        try:
            # Save to library with template tests and custom tests
            ref_text = self.ref_transcript_text.get("1.0", "end-1c").strip()
            
            voice_id = self.voice_library.save_cloned_voice(
                name=name,
                ref_audio_path=self.ref_audio_path,
                ref_text=ref_text,
                voice_clone_prompt=self.current_voice_prompt,
                tags=tags,
                language="Auto",
                template_test_audios=self.template_test_audios,
                custom_test_audios=self.custom_test_audios
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
    
    def _save_design_model(self, name: str, tags: list) -> None:
        """Save designed voice model."""
        if self.sample_audio is None or not self.current_description:
            messagebox.showerror("Error", "Please create a voice model first.")
            return
        
        if self.sample_sr is None:
            messagebox.showerror("Error", "Invalid sample audio data.")
            return
        
        try:
            # Save sample audio temporarily
            if self.workspace_dir:
                temp_path = self.workspace_dir / "temp" / f"voice_design_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = str(temp_path)
            else:
                temp_path = f"output/temp/voice_design_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            
            save_audio(self.sample_audio, self.sample_sr, temp_path)
            
            # Save to library with template tests and custom tests
            language = self.language_combo.get()
            
            voice_id = self.voice_library.save_designed_voice(
                name=name,
                description=self.current_description,
                sample_audio_path=temp_path,
                tags=tags,
                language=language,
                template_test_audios=self.template_test_audios,
                custom_test_audios=self.custom_test_audios
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
