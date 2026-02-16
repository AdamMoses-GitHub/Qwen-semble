"""Voice browser widget for advanced voice selection."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable, List, Dict
from pathlib import Path

from core.audio_utils import AudioPlayer, load_audio
from utils.error_handler import logger


class VoiceCard(ctk.CTkFrame):
    """Card widget displaying voice information with selection."""
    
    def __init__(
        self,
        parent,
        voice_data: dict,
        on_select: Callable,
        on_preview: Optional[Callable] = None,
        is_selected: bool = False,
        **kwargs
    ):
        """Initialize voice card.
        
        Args:
            parent: Parent widget
            voice_data: Voice metadata dictionary
            on_select: Callback when voice is selected
            on_preview: Optional callback to preview voice
            is_selected: Whether this voice is currently selected
        """
        super().__init__(parent, **kwargs)
        
        self.voice_data = voice_data
        self.on_select = on_select
        self.on_preview = on_preview
        self.is_selected = is_selected
        
        self._create_ui()
        self._update_selection_state()
    
    def _create_ui(self) -> None:
        """Create card UI."""
        self.configure(fg_color=("gray90", "gray20"), corner_radius=8)
        
        # Main content frame
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header with name and type badge
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Voice name
        name_label = ctk.CTkLabel(
            header_frame,
            text=self.voice_data.get("name", "Unknown"),
            font=("Arial", 13, "bold"),
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)
        
        # Type badge
        voice_type = self.voice_data.get("type", "preset")
        type_colors = {
            "cloned": ("#2563eb", "#60a5fa"),
            "designed": ("#c026d3", "#e879f9"),
            "preset": ("#16a34a", "#4ade80")
        }
        type_color = type_colors.get(voice_type, type_colors["preset"])
        
        type_badge = ctk.CTkLabel(
            header_frame,
            text=voice_type.capitalize(),
            font=("Arial", 9, "bold"),
            text_color="white",
            fg_color=type_color,
            corner_radius=4,
            padx=8,
            pady=2
        )
        type_badge.pack(side="right", padx=5)
        
        # Metadata row
        meta_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        meta_frame.pack(fill="x", pady=(0, 5))
        
        # Language
        if self.voice_data.get("language"):
            lang_label = ctk.CTkLabel(
                meta_frame,
                text=f"🌐 {self.voice_data['language']}",
                font=("Arial", 9),
                text_color="gray",
                anchor="w"
            )
            lang_label.pack(side="left", padx=(0, 10))
        
        # Usage count
        usage = self.voice_data.get("usage_count", 0)
        if usage > 0:
            usage_label = ctk.CTkLabel(
                meta_frame,
                text=f"📊 Used {usage}x",
                font=("Arial", 9),
                text_color="gray",
                anchor="w"
            )
            usage_label.pack(side="left", padx=(0, 10))
        
        # Created date
        if self.voice_data.get("created"):
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(self.voice_data["created"])
                date_str = dt.strftime("%b %d, %Y")
                date_label = ctk.CTkLabel(
                    meta_frame,
                    text=f"📅 {date_str}",
                    font=("Arial", 9),
                    text_color="gray",
                    anchor="w"
                )
                date_label.pack(side="left")
            except:
                pass
        
        # Tags (if present and not too many)
        tags = self.voice_data.get("tags", [])
        if tags:
            tags_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            tags_frame.pack(fill="x", pady=(0, 5))
            
            tags_label = ctk.CTkLabel(
                tags_frame,
                text="🏷️ " + ", ".join(tags[:3]) + ("..." if len(tags) > 3 else ""),
                font=("Arial", 9),
                text_color="gray",
                anchor="w"
            )
            tags_label.pack(side="left")
        
        # Action buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(5, 0))
        
        # Preview button
        if self.on_preview:
            preview_btn = ctk.CTkButton(
                button_frame,
                text="▶ Preview",
                command=self._on_preview_click,
                width=80,
                height=28,
                font=("Arial", 10)
            )
            preview_btn.pack(side="left", padx=(0, 5))
        
        # Select button
        self.select_btn = ctk.CTkButton(
            button_frame,
            text="✓ Select" if self.is_selected else "Select",
            command=self._on_select_click,
            width=80,
            height=28,
            font=("Arial", 10),
            fg_color="green" if self.is_selected else None
        )
        self.select_btn.pack(side="right")
    
    def _on_select_click(self) -> None:
        """Handle select button click."""
        if self.on_select:
            self.on_select(self.voice_data)
    
    def _on_preview_click(self) -> None:
        """Handle preview button click."""
        if self.on_preview:
            self.on_preview(self.voice_data)
    
    def _update_selection_state(self) -> None:
        """Update visual state based on selection."""
        if self.is_selected:
            self.configure(border_width=2, border_color="green")
        else:
            self.configure(border_width=0)
    
    def set_selected(self, selected: bool) -> None:
        """Update selection state.
        
        Args:
            selected: Whether voice is selected
        """
        self.is_selected = selected
        self._update_selection_state()
        if hasattr(self, 'select_btn'):
            self.select_btn.configure(
                text="✓ Selected" if selected else "Select",
                fg_color="green" if selected else None
            )


class VoiceBrowserWidget(ctk.CTkToplevel):
    """Advanced voice browser with search, filter, and preview."""
    
    def __init__(
        self,
        parent,
        voice_library,
        tts_engine,
        config,
        on_select: Callable[[dict], None],
        current_selection: Optional[str] = None,
        title: str = "Select Voice"
    ):
        """Initialize voice browser.
        
        Args:
            parent: Parent widget
            voice_library: Voice library instance
            tts_engine: TTS engine instance
            config: Config instance
            on_select: Callback when voice is selected (receives voice data dictionary)
            current_selection: Currently selected voice name
            title: Window title
        """
        super().__init__(parent)
        
        self.voice_library = voice_library
        self.tts_engine = tts_engine
        self.config = config
        self.on_select_callback = on_select
        self.current_selection = current_selection
        
        self.selected_voice = current_selection
        self.selected_voice_data = None  # Store full voice data
        self.filter_type = "all"  # all, preset, cloned, designed
        self.search_query = ""
        self.voice_cards = {}  # voice_name -> VoiceCard widget
        self.voice_data_map = {}  # voice_name -> voice_data dict
        
        # Audio player for previews
        self.audio_player = AudioPlayer()
        
        # Configure window
        self.title(title)
        self.geometry("800x600")
        self.resizable(True, True)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        self._populate_voices()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self) -> None:
        """Create browser UI."""
        # Header with search and filters
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Voice Library",
            font=("Arial", 16, "bold")
        )
        title_label.pack(anchor="w", pady=(0, 10))
        
        # Search bar
        search_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 10))
        
        search_label = ctk.CTkLabel(search_frame, text="🔍 Search:")
        search_label.pack(side="left", padx=(0, 5))
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by name or tags...",
            width=300
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_changed())
        
        clear_btn = ctk.CTkButton(
            search_frame,
            text="Clear",
            command=self._clear_search,
            width=60
        )
        clear_btn.pack(side="left")
        
        # Type filters
        filter_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        filter_frame.pack(fill="x")
        
        filter_label = ctk.CTkLabel(filter_frame, text="Type:")
        filter_label.pack(side="left", padx=(0, 10))
        
        self.filter_buttons = {}
        for filter_type, label in [("all", "All"), ("preset", "Preset"), ("cloned", "Cloned"), ("designed", "Designed")]:
            btn = ctk.CTkButton(
                filter_frame,
                text=label,
                command=lambda ft=filter_type: self._set_filter(ft),
                width=80,
                fg_color="green" if filter_type == "all" else "gray"
            )
            btn.pack(side="left", padx=2)
            self.filter_buttons[filter_type] = btn
        
        # Voice count label
        self.count_label = ctk.CTkLabel(filter_frame, text="", font=("Arial", 10))
        self.count_label.pack(side="right", padx=10)
        
        # Scrollable voice list
        self.voice_list_frame = ctk.CTkScrollableFrame(self)
        self.voice_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.voice_list_frame.columnconfigure(0, weight=1)
        
        # Footer with actions
        footer_frame = ctk.CTkFrame(self)
        footer_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Selected voice display
        self.selection_label = ctk.CTkLabel(
            footer_frame,
            text=f"Selected: {self.current_selection or 'None'}",
            font=("Arial", 11),
            anchor="w"
        )
        self.selection_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            footer_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100
        )
        cancel_btn.pack(side="left", padx=5)
        
        # Confirm button
        self.confirm_btn = ctk.CTkButton(
            footer_frame,
            text="Confirm Selection",
            command=self._on_confirm,
            width=150,
            fg_color="green",
            state="normal" if self.current_selection else "disabled"
        )
        self.confirm_btn.pack(side="left", padx=5)
    
    def _populate_voices(self) -> None:
        """Populate voice list based on filters."""
        # Clear existing cards
        for widget in self.voice_list_frame.winfo_children():
            widget.destroy()
        self.voice_cards.clear()
        
        # Get all voices
        all_voices = []
        
        # Get voices from library (includes presets now)
        if self.filter_type == "all":
            all_voices = self.voice_library.get_all_voices()
        else:
            all_voices = self.voice_library.get_all_voices(self.filter_type)
        
        # Apply search filter
        if self.search_query:
            query_lower = self.search_query.lower()
            all_voices = [
                v for v in all_voices
                if query_lower in v["name"].lower()
                or any(query_lower in tag.lower() for tag in v.get("tags", []))
            ]
        
        # Sort by usage, then name
        all_voices.sort(key=lambda v: (-v.get("usage_count", 0), v["name"]))
        
        # Update count
        self.count_label.configure(text=f"{len(all_voices)} voice{'s' if len(all_voices) != 1 else ''}")
        
        # Create voice cards
        if all_voices:
            for idx, voice in enumerate(all_voices):
                voice_name = voice["name"]
                is_selected = (voice_name == self.selected_voice)
                
                card = VoiceCard(
                    self.voice_list_frame,
                    voice_data=voice,
                    on_select=self._on_voice_selected,
                    on_preview=self._on_voice_preview,
                    is_selected=is_selected
                )
                card.grid(row=idx, column=0, sticky="ew", padx=5, pady=5)
                self.voice_cards[voice_name] = card
        else:
            # No voices found
            no_voices_label = ctk.CTkLabel(
                self.voice_list_frame,
                text="No voices found matching criteria",
                font=("Arial", 12),
                text_color="gray"
            )
            no_voices_label.grid(row=0, column=0, pady=50)
    
    def _on_search_changed(self) -> None:
        """Handle search query change."""
        self.search_query = self.search_entry.get()
        self._populate_voices()
    
    def _clear_search(self) -> None:
        """Clear search."""
        self.search_entry.delete(0, "end")
        self.search_query = ""
        self._populate_voices()
    
    def _set_filter(self, filter_type: str) -> None:
        """Set voice type filter.
        
        Args:
            filter_type: Filter type (all, preset, cloned, designed)
        """
        self.filter_type = filter_type
        
        # Update button colors
        for ft, btn in self.filter_buttons.items():
            btn.configure(fg_color="green" if ft == filter_type else "gray")
        
        self._populate_voices()
    
    def _on_voice_selected(self, voice_data: dict) -> None:
        """Handle voice selection.
        
        Args:
            voice_data: Selected voice data
        """
        # Update selection
        old_selection = self.selected_voice
        self.selected_voice = voice_data["name"]
        self.selected_voice_data = voice_data  # Store full voice data
        
        # Update card states
        if old_selection and old_selection in self.voice_cards:
            self.voice_cards[old_selection].set_selected(False)
        
        if self.selected_voice in self.voice_cards:
            self.voice_cards[self.selected_voice].set_selected(True)
        
        # Update footer
        self.selection_label.configure(text=f"Selected: {self.selected_voice}")
        self.confirm_btn.configure(state="normal")
    
    def _on_voice_preview(self, voice_data: dict) -> None:
        """Preview voice audio.
        
        Args:
            voice_data: Voice data to preview
        """
        try:
            voice_type = voice_data.get("type")
            voice_name = voice_data["name"]
            
            logger.info(f"Previewing voice: {voice_name} (type: {voice_type})")
            
            # Stop any currently playing audio
            self.audio_player.stop()
            
            if voice_type == "preset":
                # Generate quick sample for preset voices
                messagebox.showinfo("Preview", "Preset voice preview not yet implemented.\nSelect to use this voice.")
                return
            
            # For library voices, try to play first template test or sample
            if voice_type in ("cloned", "designed"):
                voice_id = voice_data.get("id")
                template_tests = voice_data.get("template_tests", [])
                
                if template_tests and template_tests[0]:
                    audio_path = template_tests[0]
                    if Path(audio_path).exists():
                        audio_data, sr = load_audio(audio_path)
                        self.audio_player.play(audio_data, sr)
                        logger.info(f"Playing template test: {audio_path}")
                    else:
                        messagebox.showwarning("Preview", "Template audio file not found.")
                        logger.warning(f"Template test file not found: {audio_path}")
                else:
                    messagebox.showinfo("Preview", "No preview audio available for this voice.")
                    logger.info(f"No template tests available for voice: {voice_name}")
            
        except Exception as e:
            logger.error(f"Failed to preview voice: {e}")
            messagebox.showerror("Preview Error", f"Failed to preview voice:\n{e}")
    
    def _on_confirm(self) -> None:
        """Confirm selection and close."""
        if self.selected_voice_data:
            if self.on_select_callback:
                self.on_select_callback(self.selected_voice_data)
            self.destroy()
    
    def _on_cancel(self) -> None:
        """Cancel selection and close."""
        self.destroy()
