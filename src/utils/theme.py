"""Centralized theme and color management for the application."""


def get_theme_colors() -> dict:
    """Get theme-appropriate colors based on appearance mode.
    
    CustomTkinter automatically handles appearance mode switching.
    Colors are specified as tuples: (light_mode_color, dark_mode_color)
    
    Returns:
        Dictionary of color names to theme-aware color tuples
    """
    return {
        # Background colors
        "header_bg": ("gray85", "gray20"),
        "row_even": ("gray95", "gray17"),
        "row_odd": ("white", "gray14"),
        "row_selected": ("gray80", "gray25"),
        "panel_bg": ("gray90", "gray18"),
        
        # Text colors - PRIMARY/SECONDARY avoid hard-coded white/gray
        "text_primary": ("gray10", "gray90"),      # Main text (dark in light, light in dark)
        "text_secondary": ("gray40", "gray60"),    # Secondary/muted text
        "text_disabled": ("gray60", "gray40"),     # Disabled text
        
        # Status colors - SUCCESS/ERROR/WARNING
        "success_text": ("#047857", "#10b981"),    # Green: success messages
        "success_bg": ("#d1fae5", "#065f46"),      # Green backgrounds
        "error_text": ("#dc2626", "#ef4444"),      # Red: error messages
        "error_bg": ("#fee2e2", "#7f1d1d"),        # Red backgrounds
        "warning_text": ("#ea580c", "#fb923c"),    # Orange: warning messages
        "warning_bg": ("#ffedd5", "#7c2d12"),      # Orange backgrounds
        "info_text": ("#2563eb", "#60a5fa"),       # Blue: info messages
        "info_bg": ("#dbeafe", "#1e3a8a"),         # Blue backgrounds
        
        # Semantic colors for labels and badges
        "badge_text": ("white", "white"),          # Text on colored badges (white works on all dark badge backgrounds)
        "type_cloned": ("#2563eb", "#60a5fa"),     # Blue for cloned voices
        "type_designed": ("#c026d3", "#e879f9"),   # Purple/magenta for designed voices
        "type_preset": ("#059669", "#34d399"),     # Green for preset voices
        
        # UI element colors
        "button_success": ("#16a34a", "#22c55e"),  # Green buttons
        "button_error": ("#dc2626", "#ef4444"),    # Red buttons (delete, etc.)
        "button_info": ("#2563eb", "#3b82f6"),     # Blue buttons
        "button_inactive": ("gray70", "gray30"),   # Inactive/disabled buttons
        
        # Dividers and borders
        "divider": ("gray70", "gray40"),
        "border": ("gray60", "gray50"),
    }
