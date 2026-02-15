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
from gui.components import AudioPlayerWidget, FilePickerWidget, LoadingOverlay, VoiceLibraryItem


class VoiceCloneTab(ctk.CTkFrame):
    """Voice cloning tab."""
    
    def __init__(self, parent, tts_engine, voice_library, config, narration_refresh_callback=None):
        """Initialize voice clone tab.
        
        Args:
            parent: Parent widget
            tts_engine: TTS engine instance
            voice_library: Voice library instance
            config: Configuration instance
            narration_refresh_callback: Callback to refresh narration tab voice list
        """
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.voice_library = voice_library
        self.config = config
        self.narration_refresh_callback = narration_refresh_callback
        
        self.ref_audio_path = None
        self.generated_audio = None
        self.generated_sr = None
        self.current_voice_prompt = None
        self.current_worker = None
        self._generation_start_time = 0
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        # Main container with 3 columns
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Left panel: Reference audio
        self._create_reference_panel()
        
        # Middle panel: Generation
        self._create_generation_panel()
        
        # Right panel: Output and library
        self._create_output_panel()
    
    def _create_reference_panel(self) -> None:
        """Create reference audio panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Reference Audio", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # File picker
        audio_types = [
            ("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
            ("All files", "*.*")
        ]
        self.audio_picker = FilePickerWidget(
            panel,
            label="Audio File:",
            filetypes=audio_types,
            callback=self._on_audio_selected
        )
        self.audio_picker.pack(fill="x", padx=10, pady=5)
        
        # Audio info
        self.audio_info_label = ctk.CTkLabel(panel, text="", text_color="gray")
        self.audio_info_label.pack(pady=5)
        
        # Play reference button
        self.play_ref_button = ctk.CTkButton(
            panel,
            text="▶ Play Reference",
            command=self._play_reference,
            state="disabled"
        )
        self.play_ref_button.pack(pady=5)
        
        # Reference transcript
        ref_label = ctk.CTkLabel(panel, text="Reference Transcript:")
        ref_label.pack(pady=(20, 5))
        
        self.ref_transcript_text = ctk.CTkTextbox(panel, height=150)
        self.ref_transcript_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # X-Vector mode checkbox
        self.x_vector_var = ctk.BooleanVar(value=False)
        self.x_vector_check = ctk.CTkCheckBox(
            panel,
            text="X-Vector Only Mode (no transcript needed, lower quality)",
            variable=self.x_vector_var
        )
        self.x_vector_check.pack(pady=10)
    
    def _create_generation_panel(self) -> None:
        """Create generation panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Generate Speech", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Text to generate
        text_label = ctk.CTkLabel(panel, text="Text to Generate:")
        text_label.pack(pady=(10, 5))
        
        self.gen_text = ctk.CTkTextbox(panel, height=200)
        self.gen_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Character counter
        self.char_count_label = ctk.CTkLabel(panel, text="0 characters", text_color="gray")
        self.char_count_label.pack()
        self.gen_text.bind("<KeyRelease>", self._update_char_count)
        
        # Language selection
        lang_frame = ctk.CTkFrame(panel)
        lang_frame.pack(fill="x", padx=10, pady=10)
        
        lang_label = ctk.CTkLabel(lang_frame, text="Language:")
        lang_label.pack(side="left", padx=5)
        
        languages = ["Auto"] + self.tts_engine.LANGUAGES[1:]  # Skip duplicate "Auto"
        last_lang = self.config.get("last_used_language", "Auto")
        self.language_combo = ctk.CTkComboBox(lang_frame, values=languages, width=150)
        self.language_combo.set(last_lang)
        self.language_combo.pack(side="left", padx=5)
        
        # Generate button
        self.generate_button = ctk.CTkButton(
            panel,
            text="Generate Speech",
            command=self._generate_speech,
            height=40,
            font=("Arial", 14, "bold"),
            fg_color="green"
        )
        self.generate_button.pack(pady=20)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(panel)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        self.progress_var = ctk.StringVar(value="")
        self.progress_label = ctk.CTkLabel(panel, textvariable=self.progress_var)
        self.progress_label.pack()
    
    def _create_output_panel(self) -> None:
        """Create output and library panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Output & Library", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Audio player
        self.audio_player = AudioPlayerWidget(panel)
        self.audio_player.pack(fill="x", padx=10, pady=5)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(panel)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.save_audio_button = ctk.CTkButton(
            btn_frame,
            text="Save Audio",
            command=self._save_audio,
            state="disabled"
        )
        self.save_audio_button.pack(fill="x", pady=2)
        
        self.save_voice_button = ctk.CTkButton(
            btn_frame,
            text="Save to Voice Library",
            command=self._save_to_library,
            state="disabled"
        )
        self.save_voice_button.pack(fill="x", pady=2)
        
        # Voice library
        lib_label = ctk.CTkLabel(panel, text="Cloned Voice Library:", font=("Arial", 12, "bold"))
        lib_label.pack(pady=(20, 5))
        
        # Scrollable frame for voice items
        self.voice_list_frame = ctk.CTkScrollableFrame(panel, height=300)
        self.voice_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Refresh library button
        refresh_btn = ctk.CTkButton(
            panel,
            text="Refresh Library",
            command=self._refresh_library
        )
        refresh_btn.pack(pady=5)
        
        # Load library
        self._refresh_library()
    
    def _on_audio_selected(self, filepath: str) -> None:
        """Handle audio file selection.
        
        Args:
            filepath: Path to selected audio file
        """
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
                self.audio_player.load_audio(audio, sr)
                self.audio_player.play()
            except Exception as e:
                show_error_dialog(e, "playing reference audio", self)
    
    def _update_char_count(self, event=None) -> None:
        """Update character count label."""
        text = self.gen_text.get("1.0", "end-1c")
        count = len(text)
        self.char_count_label.configure(text=f"{count} characters")
    
    def _generate_speech(self) -> None:
        """Generate speech with voice cloning."""
        logger.info("Starting voice clone speech generation...")
        # Validate inputs
        if not self.ref_audio_path:
            logger.warning("Generate attempted without reference audio")
            messagebox.showerror("Missing Input", "Please select a reference audio file.")
            return
        
        ref_text = self.ref_transcript_text.get("1.0", "end-1c").strip()
        x_vector_mode = self.x_vector_var.get()
        logger.debug(f"X-Vector mode: {x_vector_mode}, Has ref_text: {bool(ref_text)}")
        
        if not x_vector_mode and not ref_text:
            logger.warning("Generate attempted without reference transcript (non-X-Vector mode)")
            messagebox.showerror(
                "Missing Input",
                "Please provide reference transcript or enable X-Vector mode."
            )
            return
        
        gen_text = self.gen_text.get("1.0", "end-1c").strip()
        if not gen_text:
            logger.warning("Generate attempted without generation text")
            messagebox.showerror("Missing Input", "Please enter text to generate.")
            return
        
        logger.info(f"Generation text length: {len(gen_text)} characters")
        logger.debug(f"Reference audio: {self.ref_audio_path}")
        
        # Warn if text is very long
        if len(gen_text) > 500:
            result = messagebox.askyesno(
                "Long Text Warning",
                f"Your text is {len(gen_text)} characters long. This may take 2-5 minutes to generate.\n\n"
                "Consider breaking it into smaller chunks for faster processing.\n\n"
                "Continue anyway?"
            )
            if not result:
                logger.info("User cancelled generation due to long text")
                return
            logger.info("User confirmed generation of long text")
        
        # Disable UI
        self.generate_button.configure(state="disabled", text="Generating...")
        self.progress_bar.set(0)
        self.progress_var.set("Initializing...")
        
        # Load base model if not loaded
        if self.tts_engine.base_model is None:
            logger.info("Base model not loaded, loading now...")
            self.progress_var.set("Loading Base model...")
            try:
                model_size = self.config.get("model_size", "1.7B")
                logger.debug(f"Loading Base model with size: {model_size}")
                self.tts_engine.load_base_model(model_size)
            except Exception as e:
                logger.error(f"Failed to load Base model: {e}")
                show_error_dialog(e, "loading Base model", self)
                self._reset_generate_ui()
                return
        else:
            logger.debug("Base model already loaded")
        
        # Get generation parameters
        language = self.language_combo.get()
        logger.debug(f"Language: {language}")
        self.config.set("last_used_language", language)
        
        def generate_task():
            """Background generation task."""
            logger.info("Starting voice clone generation task...")
            try:
                # Create voice clone prompt if not exists
                logger.info("Creating voice clone prompt...")
                logger.debug(f"Prompt params - ref_audio: {self.ref_audio_path}, x_vector_only: {x_vector_mode}")
                self.current_voice_prompt = self.tts_engine.create_voice_clone_prompt(
                    ref_audio=self.ref_audio_path,
                    ref_text=ref_text if not x_vector_mode else "",
                    x_vector_only_mode=x_vector_mode
                )
                logger.debug("Voice clone prompt created")
                
                # Generate audio with parameters to prevent hanging
                logger.info("Generating cloned voice audio...")
                logger.debug(f"Text length: {len(gen_text)} characters")
                
                # Add generation parameters
                generation_params = {
                    'max_new_tokens': 2048,  # Limit generation length
                    'temperature': 0.7,
                    'do_sample': True
                }
                logger.debug(f"Generation parameters: {generation_params}")
                
                wavs, sr = self.tts_engine.generate_voice_clone(
                    text=gen_text,
                    language=language,
                    voice_clone_prompt=self.current_voice_prompt,
                    **generation_params
                )
                logger.info(f"Voice clone generation completed - {len(wavs)} segments at {sr}Hz")
                
                return wavs, sr
                
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                raise
        
        def on_success(result):
            """Handle successful generation."""
            logger.info("Processing generation success in UI thread")
            try:
                wavs, sr = result
                self.generated_audio = wavs[0]
                self.generated_sr = sr
                
                logger.debug(f"Loading audio into player: {len(self.generated_audio)} samples at {sr}Hz")
                # Update UI
                self.progress_bar.set(1.0)
                self.progress_var.set("Generation complete!")
                self.audio_player.load_audio(self.generated_audio, sr)
                self.save_audio_button.configure(state="normal")
                self.save_voice_button.configure(state="normal")
                
                self._reset_generate_ui()
                
                logger.info("Voice clone generation successful!")
                messagebox.showinfo("Success", "Speech generated successfully!")
            except Exception as e:
                logger.error(f"Error in success callback: {e}", exc_info=True)
                show_error_dialog(e, "processing generation result", self)
        
        def on_error(error):
            """Handle generation error."""
            logger.error(f"Callback received error: {error}")
            show_error_dialog(error, "generating speech", self)
            self._reset_generate_ui()
        
        def progress_update(pct, msg):
            """Update progress during generation."""
            self.progress_bar.set(pct / 100.0)
            self.progress_var.set(msg)
            logger.debug(f"Progress: {pct:.1f}% - {msg}")
        
        # Update UI to show generation started
        self.progress_bar.set(0.1)
        self.progress_var.set("Preparing generation...")
        logger.info("Starting background worker thread...")
        
        # Add periodic progress updates to show it's not frozen
        self._generation_start_time = time.time()
        self._update_generation_progress()
        
        # Run in background with proper callback capture
        def success_wrapper(result):
            logger.info("Generation task completed, scheduling UI update")
            self.after(0, lambda: on_success(result))
        
        def error_wrapper(error):
            logger.error(f"Generation task failed: {error}")
            self.after(0, lambda: on_error(error))
        
        worker = TTSWorker(
            generate_task,
            success_callback=success_wrapper,
            error_callback=error_wrapper
        )
        self.current_worker = worker
        worker.start()
        logger.debug("Worker thread started")
    
    def _update_generation_progress(self) -> None:
        """Update progress indicator periodically during generation."""
        if self.current_worker and self.current_worker.is_alive():
            elapsed = time.time() - self._generation_start_time
            self.progress_var.set(f"Generating... ({int(elapsed)}s elapsed)")
            # Schedule next update in 1 second
            self.after(1000, self._update_generation_progress)
    
    def _reset_generate_ui(self) -> None:
        """Reset generation UI state."""
        logger.debug("Resetting generate UI")
        self.generate_button.configure(state="normal", text="Generate Speech")
        self.progress_bar.set(0)
        self.progress_var.set("")
        self.current_worker = None
    
    def _save_audio(self) -> None:
        """Save generated audio to file."""
        if self.generated_audio is None:
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save Audio",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        
        if filepath:
            if self.generated_sr is None:
                messagebox.showerror("Error", "Audio generation failed: no sample rate available")
                return
            try:
                save_audio(self.generated_audio, self.generated_sr, filepath)
                messagebox.showinfo("Success", f"Audio saved to:\n{filepath}")
            except Exception as e:
                show_error_dialog(e, "saving audio", self)
    
    def _save_to_library(self) -> None:
        """Save cloned voice to library."""
        if self.current_voice_prompt is None:
            messagebox.showerror("Error", "No voice to save. Generate speech first.")
            return
        
        # Dialog for voice name and tags
        dialog = VoiceSaveDialog(self, "Save Cloned Voice")
        self.wait_window(dialog)
        
        if dialog.result:
            try:
                name = dialog.result["name"]
                tags = dialog.result["tags"]
                
                # Save to library
                ref_text = self.ref_transcript_text.get("1.0", "end-1c").strip()
                language = self.language_combo.get()
                
                voice_id = self.voice_library.save_cloned_voice(
                    name=name,
                    ref_audio_path=self.ref_audio_path,
                    ref_text=ref_text,
                    voice_clone_prompt=self.current_voice_prompt,
                    tags=tags,
                    language=language
                )
                
                messagebox.showinfo("Success", f"Voice saved to library: {name}")
                self._refresh_library()
                
                # Refresh narration tab voice list if callback provided
                if self.narration_refresh_callback:
                    logger.debug("Refreshing narration tab voice list")
                    self.narration_refresh_callback()
                
            except Exception as e:
                show_error_dialog(e, "saving voice to library", self)
    
    def _refresh_library(self) -> None:
        """Refresh voice library display."""
        # Clear existing items
        for widget in self.voice_list_frame.winfo_children():
            widget.destroy()
        
        # Load voices
        voices = self.voice_library.get_all_voices(voice_type="cloned")
        
        if not voices:
            no_voices_label = ctk.CTkLabel(
                self.voice_list_frame,
                text="No cloned voices yet",
                text_color="gray"
            )
            no_voices_label.pack(pady=20)
            return
        
        # Display voices
        for voice in voices:
            item = VoiceLibraryItem(
                self.voice_list_frame,
                voice,
                on_load=self._load_voice_from_library,
                on_delete=self._delete_voice_from_library,
                on_play=self._play_voice_sample
            )
            item.pack(fill="x", pady=2)
    
    def _load_voice_from_library(self, voice_data: dict) -> None:
        """Load voice from library."""
        try:
            # Load voice clone prompt
            voice_id = voice_data["id"]
            self.current_voice_prompt = self.voice_library.load_voice_clone_prompt(voice_id)
            
            # Update UI
            self.ref_audio_path = voice_data["ref_audio"]
            self.audio_picker.set_file(self.ref_audio_path)
            self.ref_transcript_text.delete("1.0", "end")
            self.ref_transcript_text.insert("1.0", voice_data["ref_text"])
            
            messagebox.showinfo("Success", f"Loaded voice: {voice_data['name']}")
            
        except Exception as e:
            show_error_dialog(e, "loading voice from library", self)
    
    def _delete_voice_from_library(self, voice_data: dict) -> None:
        """Delete voice from library."""
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Delete voice '{voice_data['name']}' from library?\nThis cannot be undone."
        )
        
        if response:
            try:
                self.voice_library.delete_voice(voice_data["id"])
                self._refresh_library()
                messagebox.showinfo("Success", "Voice deleted from library")
            except Exception as e:
                show_error_dialog(e, "deleting voice", self)
    
    def _play_voice_sample(self, voice_data: dict) -> None:
        """Play voice sample from library."""
        try:
            audio_path = voice_data["ref_audio"]
            audio, sr = load_audio(audio_path)
            self.audio_player.load_audio(audio, sr)
            self.audio_player.play()
        except Exception as e:
            show_error_dialog(e, "playing voice sample", self)


class VoiceSaveDialog(ctk.CTkToplevel):
    """Dialog for saving voice with name and tags."""
    
    def __init__(self, parent, title="Save Voice"):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("400x250")
        self.resizable(False, False)
        
        self.result = None
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        # Name
        name_label = ctk.CTkLabel(self, text="Voice Name:")
        name_label.pack(pady=(20, 5))
        
        self.name_entry = ctk.CTkEntry(self, width=300)
        self.name_entry.pack(pady=5)
        self.name_entry.insert(0, f"Voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Tags
        tags_label = ctk.CTkLabel(self, text="Tags (comma-separated):")
        tags_label.pack(pady=(20, 5))
        
        self.tags_entry = ctk.CTkEntry(self, width=300, placeholder_text="e.g., male, clear, english")
        self.tags_entry.pack(pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(btn_frame, text="Save", command=self._save, width=100)
        save_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self._cancel, width=100)
        cancel_btn.pack(side="left", padx=5)
    
    def _save(self):
        """Save and close."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a voice name.")
            return
        
        tags_text = self.tags_entry.get().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
        
        self.result = {"name": name, "tags": tags}
        self.destroy()
    
    def _cancel(self):
        """Cancel and close."""
        self.result = None
        self.destroy()
