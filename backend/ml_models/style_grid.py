import colorsys
import logging

logger = logging.getLogger(__name__)


class ColorTheme:
    """Manages color themes and contrast adjustments for dashboards."""

    def __init__(self, primary_color="#1f77b4", text_color="#333333", background_color="#ffffff"):
        self.primary_color = primary_color
        self.text_color = text_color
        self.background_color = background_color

        # Generate color palette
        self.palette = self._generate_color_palette()

    def _generate_color_palette(self):
        """Generate a harmonious color palette from primary color."""
        try:
            # Convert hex to RGB
            r, g, b = self._hex_to_rgb(self.primary_color)

            # Generate variations
            palette = {
                'primary': self.primary_color,
                'primary_light': self._lighten_color(r, g, b, 0.3),
                'primary_dark': self._darken_color(r, g, b, 0.3),
                'secondary': self._generate_secondary_color(r, g, b),
                'accent': self._generate_accent_color(r, g, b),
                'text': self.text_color,
                'text_light': self._lighten_color_text(self.text_color, 0.2),
                'text_dark': self._darken_color_text(self.text_color, 0.2),
                'background': self.background_color,
                'background_light': self._lighten_color_bg(self.background_color, 0.1),
                'background_dark': self._darken_color_bg(self.background_color, 0.1),
                'border': self._generate_border_color(),
                'success': '#28a745',
                'warning': '#ffc107',
                'danger': '#dc3545',
                'info': '#17a2b8'
            }

            return palette

        except Exception as e:
            logger.error(f"Error generating color palette: {str(e)}")
            return self._get_default_palette()

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, r, g, b):
        """Convert RGB tuple to hex color."""
        return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))

    def _lighten_color(self, r, g, b, factor=0.1):
        """Lighten a color by a factor."""
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        new_l = min(1.0, l + factor)
        new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)
        return self._rgb_to_hex(new_r*255, new_g*255, new_b*255)

    def _darken_color(self, r, g, b, factor=0.1):
        """Darken a color by a factor."""
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        new_l = max(0.0, l - factor)
        new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)
        return self._rgb_to_hex(new_r*255, new_g*255, new_b*255)

    def _lighten_color_text(self, hex_color, factor=0.1):
        """Lighten text color appropriately."""
        r, g, b = self._hex_to_rgb(hex_color)
        # For text, we want to be more conservative with lightening
        return self._lighten_color(r, g, b, factor * 0.5)

    def _darken_color_text(self, hex_color, factor=0.1):
        """Darken text color appropriately."""
        r, g, b = self._hex_to_rgb(hex_color)
        # For text, we want to be more conservative with darkening
        return self._darken_color(r, g, b, factor * 0.5)

    def _lighten_color_bg(self, hex_color, factor=0.1):
        """Lighten background color appropriately."""
        r, g, b = self._hex_to_rgb(hex_color)
        return self._lighten_color(r, g, b, factor)

    def _darken_color_bg(self, hex_color, factor=0.1):
        """Darken background color appropriately."""
        r, g, b = self._hex_to_rgb(hex_color)
        return self._darken_color(r, g, b, factor)

    def _generate_secondary_color(self, r, g, b):
        """Generate a secondary color from primary."""
        # Use complementary color theory
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        # Shift hue by 180 degrees for complementary
        new_h = (h + 0.5) % 1.0
        new_r, new_g, new_b = colorsys.hls_to_rgb(new_h, l, s)
        return self._rgb_to_hex(new_r*255, new_g*255, new_b*255)

    def _generate_accent_color(self, r, g, b):
        """Generate an accent color."""
        # Create a triadic color (120 degrees apart)
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        new_h = (h + 1/3) % 1.0
        new_r, new_g, new_b = colorsys.hls_to_rgb(new_h, l, s)
        return self._rgb_to_hex(new_r*255, new_g*255, new_b*255)

    def _generate_border_color(self):
        """Generate border color based on background."""
        r, g, b = self._hex_to_rgb(self.background_color)
        # Create a slightly darker version for borders
        return self._darken_color(r, g, b, 0.1)

    def _get_default_palette(self):
        """Return default color palette."""
        return {
            'primary': '#1f77b4',
            'primary_light': '#6baed6',
            'primary_dark': '#084d7a',
            'secondary': '#ff7f0e',
            'accent': '#2ca02c',
            'text': '#333333',
            'text_light': '#666666',
            'text_dark': '#000000',
            'background': '#ffffff',
            'background_light': '#f8f9fa',
            'background_dark': '#e9ecef',
            'border': '#dee2e6',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8'
        }

    def ensure_contrast(self):
        """Ensure sufficient contrast between text and background."""
        try:
            # Calculate luminance
            bg_luminance = self._calculate_luminance(self.background_color)
            text_luminance = self._calculate_luminance(self.text_color)

            # Calculate contrast ratio
            contrast_ratio = self._calculate_contrast_ratio(bg_luminance, text_luminance)

            # WCAG AA requires 4.5:1 for normal text, 3:1 for large text
            min_contrast = 4.5

            if contrast_ratio < min_contrast:
                # Adjust text color for better contrast
                if bg_luminance > 0.5:
                    # Light background: use darker text
                    self.text_color = self._get_dark_text_for_light_bg()
                else:
                    # Dark background: use lighter text
                    self.text_color = self._get_light_text_for_dark_bg()

                # Regenerate palette
                self.palette = self._generate_color_palette()

        except Exception as e:
            logger.error(f"Error ensuring contrast: {str(e)}")

    def _calculate_luminance(self, hex_color):
        """Calculate relative luminance of a color."""
        r, g, b = self._hex_to_rgb(hex_color)
        r, g, b = r/255.0, g/255.0, b/255.0

        # Apply gamma correction
        def gamma_correct(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)

        # Calculate luminance
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _calculate_contrast_ratio(self, lum1, lum2):
        """Calculate contrast ratio between two luminances."""
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        return (lighter + 0.05) / (darker + 0.05)

    def _get_dark_text_for_light_bg(self):
        """Get dark text color for light background."""
        return '#000000'

    def _get_light_text_for_dark_bg(self):
        """Get light text color for dark background."""
        return '#ffffff'

    def get_plotly_theme(self):
        """Get Plotly theme configuration."""
        return {
            'template': 'plotly_white',
            'layout': {
                'plot_bgcolor': self.palette['background'],
                'paper_bgcolor': self.palette['background'],
                'font': {'color': self.palette['text']},
                'title': {'font': {'color': self.palette['text']}},
                'xaxis': {
                    'title': {'font': {'color': self.palette['text']}},
                    'tickfont': {'color': self.palette['text']}
                },
                'yaxis': {
                    'title': {'font': {'color': self.palette['text']}},
                    'tickfont': {'color': self.palette['text']}
                }
            }
        }

    def to_dict(self):
        """Convert theme to dictionary."""
        return {
            'colors': self.palette,
            'primary_color': self.primary_color,
            'text_color': self.text_color,
            'background_color': self.background_color
        }


