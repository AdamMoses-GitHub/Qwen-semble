"""Narration tab interface."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from core.transcript_parser import TranscriptParser
from core.audio_utils import save_audio, merge_audio_segments
from utils.error_handler import logger, show_error_dialog
from utils.threading_helpers import CancellableWorker
from utils.theme import get_theme_colors
from gui.components import AudioPlayerWidget, SegmentListRow, ColoredPreviewWindow
from gui.voice_browser import VoiceBrowserWidget
from gui.speaker_assignment import SpeakerAssignmentPanel


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
        
        # Selected voice for single mode
        self.selected_voice_data = None
        
        # Speaker assignment panel for annotated mode
        self.speaker_assignment_panel = None
        
        # Segment rows for manual mode
        self.segment_rows = {}
        
        # Colored preview button reference
        self.colored_preview_button = None
        
        self._create_ui()
        
        # Pack the frame into parent
        self.pack(fill="both", expand=True)
    
    def _create_mode_selector(self) -> None:
        """Create voice assignment mode selector at top."""
        mode_panel = ctk.CTkFrame(self, height=120)
        mode_panel.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(5, 0))
        mode_panel.grid_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            mode_panel,
            text="Voice Assignment Mode",
            font=("Arial", 14, "bold")
        )
        title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Container for radio buttons and explainers
        content_frame = ctk.CTkFrame(mode_panel, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.mode_var = ctk.StringVar(value="single")
        
        # Mode options with explainers
        modes = [
            ("single", "Single Voice", "Use one voice for the entire narration"),
            ("manual", "Segment Assignment", "Assign voices to text blocks separated by blank lines"),
            ("annotated", "Annotated Speakers", "Auto-detect speakers from [Name]: dialogue format")
        ]
        
        for idx, (mode_value, mode_label, explainer) in enumerate(modes):
            # Radio button
            radio = ctk.CTkRadioButton(
                content_frame,
                text=mode_label,
                variable=self.mode_var,
                value=mode_value,
                command=lambda: self._on_mode_change(self.mode_var.get()),
                font=("Arial", 12, "bold")
            )
            radio.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
            
            # Explainer text
            explainer_label = ctk.CTkLabel(
                content_frame,
                text=explainer,
                font=("Arial", 11),
                text_color="gray",
                anchor="w"
            )
            explainer_label.grid(row=idx, column=1, sticky="w", padx=(10, 5), pady=2)
    
    def _create_ui(self) -> None:
        """Create tab UI."""
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)  # Mode selector row
        self.rowconfigure(1, weight=1)  # Main content row
        
        # Mode selector at top
        self._create_mode_selector()
        
        # Left panel: Input and generation
        self._create_input_panel()
        
        # Right panel: Voice assignment
        self._create_assignment_panel()
    
    def _create_input_panel(self) -> None:
        """Create transcript input panel."""
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(panel, text="Transcript Narration", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Button container for Load and Parse buttons
        button_container = ctk.CTkFrame(panel, fg_color="transparent")
        button_container.pack(pady=5)
        
        # Load transcript button
        load_btn = ctk.CTkButton(
            button_container,
            text="Load Transcript File (.txt)",
            command=self._load_transcript,
            width=200
        )
        load_btn.pack(side="left", padx=5)
        
        # Parse text area button
        parse_btn = ctk.CTkButton(
            button_container,
            text="Parse And Check Text For Segments Or Speakers",
            command=self._parse_text_area,
            width=300
        )
        parse_btn.pack(side="left", padx=5)
        
        # Show Colored Preview button
        self.colored_preview_button = ctk.CTkButton(
            button_container,
            text="Show Colored Preview",
            command=self._show_colored_preview,
            width=180,
            state="disabled"
        )
        self.colored_preview_button.pack(side="left", padx=5)
        
        # Transcript text
        self.transcript_textbox = ctk.CTkTextbox(panel, height=200)
        self.transcript_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Statistics
        self.stats_label = ctk.CTkLabel(panel, text="", text_color="gray")
        self.stats_label.pack()
        
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
        self.assignment_panel = ctk.CTkFrame(self)
        self.assignment_panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        title = ctk.CTkLabel(self.assignment_panel, text="Voice Assignment", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Container for dynamic content - split into left (assignment) and right (explanation)
        self.assignment_content_frame = ctk.CTkFrame(self.assignment_panel)
        self.assignment_content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configure 2-column grid layout (75% assignment, 25% explainer)
        self.assignment_content_frame.columnconfigure(0, weight=3)  # Left: assignments (75%)
        self.assignment_content_frame.columnconfigure(1, weight=1)  # Right: explanations (25%)
        self.assignment_content_frame.rowconfigure(0, weight=1)
        
        # Left frame for assignment UI
        self.assignment_left_frame = ctk.CTkFrame(self.assignment_content_frame)
        self.assignment_left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        
        # Right frame for mode explanations
        self.assignment_right_frame = ctk.CTkFrame(self.assignment_content_frame)
        self.assignment_right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        
        # Segments list (for manual and single mode)
        self.segments_frame = ctk.CTkScrollableFrame(self.assignment_left_frame)
        self.segments_frame.pack(fill="both", expand=True)
        
        # Mode explanation label in right frame
        self.mode_explanation_label = ctk.CTkLabel(
            self.assignment_right_frame,
            text="",
            wraplength=250,
            justify="left",
            anchor="nw",
            font=("Arial", 11)
        )
        self.mode_explanation_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Parse Status label (larger, bold font)
        self.assignment_info_label = ctk.CTkLabel(
            self.assignment_panel,
            text="Select a voice assignment mode to begin",
            text_color="gray",
            font=("Arial", 14, "bold")
        )
        self.assignment_info_label.pack(pady=10)
        
        # Initialize with single voice mode UI
        self._update_mode_ui("single")
    
    def _get_color_palette(self):
        """Get the shared color palette for segments and speakers.
        
        Returns:
            list: Array of 8 distinct colors
        """
        return [
            "#3b82f6",  # blue
            "#ec4899",  # pink
            "#10b981",  # green
            "#f59e0b",  # amber
            "#8b5cf6",  # violet
            "#ef4444",  # red
            "#14b8a6",  # teal
            "#f97316",  # orange
        ]
    
    def _show_colored_preview(self) -> None:
        """Open window showing colored transcript preview."""
        if len(self.segments) == 0:
            return
        
        # Open colored preview window
        ColoredPreviewWindow(
            self,
            segments=self.segments,
            parser=self.parser,
            colors=self._get_color_palette(),
            mode=self.mode_var.get(),
            speaker_assignment_panel=self.speaker_assignment_panel
        )
    
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
                
                # Auto-parse the loaded transcript
                logger.debug("Auto-parsing loaded transcript...")
                self._parse_transcript(show_messages=False)
                
            except Exception as e:
                show_error_dialog(e, "loading transcript", self)
    
    def _parse_text_area(self) -> None:
        """Parse the current text in the text area."""
        logger.info("Parsing text area...")
        try:
            # Get text from textbox
            text = self.transcript_textbox.get("1.0", "end-1c").strip()
            
            if not text:
                logger.warning("Parse attempted with empty text area")
                messagebox.showwarning("Empty Text", "Please enter or load text to parse.")
                return
            
            self.transcript_text = text
            
            # Update statistics
            stats = self.parser.get_statistics(text)
            stats_text = f"{stats['words']} words, {stats['sentences']} sentences"
            self.stats_label.configure(text=stats_text)
            logger.info(f"Text area statistics: {stats_text}")
            
            # Parse the transcript without popup confirmation
            self._parse_transcript(show_messages=False)
            
        except Exception as e:
            show_error_dialog(e, "parsing text area", self)
    
    def _on_mode_change(self, mode: str) -> None:
        """Handle mode change."""
        logger.debug(f"Narration mode changed to: {mode}")
        
        # Always update UI for the new mode
        self._update_mode_ui(mode)
    
    def _browse_single_voice(self) -> None:
        """Open voice browser for single voice mode."""
        logger.debug("Opening voice browser for single voice mode")
        browser = VoiceBrowserWidget(
            self,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            on_select=self._on_single_voice_selected
        )
        browser.wait_window()
    
    def _on_single_voice_selected(self, voice_data: dict) -> None:
        """Handle voice selection for single voice mode."""
        self.selected_voice_data = voice_data
        voice_name = voice_data['name']
        voice_type = voice_data.get('type', 'cloned')
        
        logger.info(f"Selected voice for single voice mode: {voice_name} ({voice_type})")
        
        # Trigger re-parse to update UI
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        if text:
            self._parse_transcript(show_messages=False)
    
    def refresh_voice_list(self) -> None:
        """Public method to refresh voice list (called from other tabs)."""
        # Voice browser uses voice_library directly, so no refresh needed
        # But we should reset selection if the selected voice was deleted
        if self.selected_voice_data:
            voice_name = self.selected_voice_data['name']
            voice_type = self.selected_voice_data.get('type', 'cloned')
            
            # Check if voice still exists in library
            lib_voices = self.voice_library.get_all_voices()
            if not any(v['name'] == voice_name for v in lib_voices):
                logger.warning(f"Previously selected voice '{voice_name}' no longer exists")
                self.selected_voice_data = None
                # Re-parse to update UI if there's text
                text = self.transcript_textbox.get("1.0", "end-1c").strip()
                if text:
                    self._parse_transcript(show_messages=False)
    
    def _update_voice_list(self) -> None:
        """Update available voices list (deprecated - using browser now)."""
        # This method is deprecated but kept for backward compatibility
        # The voice browser now handles all voice selection
        pass
    
    def _parse_transcript(self, show_messages: bool = True) -> None:
        """Parse transcript into segments.
        
        Args:
            show_messages: Whether to show success/error messageboxes
        """
        logger.info("Starting transcript parsing...")
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        if not text:
            logger.warning("Parse attempted with empty transcript")
            if show_messages:
                messagebox.showerror("Error", "Please load or enter a transcript first.")
            return
        
        self.transcript_text = text
        mode = self.mode_var.get()
        logger.info(f"Parsing in {mode} mode, text length: {len(text)} characters")
        
        try:
            # Parse based on mode
            if mode == "single":
                # Use selected voice or default to first available voice
                if not self.selected_voice_data:
                    # Try to get first available voice from library
                    all_voices = self.voice_library.get_all_voices()
                    if all_voices:
                        self.selected_voice_data = all_voices[0]
                        default_voice = all_voices[0]['name']
                        logger.info(f"No voice selected, using first available: {default_voice}")
                    else:
                        # No voices in library - user must create one first
                        if show_messages:
                            messagebox.showerror(
                                "No Voices Available", 
                                "No voices found in library.\n\n"
                                "Please create a voice first:\n"
                                "• Go to 'Voice Cloning' tab to clone a voice, or\n"
                                "• Go to 'Voice Design' tab to design a voice"
                            )
                        logger.error("No voices available in library")
                        return
                else:
                    default_voice = self.selected_voice_data['name']
                
                logger.debug(f"Using single voice: {default_voice}")
                self.segments = self.parser.parse_transcript(text, mode="single", default_voice=default_voice)
                self._show_single_voice_assignment()
            
            elif mode == "manual":
                logger.debug("Parsing for segment voice assignment")
                self.segments = self.parser.parse_transcript(text, mode="manual")
                self._show_manual_assignment()
            
            elif mode == "annotated":
                logger.debug("Parsing annotated transcript")
                self.segments = self.parser.parse_transcript(text, mode="annotated")
                detected_speakers = self.parser.detect_speakers(text)
                
                if not detected_speakers:
                    logger.warning("No speakers detected in annotated transcript")
                    if show_messages:
                        messagebox.showwarning(
                            "No Speakers Detected",
                            "No speaker annotations found in the transcript.\n"
                            "Use format: [SpeakerName]: dialogue"
                        )
                    self._show_annotated_assignment_empty()
                    return
                
                # Count segments per speaker
                segment_counts = {}
                for segment in self.segments:
                    speaker = segment.voice  # In annotated mode, voice field contains speaker name
                    segment_counts[speaker] = segment_counts.get(speaker, 0) + 1
                
                logger.debug(f"Detected {len(detected_speakers)} speakers: {', '.join(detected_speakers)}")
                self._show_annotated_assignment(detected_speakers, segment_counts)
            
            logger.info(f"Successfully parsed {len(self.segments)} segments")
            # Generate button will be enabled/disabled by _update_parse_status based on assignments
            self._update_parse_status()
            if show_messages:
                messagebox.showinfo("Success", f"Parsed {len(self.segments)} segments")
            
        except Exception as e:
            if show_messages:
                show_error_dialog(e, "parsing transcript", self)
            else:
                logger.error(f"Error parsing transcript: {e}")
    
    def _show_manual_assignment(self) -> None:
        """Show segment voice assignment UI."""
        # Hide speaker assignment panel and show segments frame
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.pack_forget()
        
        # Ensure segments frame is visible
        self.segments_frame.pack(fill="both", expand=True)
        
        # Clear segments frame and segment rows storage
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        self.segment_rows = {}
        
        # Handle empty segments
        if len(self.segments) == 0:
            empty_label = ctk.CTkLabel(
                self.segments_frame,
                text="Load a transcript to assign voices to segments",
                text_color="gray",
                font=("Arial", 12)
            )
            empty_label.pack(pady=40)
            self._update_parse_status()
            return
        
        # Get shared color palette for segments
        segment_colors = self._get_color_palette()
        
        # Show first 50 segments (performance)
        max_show = min(50, len(self.segments))
        total_segments = len(self.segments)
        for i, segment in enumerate(self.segments[:max_show]):
            preview = self.parser.preview_segment(segment, max_length=80)
            segment_color = segment_colors[i % len(segment_colors)]
            row = SegmentListRow(
                self.segments_frame,
                segment.segment_id,
                preview,
                total_segments,
                segment_color,
                on_voice_select=self._browse_voice_for_segment
            )
            row.pack(fill="x", pady=5, padx=5)
            self.segment_rows[segment.segment_id] = row
        
        if len(self.segments) > max_show:
            more_label = ctk.CTkLabel(
                self.segments_frame,
                text=f"... and {len(self.segments) - max_show} more segments",
                text_color="gray"
            )
            more_label.pack(pady=10)
        
        self._update_parse_status()
    
    def _show_single_voice_assignment(self) -> None:
        """Show single voice assignment UI."""
        # Hide other panels
        self.segments_frame.pack_forget()
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.pack_forget()
        
        # Clear segments frame
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        
        # Re-pack segments frame for single voice UI
        self.segments_frame.pack(fill="both", expand=True)
        
        # Create single row for voice assignment
        row_frame = ctk.CTkFrame(self.segments_frame)
        row_frame.pack(fill="x", pady=10, padx=5)
        row_frame.columnconfigure(0, weight=0)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(2, weight=0)
        
        # Voice indicator/color badge
        color_badge = ctk.CTkFrame(row_frame, width=5, height=30, fg_color="#3b82f6")
        color_badge.grid(row=0, column=0, sticky="w", padx=(5, 2))
        color_badge.grid_propagate(False)
        
        # Label
        label = ctk.CTkLabel(
            row_frame,
            text="Single Voice",
            font=("Arial", 13, "bold"),
            anchor="w"
        )
        label.grid(row=0, column=0, sticky="w", padx=(15, 5))
        
        # Current voice display
        if self.selected_voice_data:
            voice_name = self.selected_voice_data['name']
            voice_type = self.selected_voice_data.get('type', 'cloned')
            display_text = f"{voice_name} ({voice_type})"
            colors = get_theme_colors()
            text_color = colors["text_primary"]
        else:
            display_text = "No voice selected"
            colors = get_theme_colors()
            text_color = colors["text_secondary"]
        
        voice_display = ctk.CTkLabel(
            row_frame,
            text=display_text,
            anchor="w",
            text_color=text_color
        )
        voice_display.grid(row=0, column=1, sticky="w", padx=10)
        
        # Select button
        select_btn = ctk.CTkButton(
            row_frame,
            text="Select Voice",
            width=120,
            command=self._browse_single_voice
        )
        select_btn.grid(row=0, column=2, sticky="e", padx=5)
        
        # Update Parse Status
        self._update_parse_status()
    
    def _update_mode_ui(self, mode: str) -> None:
        """Update voice assignment UI for current mode (with or without parsed text).
        
        This method orchestrates UI updates when mode changes, regardless of whether
        transcript text exists. It either parses and populates data, or shows empty state.
        """
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        
        if text:
            # Parse and populate with data
            logger.debug(f"Parsing transcript for mode: {mode}")
            self._parse_transcript(show_messages=False)
        else:
            # Show empty state for this mode
            logger.debug(f"Showing empty state for mode: {mode}")
            if mode == "single":
                self._show_single_voice_assignment()
            elif mode == "manual":
                self._show_manual_assignment()
            elif mode == "annotated":
                self._show_annotated_assignment_empty()
        
        # Update mode explanation text
        self._update_mode_explanation(mode)
    
    def _update_mode_explanation(self, mode: str) -> None:
        """Update the explanation text in the right panel based on current mode."""
        explanations = {
            "single": (
                "Single Voice Mode\n\n"
                "How it works:\n"
                "• Uses one voice for the entire narration\n"
                "• No speaker detection or parsing\n"
                "• The transcript is narrated as-is\n\n"
                "Voice Assignment:\n"
                "• Select your preferred voice above\n"
                "• The same voice will be used for all text\n\n"
                "Best for:\n"
                "• Audiobooks\n"
                "• Simple narrations\n"
                "• Consistent voice throughout"
            ),
            "manual": (
                "Segment Assignment Mode\n\n"
                "What is a Segment?\n"
                "A segment = a block of text separated by blank lines.\n"
                "Text is auto-split wherever there's a blank line.\n\n"
                "Segment Detection Rules:\n"
                "• Splits at: blank lines (empty line between text)\n"
                "• Multiple sentences in one block = one segment\n"
                "• Line breaks within a block are preserved\n"
                "• Each text block = one assignable segment\n\n"
                "Examples:\n\n"
                "Input with blank line:\n"
                "Hello my name is Sam.\n"
                "\n"
                "Hello my name is Susan.\n"
                "→ Segment 1: \"Hello my name is Sam.\"\n"
                "→ Segment 2: \"Hello my name is Susan.\"\n\n"
                "Input without blank line:\n"
                "Hello my name is Sam.\n"
                "Hello my name is Susan.\n"
                "→ Segment 1: \"Hello my name is Sam.\n"
                "Hello my name is Susan.\"\n\n"
                "Voice Assignment:\n"
                "• Select a voice for each segment individually\n"
                "• Different segments can use different voices\n\n"
                "Best for:\n"
                "• Paragraph-level voice control\n"
                "• Narrations with distinct sections\n"
                "• Organizing longer texts by topic/speaker"
            ),
            "annotated": (
                "Annotated Speaker Mode\n\n"
                "How it works:\n"
                "• Automatically detects speakers from text\n"
                "• Uses [SpeakerName]: dialogue format\n"
                "• Groups all lines by speaker\n\n"
                "Format Example:\n"
                "[Alice]: Hello there!\n"
                "[Bob]: Hi Alice, how are you?\n"
                "[Alice]: I'm doing great!\n\n"
                "Voice Assignment:\n"
                "• Assign one voice per detected speaker\n"
                "• All lines by that speaker use same voice\n\n"
                "Best for:\n"
                "• Dialogue scripts\n"
                "• Plays and screenplays\n"
                "• Multi-character conversations"
            )
        }
        
        explanation_text = explanations.get(mode, "")
        self.mode_explanation_label.configure(text=explanation_text)
    
    def _show_annotated_assignment_empty(self) -> None:
        """Show empty state for annotated mode (no speakers detected or no text)."""
        # Hide other panels
        self.segments_frame.pack_forget()
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.destroy()
            self.speaker_assignment_panel = None
        
        # Clear segments frame and show empty message
        for widget in self.segments_frame.winfo_children():
            widget.destroy()
        
        self.segments_frame.pack(fill="both", expand=True)
        
        empty_label = ctk.CTkLabel(
            self.segments_frame,
            text="Load a transcript with [Speaker]: format\nto detect and assign speakers",
            text_color="gray",
            font=("Arial", 12),
            justify="center"
        )
        empty_label.pack(pady=40)
        
        self._update_parse_status()
    
    def _show_annotated_assignment(self, speakers: list, segment_counts: dict) -> None:
        """Show annotated mode speaker assignment UI."""
        # Hide segments frame and show speaker assignment panel
        self.segments_frame.pack_forget()
        
        # Destroy old speaker assignment panel if exists
        if self.speaker_assignment_panel:
            self.speaker_assignment_panel.destroy()
        
        # Create new speaker assignment panel
        self.speaker_assignment_panel = SpeakerAssignmentPanel(
            self.assignment_left_frame,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            speakers=speakers,
            segment_counts=segment_counts,
            on_assignment_change=self._on_speaker_assignment_change
        )
        self.speaker_assignment_panel.pack(fill="both", expand=True)
        
        self._update_parse_status()
        
        logger.info(f"Created speaker assignment panel with {len(speakers)} speakers")
    
    def _browse_voice_for_segment(self, segment_id: int) -> None:
        """Open voice browser for a specific segment.
        
        Args:
            segment_id: ID of segment to assign voice to
        """
        logger.debug(f"Opening voice browser for segment: {segment_id}")
        
        def on_voice_select(voice_data: dict) -> None:
            self._on_segment_voice_assigned(segment_id, voice_data)
        
        browser = VoiceBrowserWidget(
            self,
            voice_library=self.voice_library,
            tts_engine=self.tts_engine,
            config=self.config,
            on_select=on_voice_select
        )
        browser.wait_window()
    
    def _on_segment_voice_assigned(self, segment_id: int, voice_data: dict) -> None:
        """Handle voice assignment to a segment.
        
        Args:
            segment_id: ID of segment
            voice_data: Selected voice data dictionary
        """
        # Store the voice data in mapping
        self.voice_mapping[segment_id] = voice_data
        
        # Update the UI if row exists
        if segment_id in self.segment_rows:
            self.segment_rows[segment_id].set_voice(voice_data)
        
        logger.info(f"Assigned voice '{voice_data['name']}' to segment {segment_id}")
        self._update_parse_status()
    
    def _on_speaker_assignment_change(self, speaker: str, voice_data: dict) -> None:
        """Handle speaker-to-voice assignment changes."""
        logger.debug(f"Speaker '{speaker}' assigned to voice '{voice_data['name']}'")
        # The assignment is stored in the speaker_assignment_panel
        # We'll use it during generation
        self._update_parse_status()
    
    def _update_parse_status(self) -> None:
        """Update the Parse Status label based on current transcript and assignment state."""
        # Check if transcript is empty or whitespace
        text = self.transcript_textbox.get("1.0", "end-1c").strip()
        colors = get_theme_colors()
        
        if not text:
            # Empty transcript
            self.assignment_info_label.configure(
                text="Transcript Is Empty",
                text_color=colors["text_secondary"]
            )
            self.generate_button.configure(state="disabled")
            # Disable colored preview button
            if self.colored_preview_button:
                self.colored_preview_button.configure(state="disabled")
            return
        
        # Transcript has content - check mode
        mode = self.mode_var.get()
        
        # Update colored preview button state based on mode
        if self.colored_preview_button:
            if mode in ["manual", "annotated"] and len(self.segments) > 0:
                # Enable preview button for segment/speaker modes with segments
                self.colored_preview_button.configure(state="normal")
            else:
                # Disable for single mode or when no segments
                self.colored_preview_button.configure(state="disabled")
        
        if mode == "single":
            # Single voice mode - always green success message and enable generate
            self.assignment_info_label.configure(
                text="Single Voice Applied To All Text",
                text_color=colors["success_text"]
            )
            self.generate_button.configure(state="normal")
        
        elif mode == "manual":
            # Manual/segment mode - check assignment completion
            total_segments = len(self.segments)
            assigned_segments = len(self.voice_mapping)
            
            if assigned_segments < total_segments:
                # Not all assigned
                self.assignment_info_label.configure(
                    text=f"{total_segments} Segments Detected - Must Assign All Segments Voices",
                    text_color=colors["error_text"]
                )
                self.generate_button.configure(state="disabled")
            else:
                # All assigned
                self.assignment_info_label.configure(
                    text=f"{total_segments} Segments Detected - All Segments Assigned Voices",
                    text_color=colors["success_text"]
                )
                self.generate_button.configure(state="normal")
        
        elif mode == "annotated":
            # Annotated speaker mode
            if not self.speaker_assignment_panel:
                # No speaker panel = no speakers detected
                self.assignment_info_label.configure(
                    text="No Speaker Detected",
                    text_color=colors["error_text"]
                )
                self.generate_button.configure(state="disabled")
            else:
                # Have speaker panel - check completion
                speakers = self.speaker_assignment_panel.speakers
                total_speakers = len(speakers)
                
                if not self.speaker_assignment_panel.is_complete():
                    # Not all speakers assigned
                    self.assignment_info_label.configure(
                        text=f"{total_speakers} Speakers Detected - Must Assign All Speakers Voices",
                        text_color=colors["error_text"]
                    )
                    self.generate_button.configure(state="disabled")
                else:
                    # All speakers assigned
                    self.assignment_info_label.configure(
                        text=f"{total_speakers} Speakers Detected - All Speakers Assigned Voices",
                        text_color=colors["success_text"]
                    )
                    self.generate_button.configure(state="normal")
    
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
            logger.debug("Applying voice mappings for segment assignment mode")
            # Update segments with voice mapping
            for segment in self.segments:
                if segment.segment_id in self.voice_mapping:
                    voice_data = self.voice_mapping[segment.segment_id]
                    segment.voice = voice_data['name']
                elif not segment.voice:
                    # Use selected voice as default if available
                    if self.selected_voice_data:
                        segment.voice = self.selected_voice_data['name']
                    else:
                        logger.error("No default voice available for unassigned segments")
                        messagebox.showerror("Error", "Some segments don't have voices assigned and no default voice is selected.")
                        return
        
        elif mode == "annotated":
            logger.debug("Applying speaker-to-voice assignments for annotated mode")
            # Check if all speakers have voice assignments
            if not self.speaker_assignment_panel or not self.speaker_assignment_panel.is_complete():
                logger.error("Not all speakers have voice assignments")
                messagebox.showerror(
                    "Missing Assignments",
                    "Please assign voices to all detected speakers before generating."
                )
                return
            
            # Get speaker assignments
            speaker_assignments = self.speaker_assignment_panel.get_assignments()
            
            # Map segments to voices based on speaker assignments
            for segment in self.segments:
                speaker = segment.voice  # In annotated mode, voice field contains speaker name
                if speaker in speaker_assignments:
                    voice_data = speaker_assignments[speaker]
                    segment.voice = voice_data['name']
                else:
                    logger.error(f"No voice assignment found for speaker: {speaker}")
                    messagebox.showerror(
                        "Assignment Error",
                        f"Speaker '{speaker}' does not have a voice assigned."
                    )
                    return
        
        # Validate voices
        available_voices = []
        
        lib_voices = self.voice_library.get_all_voices()
        for voice in lib_voices:
            available_voices.append(voice['name'])
        
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
        self.cancel_button.configure(state="normal")
        
        self.generated_segments = []
        
        def generate_task(progress_callback):
            """Background generation task."""
            segments_audio = []
            total = len(self.segments)
            logger.info(f"Starting background generation task for {total} segments")
            
            # Get generation parameters from config
            gen_params = self.config.get("generation_params", {})
            logger.debug(f"Using generation params: {gen_params}")
            
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
                
                # Get voice data from library
                voice_data = self.voice_library.get_voice_by_name(voice)
                
                if voice_data:
                    voice_type = voice_data.get("type")
                    
                    if voice_type == "cloned":
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
                                voice_clone_prompt=voice_prompt,
                                **gen_params
                            )
                            logger.debug(f"Cloned voice generation successful")
                            
                            # Track usage
                            self.voice_library.increment_usage(voice_data["id"])
                        except Exception as e:
                            logger.error(f"Failed to use cloned voice: {e}")
                            raise
                    
                    elif voice_type == "designed":
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
                                instruct=voice_data.get("description", ""),
                                **gen_params
                            )
                            logger.debug(f"Designed voice generation successful")
                            
                            # Track usage
                            self.voice_library.increment_usage(voice_data["id"])
                        except Exception as e:
                            logger.error(f"Failed to use designed voice: {e}")
                            raise
                    else:
                        logger.error(f"Unknown voice type: {voice_type}")
                        continue
                else:
                    logger.error(f"Voice not found: {voice}")
                    continue
                
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
        # Re-check assignments to determine if generate button should be enabled
        self._update_parse_status()
        self.cancel_button.configure(state="disabled")
        self.worker = None
