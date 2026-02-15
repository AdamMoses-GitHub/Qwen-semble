"""Narration tab interface."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from core.transcript_parser import TranscriptParser
from core.audio_utils import save_audio, merge_audio_segments
from utils.error_handler import logger, show_error_dialog
from utils.threading_helpers import CancellableWorker
from gui.components import AudioPlayerWidget, SegmentListRow


class NarrationTab(ctk.CTkFrame):
    """Multi-voice narration tab."""
    
    def __init__(self, parent, tts_engine, voice_library, config, workspace_dir=None):
        super().__init__(parent)
        
        self.tts_engine = tts_engine
        self.voice_library = voice_library
        self.config = config
        self.workspace_dir = workspace_dir
        self.parser = TranscriptParser()
        self._base_model_loading = False
        
        self.transcript_text = ""
        self.segments = []
        self.voice_mapping = {}
        self.generated_segments = []
        self.worker = None
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Left panel: Input and generation
        self._create_input_panel()
        
        # Right panel: Voice assignment
        self._create_assignment_panel()
    
    def _create_input_panel(self) -> None:
        """Create transcript input panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Transcript Narration", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Load transcript button
        load_btn = ctk.CTkButton(
            panel,
            text="Load Transcript File (.txt)",
            command=self._load_transcript
        )
        load_btn.pack(pady=5)
        
        # Transcript text
        self.transcript_textbox = ctk.CTkTextbox(panel, height=200)
        self.transcript_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Statistics
        self.stats_label = ctk.CTkLabel(panel, text="", text_color="gray")
        self.stats_label.pack()
        
        # Mode selection
        mode_frame = ctk.CTkFrame(panel)
        mode_frame.pack(fill="x", padx=10, pady=10)
        
        mode_label = ctk.CTkLabel(mode_frame, text="Voice Assignment Mode:")
        mode_label.pack(side="left", padx=5)
        
        self.mode_var = ctk.StringVar(value="single")
        self.mode_buttons = ctk.CTkSegmentedButton(
            mode_frame,
            values=["single", "manual", "annotated"],
            variable=self.mode_var,
            command=self._on_mode_change
        )
        self.mode_buttons.pack(side="left", padx=5)
        
        # Single voice selection (shown when mode is "single")
        self.single_voice_frame = ctk.CTkFrame(panel)
        self.single_voice_frame.pack(fill="x", padx=10, pady=5)
        
        voice_label = ctk.CTkLabel(self.single_voice_frame, text="Voice:")
        voice_label.pack(side="left", padx=5)
        
        self.voice_combo = ctk.CTkComboBox(self.single_voice_frame, values=[], width=200)
        self.voice_combo.pack(side="left", padx=5)
        self._update_voice_list()
        
        # Parse button
        self.parse_button = ctk.CTkButton(
            panel,
            text="Parse Transcript",
            command=self._parse_transcript
        )
        self.parse_button.pack(pady=10)
        
        # Generate button
        self.generate_button = ctk.CTkButton(
            panel,
            text="Generate Narration",
            command=self._generate_narration,
            height=40,
            font=("Arial", 14, "bold"),
            fg_color="green",
            state="disabled"
        )
        self.generate_button.pack(pady=10)
        
        # Progress
        self.progress_bar = ctk.CTkProgressBar(panel)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(panel, text="")
        self.progress_label.pack()
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            panel,
            text="Cancel",
            command=self._cancel_generation,
            state="disabled"
        )
        self.cancel_button.pack(pady=5)
        
        # Output info
        self.output_label = ctk.CTkLabel(panel, text="", text_color="green")
        self.output_label.pack(pady=10)
    
    def _create_assignment_panel(self) -> None:
        """Create voice assignment panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Voice Assignment", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Segments list (for manual mode)
        self.segments_frame = ctk.CTkScrollableFrame(panel)
        self.segments_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Info label
        self.assignment_info_label = ctk.CTkLabel(
            panel,
            text="Load and parse a transcript to assign voices",
            text_color="gray"
        )
        self.assignment_info_label.pack(pady=10)
    
    def _load_transcript(self) -> None:
        """Load transcript from file."""
        filepath = filedialog.askopenfilename(
            title="Load Transcript",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            logger.info(f"Loading transcript from file: {filepath}")
            try:
                text = self.parser.load_transcript_file(filepath)
                self.transcript_textbox.delete("1.0", "end")
                self.transcript_textbox.insert("1.0", text)
                self.transcript_text = text
                
                # Update statistics
                stats = self.parser.get_statistics(text)
                stats_text = f"{stats['words']} words, {stats['sentences']} sentences"
                self.stats_label.configure(text=stats_text)
                logger.info(f"Transcript loaded successfully: {stats_text}")
                
                messagebox.showinfo("Success", f"Transcript loaded:\n{stats_text}")
                
            except Exception as e:
                show_error_dialog(e, "loading transcript", self)
    
    def _on_mode_change(self, mode: str) -> None:
        """Handle mode change."""
        logger.debug(f"Narration mode changed to: {mode}")
        if mode == "single":
            self.single_voice_frame.pack(fill="x", padx=10, pady=5)
        else:
            self.single_voice_frame.pack_forget()
    
    def refresh_voice_list(self) -> None:
        """Public method to refresh voice list (called from other tabs)."""
        self._update_voice_list()
    
    def _update_voice_list(self) -> None:
        """Update available voices list."""
        logger.debug("Updating voice list...")
        # Get preset speakers
        voices = self.tts_engine.get_supported_speakers()
        
        # Add library voices
        lib_voices = self.voice_library.get_all_voices()
        for voice in lib_voices:
            voices.append(f"[Library] {voice['name']}")
        
        logger.debug(f"Found {len(voices)} available voices")
        self.voice_combo.configure(values=voices)
        if voices:
            self.voice_combo.set(voices[0])
    
    def _parse_transcript(self) -> None:
        """Parse transcript into segments."""
        logger.info("Starting transcript parsing...")
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        if not text:
            logger.warning("Parse attempted with empty transcript")
            messagebox.showerror("Error", "Please load or enter a transcript first.")
            return
        
        self.transcript_text = text
        mode = self.mode_var.get()
        logger.info(f"Parsing in {mode} mode, text length: {len(text)} characters")
        
        try:
            # Parse based on mode
            if mode == "single":
                default_voice = self.voice_combo.get()
                logger.debug(f"Using single voice: {default_voice}")
                self.segments = self.parser.parse_transcript(text, mode="single", default_voice=default_voice)
                self.assignment_info_label.configure(text=f"Mode: Single voice ({default_voice})")
            
            elif mode == "manual":
                logger.debug("Parsing for manual voice assignment")
                self.segments = self.parser.parse_transcript(text, mode="manual")
                self._show_manual_assignment()
            
            elif mode == "annotated":
                logger.debug("Parsing annotated transcript")
                self.segments = self.parser.parse_transcript(text, mode="annotated")
                detected_speakers = self.parser.detect_speakers(text)
                speaker_text = ", ".join(detected_speakers) if detected_speakers else "None"
                logger.debug(f"Detected speakers: {speaker_text}")
                self.assignment_info_label.configure(text=f"Detected speakers: {speaker_text}")
            
            logger.info(f"Successfully parsed {len(self.segments)} segments")
            self.generate_button.configure(state="normal")
            messagebox.showinfo("Success", f"Parsed {len(self.segments)} segments")
            
        except Exception as e:
            show_error_dialog(e, "parsing transcript", self)
    
    def _show_manual_assignment(self) -> None:
        """Show manual voice assignment UI."""
        # Clear segments frame
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        
        voices = self.voice_combo.cget("values")
        
        # Show first 50 segments (performance)
        max_show = min(50, len(self.segments))
        for i, segment in enumerate(self.segments[:max_show]):
            preview = self.parser.preview_segment(segment, max_length=60)
            row = SegmentListRow(
                self.segments_frame,
                segment.segment_id,
                preview,
                voices,
                on_voice_change=self._on_segment_voice_change
            )
            row.pack(fill="x", pady=2)
        
        if len(self.segments) > max_show:
            more_label = ctk.CTkLabel(
                self.segments_frame,
                text=f"... and {len(self.segments) - max_show} more segments",
                text_color="gray"
            )
            more_label.pack(pady=10)
        
        self.assignment_info_label.configure(text=f"Assign voices to {len(self.segments)} segments")
    
    def _on_segment_voice_change(self, segment_id: int, voice: str) -> None:
        """Handle segment voice change in manual mode."""
        self.voice_mapping[segment_id] = voice
    
    def _generate_narration(self) -> None:
        """Generate narration from segments."""
        logger.info("Starting narration generation...")
        if not self.segments:
            logger.warning("Generate attempted with no segments")
            messagebox.showerror("Error", "No segments to generate. Parse transcript first.")
            return
        
        # Ensure all segments have voices assigned
        mode = self.mode_var.get()
        logger.debug(f"Generation mode: {mode}, Total segments: {len(self.segments)}")
        
        if mode == "manual":
            logger.debug("Applying voice mappings for manual mode")
            # Update segments with voice mapping
            for segment in self.segments:
                if segment.segment_id in self.voice_mapping:
                    segment.voice = self.voice_mapping[segment.segment_id]
                elif not segment.voice:
                    segment.voice = self.voice_combo.get()  # Use default
        
        # Validate voices
        available_voices = self.voice_combo.cget("values")
        logger.debug(f"Validating voices against {len(available_voices)} available voices")
        is_valid, missing = self.parser.validate_segment_voices(self.segments, available_voices)
        
        if not is_valid:
            logger.error(f"Voice validation failed. Missing voices: {missing}")
            messagebox.showerror(
                "Validation Error",
                f"Some segments reference unknown voices:\n{', '.join(missing)}\n\n"
                "Check speaker annotations or voice assignments."
            )
            return
        
        logger.info("Voice validation passed, starting generation process...")
        # Disable UI
        self.generate_button.configure(state="disabled")
        self.parse_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        
        self.generated_segments = []
        
        def generate_task(progress_callback):
            """Background generation task."""
            segments_audio = []
            total = len(self.segments)
            logger.info(f"Starting background generation task for {total} segments")
            
            for i, segment in enumerate(self.segments):
                # Check for cancellation
                if self.worker and self.worker.stop_flag.is_set():
                    logger.info("Generation cancelled by user")
                    return None
                
                # Update progress
                progress = int((i / total) * 100)
                progress_callback(progress, f"Processing segment {i+1}/{total}")
                logger.debug(f"Generating segment {i+1}/{total} - voice: {segment.voice}, text: '{segment.text[:50]}...'")
                
                # Generate audio for segment
                voice = segment.voice
                text = segment.text
                
                # Use appropriate model based on voice
                if voice in self.tts_engine.get_supported_speakers():
                    # Preset voice - use CustomVoice model
                    logger.debug(f"Using preset voice: {voice}")
                    wavs, sr = self.tts_engine.generate_custom_voice(
                        text=text,
                        language="Auto",
                        speaker=voice
                    )
                else:
                    # Library voice - need to load voice clone prompt or handle designed voice
                    logger.debug(f"Attempting to use library voice: {voice}")
                    voice_data = self.voice_library.get_voice_by_name(voice)
                    
                    if voice_data:
                        if voice_data["type"] == "cloned":
                            # Cloned voice - load prompt and use Base model
                            logger.debug(f"Loading cloned voice: {voice_data['id']}")
                            try:
                                # Ensure Base model is loaded
                                if self.tts_engine.base_model is None:
                                    logger.info("Base model not loaded, loading now...")
                                    model_size = self.config.get("model_size", "1.7B")
                                    self.tts_engine.load_base_model(model_size)
                                
                                # Load voice clone prompt
                                voice_prompt = self.voice_library.load_voice_clone_prompt(voice_data["id"])
                                
                                # Generate with cloned voice
                                wavs, sr = self.tts_engine.generate_voice_clone(
                                    text=text,
                                    language=voice_data.get("language", "Auto"),
                                    voice_clone_prompt=voice_prompt
                                )
                                logger.debug(f"Cloned voice generation successful")
                                
                                # Track usage
                                self.voice_library.increment_usage(voice_data["id"])
                            except Exception as e:
                                logger.error(f"Failed to use cloned voice: {e}")
                                raise
                        
                        elif voice_data["type"] == "designed":
                            # Designed voice - use VoiceDesign model with description
                            logger.debug(f"Using designed voice: {voice_data['id']}")
                            try:
                                # Ensure VoiceDesign model is loaded
                                if self.tts_engine.voice_design_model is None:
                                    logger.info("VoiceDesign model not loaded, loading now...")
                                    model_size = self.config.get("model_size", "1.7B")
                                    self.tts_engine.load_voice_design_model(model_size)
                                
                                # Generate with voice design
                                wavs, sr = self.tts_engine.generate_voice_design(
                                    text=text,
                                    language=voice_data.get("language", "Auto"),
                                    instruct=voice_data.get("description", "")
                                )
                                logger.debug(f"Designed voice generation successful")
                                
                                # Track usage
                                self.voice_library.increment_usage(voice_data["id"])
                            except Exception as e:
                                logger.error(f"Failed to use designed voice: {e}")
                                raise
                        else:
                            raise ValueError(f"Unknown voice type: {voice_data['type']}")
                    else:
                        # Voice not found - fall back to default
                        logger.warning(f"Voice {voice} not found in library, using default preset")
                        wavs, sr = self.tts_engine.generate_custom_voice(
                            text=text,
                            language="Auto",
                            speaker=self.tts_engine.get_supported_speakers()[0]
                        )
                
                logger.debug(f"Segment {i+1} generated successfully")
                segments_audio.append((wavs[0], sr))
            
            logger.info(f"All {total} segments generated successfully")
            return segments_audio
        
        def on_progress(percentage, message):
            """Update progress during generation."""
            self.progress_bar.set(percentage / 100.0)
            self.progress_label.configure(text=message)
            logger.debug(f"Narration progress: {percentage:.1f}% - {message}")
        
        def on_success(result):
            """Handle successful narration generation."""
            logger.info("Processing narration success in UI thread")
            try:
                if result is None:
                    # Cancelled
                    logger.info("Narration generation was cancelled")
                    self.progress_label.configure(text="Generation cancelled")
                    self._reset_generate_ui()
                    return
                
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="Merging segments...")
                logger.debug(f"Merging {len(result)} audio segments...")
                
                # Merge segments
                audio_segments = [seg[0] for seg in result]
                sr = result[0][1]
                merged = merge_audio_segments(audio_segments, sr)
                
                # Save output
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if self.workspace_dir:
                    output_dir = self.workspace_dir / "narrations" / f"narration_{timestamp}"
                else:
                    output_dir = Path(f"output/narrations/narration_{timestamp}")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / "narration_full.wav"
                logger.info(f"Saving narration to: {output_file}")
                save_audio(merged, sr, str(output_file))
                
                self.output_label.configure(text=f"Saved: {output_file}")
                self.progress_label.configure(text="Complete!")
                
                self._reset_generate_ui()
                logger.info("Narration generation completed successfully")
                messagebox.showinfo("Success", f"Narration generated!\n\nSaved to:\n{output_file}")
            except Exception as e:
                logger.error(f"Error in success callback: {e}", exc_info=True)
                show_error_dialog(e, "processing narration result", self)
        
        def on_error(error):
            """Handle narration generation error."""
            logger.error(f"Narration generation failed: {error}")
            show_error_dialog(error, "generating narration", self)
            self._reset_generate_ui()
        
        # Start generation with proper callback capture
        logger.info("Starting narration background worker thread...")
        
        def success_wrapper(result):
            logger.info("Narration task completed, scheduling UI update")
            self.after(0, lambda: on_success(result))
        
        def error_wrapper(error):
            logger.error(f"Narration task failed: {error}")
            self.after(0, lambda: on_error(error))
        
        self.worker = CancellableWorker(
            generate_task,
            kwargs={"progress_callback": on_progress},
            success_callback=success_wrapper,
            error_callback=error_wrapper
        )
        self.worker.start()
        logger.debug("Worker thread started")
    
    def _cancel_generation(self) -> None:
        """Cancel current generation."""
        if self.worker:
            self.worker.stop()
            self.cancel_button.configure(state="disabled")
    
    def _reset_generate_ui(self) -> None:
        """Reset generation UI."""
        self.generate_button.configure(state="normal")
        self.parse_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.worker = None