def generate_color_grid():
    """Generate a color grid for user selection."""
    # Base colors for the grid
    base_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
    ]

    # Generate variations (lighter and darker)
    color_grid = []

    for color in base_colors:
        variations = [color]

        # Add lighter variation
        r, g, b = _hex_to_rgb_static(color)
        lighter = _lighten_color_static(r, g, b, 0.3)
        variations.append(lighter)

        # Add darker variation
        darker = _darken_color_static(r, g, b, 0.3)
        variations.append(darker)

        color_grid.append({
            'base': color,
            'variations': variations
        })

    return color_grid


def _hex_to_rgb_static(hex_color):
    """Static version of hex to RGB conversion."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex_static(r, g, b):
    """Static version of RGB to hex conversion."""
    return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))


def _lighten_color_static(r, g, b, factor=0.1):
    """Static version of lighten color."""
    h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
    new_l = min(1.0, l + factor)
    new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)
    return _rgb_to_hex_static(new_r*255, new_g*255, new_b*255)


def _darken_color_static(r, g, b, factor=0.1):
    """Static version of darken color."""
    h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
    new_l = max(0.0, l - factor)
    new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)
    return _rgb_to_hex_static(new_r*255, new_g*255, new_b*255)


def create_theme_from_selections(text_color, chart_color, background_color):
    """
    Create a complete theme from user color selections.

    Args:
        text_color (str): Selected text color
        chart_color (str): Selected chart color
        background_color (str): Selected background color

    Returns:
        ColorTheme: Complete theme object
    """
    theme = ColorTheme(
        primary_color=chart_color,
        text_color=text_color,
        background_color=background_color
    )

    # Ensure contrast compliance
    theme.ensure_contrast()

    return theme


def get_accessible_color_combinations():
    """Get pre-defined accessible color combinations."""
    combinations = [
        {
            'name': 'Default Blue',
            'text': '#333333',
            'chart': '#1f77b4',
            'background': '#ffffff'
        },
        {
            'name': 'Dark Mode',
            'text': '#ffffff',
            'chart': '#60a5fa',
            'background': '#1f2937'
        },
        {
            'name': 'High Contrast',
            'text': '#000000',
            'chart': '#0066cc',
            'background': '#ffffff'
        },
        {
            'name': 'Warm Theme',
            'text': '#2d3748',
            'chart': '#e53e3e',
            'background': '#fffaf0'
        },
        {
            'name': 'Cool Theme',
            'text': '#2d3748',
            'chart': '#38b2ac',
            'background': '#f7fafc'
        }
    ]

    return combinations
