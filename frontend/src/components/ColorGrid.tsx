import React, { useState, useEffect } from 'react';
import { FaCheck, FaPalette } from 'react-icons/fa';

interface ColorOption {
  base: string;
  variations: string[];
}

interface ThemePreset {
  name: string;
  text: string;
  chart: string;
  background: string;
}

interface ColorGridProps {
  onThemeChange: (theme: any) => void;
  currentTheme: any;
}

const ColorGrid: React.FC<ColorGridProps> = ({ onThemeChange, currentTheme }) => {
  const [selectedText, setSelectedText] = useState(currentTheme?.colors?.text || '#333333');
  const [selectedChart, setSelectedChart] = useState(currentTheme?.colors?.chart || '#1f77b4');
  const [selectedBackground, setSelectedBackground] = useState(currentTheme?.colors?.background || '#ffffff');

  // Reset state when currentTheme changes to ensure color grid is updated
  useEffect(() => {
    if (currentTheme && currentTheme.colors) {
      setSelectedText(currentTheme.colors.text || '#333333');
      setSelectedChart(currentTheme.colors.chart || '#1f77b4');
      setSelectedBackground(currentTheme.colors.background || '#ffffff');
    }
  }, [currentTheme]);

  const colorGrid: ColorOption[] = [
    {
      base: '#1f77b4',
      variations: ['#1f77b4', '#6baed6', '#084d7a']
    },
    {
      base: '#ff7f0e',
      variations: ['#ff7f0e', '#ffbb78', '#b8550c']
    },
    {
      base: '#2ca02c',
      variations: ['#2ca02c', '#98df8a', '#1e6b1e']
    },
    {
      base: '#d62728',
      variations: ['#d62728', '#ff9896', '#a31621']
    },
    {
      base: '#9467bd',
      variations: ['#9467bd', '#c5b0d5', '#6b4c93']
    },
    {
      base: '#8c564b',
      variations: ['#8c564b', '#c49c94', '#6b3d33']
    },
    {
      base: '#e377c2',
      variations: ['#e377c2', '#f7b6d2', '#c556a0']
    },
    {
      base: '#7f7f7f',
      variations: ['#7f7f7f', '#c7c7c7', '#575757']
    },
    {
      base: '#bcbd22',
      variations: ['#bcbd22', '#dbdb8d', '#969818']
    },
    {
      base: '#17becf',
      variations: ['#17becf', '#9edae5', '#1295a3']
    }
  ];

  const presets: ThemePreset[] = [
    {
      name: 'Default Blue',
      text: '#333333',
      chart: '#1f77b4',
      background: '#ffffff'
    },
    {
      name: 'Dark Mode',
      text: '#ffffff',
      chart: '#60a5fa',
      background: '#1f2937'
    },
    {
      name: 'High Contrast',
      text: '#000000',
      chart: '#0066cc',
      background: '#ffffff'
    },
    {
      name: 'Warm Theme',
      text: '#2d3748',
      chart: '#e53e3e',
      background: '#fffaf0'
    },
    {
      name: 'Cool Theme',
      text: '#2d3748',
      chart: '#38b2ac',
      background: '#f7fafc'
    }
  ];

  // Update parent component when selections change
  // Do NOT auto-apply the theme on every color click.
  // Let the user pick multiple colors, then click Apply to send the theme to the parent.

  const buildTheme = () => ({
    colors: {
      text: selectedText,
      chart: selectedChart,
      background: selectedBackground,
      primary: selectedChart,
    }
  });

  const handleApply = () => {
    onThemeChange(buildTheme());
  };

  const handleReset = () => {
    // Reset to values from currentTheme prop
    if (currentTheme && currentTheme.colors) {
      setSelectedText(currentTheme.colors.text || '#333333');
      setSelectedChart(currentTheme.colors.chart || '#1f77b4');
      setSelectedBackground(currentTheme.colors.background || '#ffffff');
    } else {
      setSelectedText('#333333');
      setSelectedChart('#1f77b4');
      setSelectedBackground('#ffffff');
    }
  };

  const [linkColors, setLinkColors] = useState(false);

  const handlePresetSelect = (preset: ThemePreset) => {
    setSelectedText(preset.text);
    setSelectedChart(preset.chart);
    setSelectedBackground(preset.background);
  };

  const calculateContrast = (color1: string, color2: string): number => {
    // Simple contrast calculation - in production, use a proper library
    const getLuminance = (hex: string): number => {
      const rgb = parseInt(hex.slice(1), 16);
      const r = (rgb >> 16) & 0xff;
      const g = (rgb >>  8) & 0xff;
      const b = (rgb >>  0) & 0xff;
      return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    };

    const lum1 = getLuminance(color1);
    const lum2 = getLuminance(color2);
    const brightest = Math.max(lum1, lum2);
    const darkest = Math.min(lum1, lum2);

    return (brightest + 0.05) / (darkest + 0.05);
  };

  const getContrastLevel = (contrast: number): string => {
    if (contrast >= 7) return 'AAA';
    if (contrast >= 4.5) return 'AA';
    if (contrast >= 3) return 'AA Large';
    return 'Fail';
  };

  const textContrast = calculateContrast(selectedText, selectedBackground);
  const chartContrast = calculateContrast(selectedChart, selectedBackground);

  return (
    <div className="space-y-6">
      {/* Current Theme Preview */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Theme Preview</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="w-16 h-16 rounded-lg mx-auto mb-2" style={{ backgroundColor: selectedText }}></div>
            <p className="text-sm text-gray-600">Text Color</p>
            <p className="text-xs text-gray-500">{selectedText}</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 rounded-lg mx-auto mb-2" style={{ backgroundColor: selectedChart }}></div>
            <p className="text-sm text-gray-600">Chart Color</p>
            <p className="text-xs text-gray-500">{selectedChart}</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 rounded-lg mx-auto mb-2" style={{ backgroundColor: selectedBackground }}></div>
            <p className="text-sm text-gray-600">Background</p>
            <p className="text-xs text-gray-500">{selectedBackground}</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium">Text Contrast: </span>
            <span className={`font-medium ${
              textContrast >= 4.5 ? 'text-green-600' : 'text-red-600'
            }`}>
              {textContrast.toFixed(2)} ({getContrastLevel(textContrast)})
            </span>
          </div>
          <div>
            <span className="font-medium">Chart Contrast: </span>
            <span className={`font-medium ${
              chartContrast >= 3 ? 'text-green-600' : 'text-red-600'
            }`}>
              {chartContrast.toFixed(2)} ({getContrastLevel(chartContrast)})
            </span>
          </div>
        </div>
      </div>

      {/* Presets */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Theme Presets</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {presets.map((preset) => (
            <button
              key={preset.name}
              onClick={() => handlePresetSelect(preset)}
              className={`p-3 rounded-lg border-2 transition-all hover:shadow-md ${
                selectedText === preset.text && selectedChart === preset.chart && selectedBackground === preset.background
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm">{preset.name}</span>
                {selectedText === preset.text && selectedChart === preset.chart && selectedBackground === preset.background && (
                  <FaCheck className="h-4 w-4 text-blue-600" />
                )}
              </div>
              <div className="flex space-x-2">
                <div
                  className="w-6 h-6 rounded border"
                  style={{ backgroundColor: preset.text }}
                  title="Text"
                ></div>
                <div
                  className="w-6 h-6 rounded border"
                  style={{ backgroundColor: preset.chart }}
                  title="Chart"
                ></div>
                <div
                  className="w-6 h-6 rounded border"
                  style={{ backgroundColor: preset.background }}
                  title="Background"
                ></div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Color Grid */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Custom Colors</h3>

        {/* Text Color Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Text Color
          </label>
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
            {colorGrid.map((colorOption) => (
              colorOption.variations.map((color) => (
                <button
                  key={`text-${color}`}
                  onClick={() => {
                    setSelectedText(color);
                    if (linkColors) {
                      setSelectedChart(color);
                      setSelectedBackground(color);
                    }
                  }}
                  className={`w-8 h-8 rounded border-2 transition-all hover:scale-110 ${
                    selectedText === color
                      ? 'border-blue-500 shadow-lg'
                      : 'border-gray-300'
                  }`}
                  style={{ backgroundColor: color }}
                  title={color}
                >
                  {selectedText === color && (
                    <FaCheck className="h-3 w-3 text-white drop-shadow-sm" />
                  )}
                </button>
              ))
            ))}
          </div>
        </div>

        {/* Chart Color Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Chart Color
          </label>
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
            {colorGrid.map((colorOption) => (
              colorOption.variations.map((color) => (
                <button
                  key={`chart-${color}`}
                  onClick={() => {
                    setSelectedChart(color);
                    if (linkColors) {
                      setSelectedText(color);
                      setSelectedBackground(color);
                    }
                  }}
                  className={`w-8 h-8 rounded border-2 transition-all hover:scale-110 ${
                    selectedChart === color
                      ? 'border-blue-500 shadow-lg'
                      : 'border-gray-300'
                  }`}
                  style={{ backgroundColor: color }}
                  title={color}
                >
                  {selectedChart === color && (
                    <FaCheck className="h-3 w-3 text-white drop-shadow-sm" />
                  )}
                </button>
              ))
            ))}
          </div>
        </div>

        {/* Background Color Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Background Color
          </label>
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
            {[
              '#ffffff', '#f8f9fa', '#e9ecef', '#dee2e6', '#ced4da',
              '#adb5bd', '#6c757d', '#495057', '#343a40', '#212529',
              '#fffaf0', '#f7fafc', '#edf2f7', '#e2e8f0', '#cbd5e0',
              '#a0aec0', '#718096', '#4a5568', '#2d3748', '#1a202c'
            ].map((color) => (
              <button
                key={`bg-${color}`}
                onClick={() => {
                  setSelectedBackground(color);
                  if (linkColors) {
                    setSelectedText(color);
                    setSelectedChart(color);
                  }
                }}
                className={`w-8 h-8 rounded border-2 transition-all hover:scale-110 ${
                  selectedBackground === color
                    ? 'border-blue-500 shadow-lg'
                    : 'border-gray-300'
                }`}
                style={{ backgroundColor: color }}
                title={color}
              >
                {selectedBackground === color && (
                  <FaCheck className="h-3 w-3 text-white drop-shadow-sm" />
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Link / Actions */}
      <div className="flex items-center justify-between mt-4">
        <div className="flex items-center space-x-3">
          <label className="flex items-center text-sm">
            <input type="checkbox" className="mr-2" checked={linkColors} onChange={() => setLinkColors(!linkColors)} />
            Link colors (apply same color to text/chart/background)
          </label>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleReset}
            className="px-3 py-1 border rounded bg-white hover:shadow-sm text-sm"
            type="button"
          >
            Reset
          </button>
          <button
            onClick={() => {
              // Cancel: restore from currentTheme prop without applying
              handleReset();
            }}
            className="px-3 py-1 border rounded bg-gray-100 hover:shadow-sm text-sm"
            type="button"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm"
            type="button"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Accessibility Note */}
      <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
        <div className="flex">
          <FaPalette className="h-5 w-5 text-blue-400" />
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              <strong>Accessibility:</strong> Text should have at least 4.5:1 contrast ratio with background.
              Charts should have at least 3:1 contrast for large elements.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColorGrid;
