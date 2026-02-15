"""Voice design tab interface."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

from core.audio_utils import save_audio
from utils.error_handler import logger, show_error_dialog
from utils.threading_helpers import TTSWorker
from gui.components import AudioPlayerWidget, VoiceLibraryItem
from gui.tab_voice_clone import VoiceSaveDialog


class VoiceDesignTab(ctk.CTkFrame):
    """Voice design tab."""
    
    EXAMPLE_PROMPTS = [
        "Young female voice, cheerful and energetic, slightly high pitch",
        "Middle-aged male voice, authoritative news anchor tone, deep and confident",
        "Elderly female voice, warm grandmother tone,  gentle and comforting",
        "Teen male voice, slightly shy and nervous, tenor range with occasional voice breaks",
        "Professional businesswoman voice, clear articulation, confident mid-range",
    ]
    
    def __init__(self, parent, tts_engine, voice_library, config, narration_refresh_callback=None):
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.voice_library = voice_library
        self.config = config
        self.narration_refresh_callback = narration_refresh_callback
        
        self.generated_audio = None
        self.generated_sr = None
        self.current_description = ""
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Left panel: Design
        self._create_design_panel()
        
        # Right panel: Library
        self._create_library_panel()
    
    def _create_design_panel(self) -> None:
        """Create voice design panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Voice Design", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Description
        desc_label = ctk.CTkLabel(panel, text="Describe the voice you want to create:")
        desc_label.pack(pady=(10, 5))
        
        self.description_text = ctk.CTkTextbox(panel, height=120)
        self.description_text.pack(fill="x", padx=10, pady=5)
        
        # Example prompts button
        example_btn = ctk.CTkButton(
            panel,
            text="Load Example Prompt",
            command=self._show_examples
        )
        example_btn.pack(pady=5)
        
        # Test text
        test_label = ctk.CTkLabel(panel, text="Test Text:")
        test_label.pack(pady=(20, 5))
        
        self.test_text = ctk.CTkTextbox(panel, height=100)
        self.test_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.test_text.insert("1.0", "Hello, this is a test of the designed voice.")
        
        # Language
        lang_frame = ctk.CTkFrame(panel)
        lang_frame.pack(fill="x", padx=10, pady=10)
        
        lang_label = ctk.CTkLabel(lang_frame, text="Language:")
        lang_label.pack(side="left", padx=5)
        
        languages = ["Auto"] + self.tts_engine.LANGUAGES[1:]
        self.language_combo = ctk.CTkComboBox(lang_frame, values=languages, width=150)
        self.language_combo.set("Auto")
        self.language_combo.pack(side="left", padx=5)
        
        # Generate button
        self.generate_button = ctk.CTkButton(
            panel,
            text="Generate Voice",
            command=self._generate_voice,
            height=40,
            font=("Arial", 14, "bold"),
            fg_color="green"
        )
        self.generate_button.pack(pady=20)
        
        # Progress
        self.progress_bar = ctk.CTkProgressBar(panel)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(panel, text="")
        self.progress_label.pack()
        
        # Audio player
        self.audio_player = AudioPlayerWidget(panel)
        self.audio_player.pack(fill="x", padx=10, pady=10)
        
        # Save buttons
        btn_frame = ctk.CTkFrame(panel)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.save_audio_button = ctk.CTkButton(
            btn_frame,
            text="Save Audio",
            command=self._save_audio,
            state="disabled"
        )
        self.save_audio_button.pack(side="left", padx=5, expand=True, fill="x")
        
        self.save_design_button = ctk.CTkButton(
            btn_frame,
            text="Save to Library",
            command=self._save_to_library,
            state="disabled"
        )
        self.save_design_button.pack(side="left", padx=5, expand=True, fill="x")
    
    def _create_library_panel(self) -> None:
        """Create voice library panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Designed Voices", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Voice list
        self.voice_list_frame = ctk.CTkScrollableFrame(panel)
        self.voice_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Refresh button
        refresh_btn = ctk.CTkButton(panel, text="Refresh Library", command=self._refresh_library)
        refresh_btn.pack(pady=5)
        
        self._refresh_library()
    
    def _show_examples(self) -> None:
        """Show example prompts dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Example Prompts")
        dialog.geometry("600x400")
        dialog.transient(self)
        dialog.grab_set()
        
        label = ctk.CTkLabel(dialog, text="Select an example prompt:", font=("Arial", 14, "bold"))
        label.pack(pady=10)
        
        for prompt in self.EXAMPLE_PROMPTS:
            btn = ctk.CTkButton(
                dialog,
                text=prompt,
                command=lambda p=prompt: self._use_example(p, dialog),
                anchor="w"
            )
            btn.pack(fill="x", padx=20, pady=5)
    
    def _use_example(self, prompt: str, dialog) -> None:
        """Use example prompt."""
        logger.debug(f"Using example prompt: {prompt[:50]}...")
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", prompt)
        dialog.destroy()
    
    def _generate_voice(self) -> None:
        """Generate voice from description."""
        logger.info("Starting voice design generation...")
        description = self.description_text.get("1.0", "end-1c").strip()
        if not description:
            logger.warning("Generate attempted without voice description")
            messagebox.showerror("Missing Input", "Please provide a voice description.")
            return
        
        test_text = self.test_text.get("1.0", "end-1c").strip()
        if not test_text:
            logger.warning("Generate attempted without test text")
            messagebox.showerror("Missing Input", "Please provide test text.")
            return
        
        logger.info(f"Voice description: {description[:100]}...")
        logger.info(f"Test text length: {len(test_text)} characters")
        
        # Load model if needed
        if self.tts_engine.voice_design_model is None:
            logger.info("VoiceDesign model not loaded, loading now...")
            self.progress_label.configure(text="Loading VoiceDesign model...")
            try:
                model_size = self.config.get("model_size", "1.7B")
                logger.debug(f"Loading VoiceDesign model with size: {model_size}")
                self.tts_engine.load_voice_design_model(model_size)
            except Exception as e:
                logger.error(f"Failed to load VoiceDesign model: {e}")
                show_error_dialog(e, "loading VoiceDesign model", self)
                return
        else:
            logger.debug("VoiceDesign model already loaded")
        
        self.current_description = description
        language = self.language_combo.get()
        logger.debug(f"Language: {language}")
        
        self.generate_button.configure(state="disabled", text="Generating...")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Designing voice...")
        
        def generate_task():
            logger.info("Starting voice design generation task...")
            wavs, sr = self.tts_engine.generate_voice_design(
                text=test_text,
                language=language,
                instruct=description
            )
            logger.info(f"Voice design generation completed - {len(wavs)} segments at {sr}Hz")
            return wavs, sr
        
        def on_success(result):
            """Handle successful generation."""
            logger.info("Processing voice design success in UI thread")
            try:
                wavs, sr = result
                self.generated_audio = wavs[0]
                self.generated_sr = sr
                
                logger.debug(f"Loading audio into player: {len(self.generated_audio)} samples at {sr}Hz")
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="Voice generated!")
                self.audio_player.load_audio(self.generated_audio, sr)
                self.save_audio_button.configure(state="normal")
                self.save_design_button.configure(state="normal")
                
                self.generate_button.configure(state="normal", text="Generate Voice")
                logger.info("Voice design generation successful!")
                messagebox.showinfo("Success", "Voice designed successfully!")
            except Exception as e:
                logger.error(f"Error in success callback: {e}", exc_info=True)
                show_error_dialog(e, "processing voice design result", self)
        
        def on_error(error):
            logger.error(f"Voice design generation failed: {error}")
            show_error_dialog(error, "generating voice design", self)
            self.generate_button.configure(state="normal", text="Generate Voice")
            self.progress_bar.set(0)
            self.progress_label.configure(text="")
        
        # Update UI to show generation started
        self.progress_bar.set(0.1)
        self.progress_label.configure(text="Starting generation...")
        logger.info("Starting background worker thread...")
        
        # Run in background with proper callback capture
        def success_wrapper(result):
            logger.info("Voice design task completed, scheduling UI update")
            self.after(0, lambda: on_success(result))
        
        def error_wrapper(error):
            logger.error(f"Voice design task failed: {error}")
            self.after(0, lambda: on_error(error))
        
        worker = TTSWorker(
            generate_task,
            success_callback=success_wrapper,
            error_callback=error_wrapper
        )
        worker.start()
        logger.debug("Worker thread started")
    
    def _save_audio(self) -> None:
        """Save generated audio."""
        if self.generated_audio is None:
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save Audio",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")]
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
        """Save designed voice to library."""
        if self.generated_audio is None or self.generated_sr is None:
            return
        
        dialog = VoiceSaveDialog(self, "Save Designed Voice")
        self.wait_window(dialog)
        
        if dialog.result:
            try:
                # Save audio temporarily
                temp_path = f"output/temp/voice_design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                save_audio(self.generated_audio, self.generated_sr, temp_path)
                
                # Save to library
                voice_id = self.voice_library.save_designed_voice(
                    name=dialog.result["name"],
                    description=self.current_description,
                    sample_audio_path=temp_path,
                    tags=dialog.result["tags"],
                    language=self.language_combo.get()
                )
                
                messagebox.showinfo("Success", f"Voice design saved: {dialog.result['name']}")
                self._refresh_library()
                
                # Refresh narration tab voice list if callback provided
                if self.narration_refresh_callback:
                    logger.debug("Refreshing narration tab voice list")
                    self.narration_refresh_callback()
                
            except Exception as e:
                show_error_dialog(e, "saving voice design", self)
    
    def _refresh_library(self) -> None:
        """Refresh library display."""
        for widget in self.voice_list_frame.winfo_children():
            widget.destroy()
        
        voices = self.voice_library.get_all_voices(voice_type="designed")
        
        if not voices:
            label = ctk.CTkLabel(self.voice_list_frame, text="No designed voices yet", text_color="gray")
            label.pack(pady=20)
            return
        
        for voice in voices:
            item = VoiceLibraryItem(
                self.voice_list_frame,
                voice,
                on_load=self._load_design,
                on_delete=self._delete_design,
                on_play=self._play_sample
            )
            item.pack(fill="x", pady=2)
    
    def _load_design(self, voice_data: dict) -> None:
        """Load voice design."""
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", voice_data.get("description", ""))
        messagebox.showinfo("Success", f"Loaded: {voice_data['name']}")
    
    def _delete_design(self, voice_data: dict) -> None:
        """Delete voice design."""
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Delete voice design '{voice_data['name']}'?"
        )
        if response:
            self.voice_library.delete_voice(voice_data["id"])
            self._refresh_library()
    
    def _play_sample(self, voice_data: dict) -> None:
        """Play voice sample."""
        try:
            from ..core.audio_utils import load_audio
            audio, sr = load_audio(voice_data["sample_audio"])
            self.audio_player.load_audio(audio, sr)
            self.audio_player.play()
        except Exception as e:
            show_error_dialog(e, "playing sample", self)
