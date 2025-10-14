import React, { useState, useEffect, useCallback } from 'react';
import PlotlyChart from './PlotlyChart';
import { FaExpand, FaCompress, FaTrash } from 'react-icons/fa';

interface ChartComponentProps {
  chart: any;
  index: number;
  sectionIndex?: number;
  theme: any;
  chartData: any;
  onDelete?: () => void;
  onResize?: (size: number) => void;
}

const ChartComponent: React.FC<ChartComponentProps> = React.memo(({ 
  chart, 
  index, 
  sectionIndex, 
  theme,
  chartData: initialChartData,
  onDelete,
  onResize
}) => {
  const [chartSize, setChartSize] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [processedChartData, setProcessedChartData] = useState<any>(null);
  
  useEffect(() => {
    // Process chart data when it changes
    if (!initialChartData) {
      setProcessedChartData(null);
      return;
    }
    
    let processedData = initialChartData;
    
    // If backend returned full figure JSON, unwrap the traces
    if (!Array.isArray(processedData)) {
      if (processedData?.data && Array.isArray(processedData.data)) {
        processedData = processedData.data;
      } else {
        processedData = [processedData];
      }
    }
    
    // Remove traces that are clearly invalid/empty
    processedData = processedData.filter((trace: any) => {
      if (!trace) return false;
      // Heatmap must have z and x arrays
      if (trace.type === 'heatmap') {
        return Array.isArray(trace.z) && trace.z.length > 0 && Array.isArray(trace.x) && trace.x.length > 0;
      }
      // Histogram should have x or y
      if (trace.type === 'histogram') {
        return Array.isArray(trace.x) && trace.x.length > 0;
      }
      // Scatter/bar/pie: require at least one of x/y/values
      if (trace.type === 'scatter' || trace.type === 'bar') {
        return (Array.isArray(trace.x) && trace.x.length > 0) || (Array.isArray(trace.y) && trace.y.length > 0);
      }
      if (trace.type === 'pie') {
        return Array.isArray(trace.values) && trace.values.length > 0;
      }
      return true;
    });
    
    setProcessedChartData(processedData);
  }, [initialChartData]);
  
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      const elem = document.getElementById(`chart-${index}-${sectionIndex || '0'}`);
      if (elem?.requestFullscreen) {
        elem.requestFullscreen();
        setIsFullscreen(true);
      }
    } else if (document.exitFullscreen) {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, [index, sectionIndex]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const handleResize = useCallback((newSize: number) => {
    setChartSize(newSize);
    if (onResize) {
      onResize(newSize);
    }
  }, [onResize]);

  if (!processedChartData || processedChartData.length === 0) {
    console.warn(`Chart ${index} has no data:`, chart);
    return (
      <div
        className="chart-container p-4 border border-red-200 rounded-lg"
        style={{
          backgroundColor: theme?.colors?.background || '#ffffff',
          color: theme?.colors?.text || '#333333',
          position: 'relative'
        }}
      >
        <h3 className="text-lg font-medium mb-2 text-red-500">
          {chart?.title || 'Untitled Chart'}
        </h3>
        <p className="text-sm text-gray-500">No data available for this chart</p>
      </div>
    );
  }

  const chartLayout = {
    ...(chart.layout || {}),
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      color: theme?.colors?.text || '#333333',
      ...(chart.layout?.font || {})
    },
    xaxis: {
      ...(chart.layout?.xaxis || {}),
      color: theme?.colors?.text || '#333333',
    },
    yaxis: {
      ...(chart.layout?.yaxis || {}),
      color: theme?.colors?.text || '#333333',
    },
    margin: { t: 40, b: 60, l: 60, r: 40 },
    autosize: true,
  };

  return (
    <div
      id={`chart-${index}-${sectionIndex || '0'}`}
      className={`chart-container bg-white rounded-lg shadow p-4`}
      style={{
        backgroundColor: theme?.colors?.background || '#ffffff',
        color: theme?.colors?.text || '#333333',
        position: 'relative',
        gridColumn: chartSize === 2 ? '1 / -1' : 'auto',
      }}
    >
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-medium" style={{ color: theme?.colors?.text || '#333333' }}>
          {chart?.title || 'Untitled Chart'}
        </h3>
        <div className="flex space-x-2">
          <button
            onClick={() => handleResize(chartSize === 1 ? 2 : 1)}
            className="p-1 rounded hover:bg-gray-200"
            style={{ color: theme?.colors?.text || '#333333' }}
            title={chartSize === 1 ? 'Expand' : 'Shrink'}
          >
            {chartSize === 1 ? <FaExpand /> : <FaCompress />}
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-1 rounded hover:bg-gray-200"
            style={{ color: theme?.colors?.text || '#333333' }}
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <FaCompress /> : <FaExpand />}
          </button>
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 rounded hover:bg-red-100 text-red-500"
              title="Delete Chart"
            >
              <FaTrash />
            </button>
          )}
        </div>
      </div>
      <div className="w-full" style={{ minHeight: '350px' }}>
        <PlotlyChart
          data={processedChartData}
          layout={chartLayout}
          config={{
            ...(chart.config || {}),
            displayModeBar: true,
            responsive: true,
            displaylogo: false
          }}
          theme={theme}
          style={{
            width: '100%',
            height: '100%',
            minHeight: '350px'
          }}
        />
      </div>
    </div>
  );
});

export default ChartComponent;
