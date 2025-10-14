import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js';

interface PlotlyChartProps {
  data: any;
  layout?: any;
  config?: any;
  style?: any;
  className?: string;
  theme?: any;
}

const PlotlyChart = ({ data, layout, config = { responsive: true }, style, className = '', theme }: PlotlyChartProps) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<any>(null);

  useEffect(() => {
    const chartElement = chartRef.current;
    
    if (!chartElement) return;

    // Clean up previous plot
    if (plotRef.current) {
      try {
        Plotly.purge(chartElement);
      } catch (e) {
        console.warn('Error purging plot:', e);
      }
    }

    if (!data || (Array.isArray(data) && data.length === 0)) {
      console.warn('No data provided to PlotlyChart');
      return;
    }

    // Ensure data is an array
    const chartData = Array.isArray(data) ? data : [data];

    // Apply theme colors to layout
    const defaultLayout = {
      margin: { t: 30, b: 30, l: 40, r: 10 },
      autosize: true,
      showlegend: true,
      ...(layout || {})
    };

    let themedLayout = {
      ...defaultLayout,
      plot_bgcolor: theme?.colors?.background || '#ffffff',
      paper_bgcolor: theme?.colors?.background || '#ffffff',
      font: {
        color: theme?.colors?.text || '#333333',
        ...(defaultLayout?.font || {})
      }
    };

    // Apply theme to axes if they exist
    if (themedLayout.xaxis) {
      themedLayout.xaxis = {
        ...themedLayout.xaxis,
        title: {
          ...(themedLayout.xaxis.title || {}),
          font: {
            ...(themedLayout.xaxis.title?.font || {}),
            color: theme?.colors?.text || '#333333'
          }
        },
        tickfont: {
          ...(themedLayout.xaxis.tickfont || {}),
          color: theme?.colors?.text || '#333333'
        }
      };
    }

    if (themedLayout.yaxis) {
      themedLayout.yaxis = {
        ...themedLayout.yaxis,
        title: {
          ...(themedLayout.yaxis.title || {}),
          font: {
            ...(themedLayout.yaxis.title?.font || {}),
            color: theme?.colors?.text || '#333333'
          }
        },
        tickfont: {
          ...(themedLayout.yaxis.tickfont || {}),
          color: theme?.colors?.text || '#333333'
        }
      };
    }

    // Log data for debugging
    console.log('Rendering Plotly chart with data:', chartData);
    console.log('Layout:', themedLayout);

    // Validate and filter traces to avoid rendering empty/broken charts
    const validateTrace = (trace: any) => {
      if (!trace || typeof trace !== 'object') return false;
      const type = trace.type;
      // Heatmap must have non-empty z and x/y
      if (type === 'heatmap') {
        return Array.isArray(trace.z) && trace.z.length > 0 && Array.isArray(trace.x) && trace.x.length > 0 && Array.isArray(trace.y) && trace.y.length > 0;
      }
      if (type === 'histogram') {
        return Array.isArray(trace.x) && trace.x.length > 0;
      }
      if (type === 'scatter' || type === 'bar') {
        const hasX = Array.isArray(trace.x) && trace.x.length > 0;
        const hasY = Array.isArray(trace.y) && trace.y.length > 0;
        // If both present, lengths should match
        if (hasX && hasY) return trace.x.length === trace.y.length;
        return hasX || hasY;
      }
      if (type === 'pie') {
        return Array.isArray(trace.values) && trace.values.length > 0;
      }
      // Generic fallback: keep if any of x/y/z present and non-empty
      return (Array.isArray(trace.x) && trace.x.length > 0) || (Array.isArray(trace.y) && trace.y.length > 0) || (Array.isArray(trace.z) && trace.z.length > 0);
    };

    const filteredData = chartData.filter((t: any) => {
      const ok = validateTrace(t);
      if (!ok) {
        console.warn('Dropping invalid/empty trace before plotting:', t);
      }
      return ok;
    });

    if (!filteredData || filteredData.length === 0) {
      console.warn('No valid traces to render after validation. Showing placeholder.');
      try {
        // Clear any previous plot
        if (chartElement) {
          try { Plotly.purge(chartElement); } catch (e) {}
          // Insert a visible placeholder message so the UI doesn't look broken
          chartElement.innerHTML = '';
          const placeholder = document.createElement('div');
          placeholder.style.display = 'flex';
          placeholder.style.alignItems = 'center';
          placeholder.style.justifyContent = 'center';
          placeholder.style.height = '100%';
          placeholder.style.color = themedLayout?.font?.color || '#666';
          placeholder.style.fontSize = '14px';
          placeholder.innerText = 'No data available for this chart';
          chartElement.appendChild(placeholder);
        }
      } catch (err) {
        console.warn('Error rendering no-data placeholder:', err);
      }
      return;
    }

    // Create new plot
    try {
      Plotly.newPlot(chartElement, filteredData, themedLayout, {
        ...config,
        displaylogo: false,
        responsive: true
      }).then((plot: any) => {
        plotRef.current = plot;
        // Resize plot to fit container
        window.dispatchEvent(new Event('resize'));
      });
    } catch (error) {
      console.error('Error creating Plotly chart:', error);
    }

    // Handle window resize
    const handleResize = () => {
      if (plotRef.current) {
        Plotly.Plots.resize(chartElement);
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup function
    return () => {
      window.removeEventListener('resize', handleResize);
      if (plotRef.current && chartElement) {
        try {
          Plotly.purge(chartElement);
          plotRef.current = null;
        } catch (e) {
          console.warn('Error in cleanup:', e);
        }
      }
    };
  }, [data, layout, config, theme]);

  return (
    <div
      ref={chartRef}
      className={`plotly-chart ${className}`}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '400px',
        ...style
      }}
    />
  );
};

export default PlotlyChart;