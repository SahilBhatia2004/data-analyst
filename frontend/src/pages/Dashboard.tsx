import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { FaCog, FaChartBar, FaTable, FaLightbulb, FaGripVertical, FaExpand, FaCompress } from 'react-icons/fa';
import PlotlyChart from '../components/PlotlyChart';
import ColorGrid from '../components/ColorGrid';
import apiService from '../services/api';
import { FaTrash } from 'react-icons/fa';

interface DashboardData {
  title: string;
  sections: any[];
  narrative: string;
  theme?: any;
}

interface File {
  id: number;
  file_name: string;
  file_type: string;
  is_processed: boolean;
}

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const originalDashboardRef = React.useRef<DashboardData | null>(null);
  const [generating, setGenerating] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [query, setQuery] = useState(`Analyze this dataset and create a comprehensive dashboard with the following sections:

1. Executive Summary (2-3 sentences highlighting key findings)
2. Key Metrics (3-5 important KPIs with trends)
3. Trends & Patterns (time series analysis, seasonality, anomalies)
4. Comparative Analysis (segment comparisons, rankings, correlations)
5. Actionable Insights (3-5 data-driven recommendations)

For each chart or visualization, include:
- Clear, descriptive title
- Brief interpretation of what the data shows
- Any significant patterns or outliers
- Business implications
- Suggested actions based on the data

Use clear, concise language and focus on insights that drive business decisions. Include specific numbers, percentages, and comparisons where relevant.`);
  const [showColorGrid, setShowColorGrid] = useState(false);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [draggedChart, setDraggedChart] = useState<{ sectionIndex: number; chartIndex: number } | null>(null);
  const [isDragEnabled, setIsDragEnabled] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<any>({
    colors: {
      text: '#333333',
      chart: '#1f77b4',
      background: '#ffffff'
    }
  });
  const [dashboardId, setDashboardId] = useState<number | null>(null);
  const [savedDashboards, setSavedDashboards] = useState<any[]>([]);

  // Load saved dashboards when component mounts
  useEffect(() => {
    const loadSavedDashboards = async () => {
      try {
        const response = await apiService.listUserDashboards();
        if (response && response.dashboards) {
          setSavedDashboards(response.dashboards);
          
          // If there are saved dashboards, load the most recent one
          if (response.dashboards.length > 0) {
            const mostRecent = response.dashboards[0];
            try {
              const dashboardResponse = await apiService.loadUserDashboard(mostRecent.file_name);
              if (dashboardResponse && dashboardResponse.dashboard_data) {
                // Process the loaded dashboard data the same way as when generating a new dashboard
                const processedData = {
                  ...dashboardResponse.dashboard_data,
                  sections: (dashboardResponse.dashboard_data.sections || []).map((section: any) => {
                    // Ensure charts have proper data structure
                    if (section.type === 'charts_section' && section.charts) {
                      return {
                        ...section,
                        charts: section.charts.map((chart: any) => ({
                          ...chart,
                          data: chart.data || [],
                          layout: chart.layout || {},
                          config: chart.config || {}
                        }))
                      };
                    }
                    return section;
                  })
                };
                
                setDashboardData(processedData);
                originalDashboardRef.current = JSON.parse(JSON.stringify(processedData));
                if (dashboardResponse.file_id) {
                  setSelectedFileId(dashboardResponse.file_id);
                }
                toast.success('Dashboard loaded successfully');
              }
            } catch (error) {
              console.error('Error loading dashboard:', error);
            }
          }
        }
      } catch (error) {
        console.error('Error listing dashboards:', error);
      }
    };

    loadSavedDashboards();
  }, []);

  const loadFiles = useCallback(async () => {
    try {
      const response = await apiService.getFiles();
      const processedFiles = response.files?.filter((file: File) => file.is_processed) || [];
      setFiles(processedFiles);

      if (processedFiles.length > 0 && !selectedFileId) {
        setSelectedFileId(processedFiles[0].id);
      }
    } catch (error) {
      toast.error('Failed to load files');
    }
  }, [selectedFileId]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const generateDashboard = async () => {
    if (!selectedFileId) {
      toast.error('Please select a file first');
      return;
    }

    setGenerating(true);

    try {
      const response = await apiService.generateDashboard(selectedFileId, query, currentTheme);
      
      if (!response || !response.dashboard_data) {
        throw new Error('Invalid response from server');
      }

      // Log the response for debugging
      console.log('Dashboard API Response:', response);

      // Process the dashboard data to ensure it's in the correct format
      const processedData = {
        ...response.dashboard_data,
        sections: (response.dashboard_data.sections || []).map((section: any) => {
          // Ensure charts have proper data structure
          if (section.type === 'charts_section' && section.charts) {
            return {
              ...section,
              charts: section.charts.map((chart: any) => ({
                ...chart,
                data: chart.data || [],
                layout: chart.layout || {},
                config: chart.config || {}
              }))
            };
          }
          return section;
        })
      };

      // Save a copy of the original dashboard so users can restore removed items
      originalDashboardRef.current = JSON.parse(JSON.stringify(processedData));
      setDashboardData(processedData);
      // Save the dashboard ID for later use
      if (response.dashboard_id) {
        setDashboardId(response.dashboard_id);
      }
      toast.success('Dashboard generated successfully!');
    } catch (error: unknown) {
      console.error('Error generating dashboard:', error);
      if (error instanceof Error) {
        toast.error(`Failed to generate dashboard: ${error.message}`);
      } else {
        toast.error('Failed to generate dashboard: An unknown error occurred');
      }
    } finally {
      setGenerating(false);
    }
  };

  const loadSavedDashboard = async (filename: string) => {
    try {
      const response = await apiService.loadUserDashboard(filename);
      if (response && response.dashboard_data) {
        // Process the loaded dashboard data the same way as when generating a new dashboard
        const processedData = {
          ...response.dashboard_data,
          sections: (response.dashboard_data.sections || []).map((section: any) => {
            // Ensure charts have proper data structure
            if (section.type === 'charts_section' && section.charts) {
              return {
                ...section,
                charts: section.charts.map((chart: any) => ({
                  ...chart,
                  data: chart.data || [],
                  layout: chart.layout || {},
                  config: chart.config || {}
                }))
              };
            }
            return section;
          })
        };
        
        setDashboardData(processedData);
        originalDashboardRef.current = JSON.parse(JSON.stringify(processedData));
        if (response.file_id) {
          setSelectedFileId(response.file_id);
        }
        toast.success('Dashboard loaded successfully');
      }
    } catch (error) {
      console.error('Error loading dashboard:', error);
      toast.error('Failed to load dashboard');
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown date';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const restoreDashboard = async () => {
    if (originalDashboardRef.current) {
      setDashboardData(JSON.parse(JSON.stringify(originalDashboardRef.current)));
      toast.info('Dashboard restored');
      
      // Save the restored dashboard to Supabase
      if (dashboardId) {
        try {
          await apiService.saveDashboardToSupabase(dashboardId);
          toast.success('Dashboard saved to cloud storage');
        } catch (error) {
          console.error('Error saving dashboard to Supabase:', error);
          toast.error('Failed to save dashboard to cloud storage');
        }
      }
    } else {
      toast.warn('No original dashboard to restore');
    }
  };

  const saveDashboardToSupabase = async () => {
    if (!dashboardData) {
      toast.warn('No dashboard to save');
      return;
    }

    try {
      // Get the latest dashboard ID from the database
      // This assumes the dashboard was saved when it was generated
      // In a real implementation, you might want to pass the dashboard ID as a prop
      // or store it in state when the dashboard is generated
      const response = await apiService.getFiles();
      if (response && response.files && response.files.length > 0) {
        // For now, we'll just show a message that this feature is being implemented
        toast.info('Dashboard saving feature is being implemented');
        // In a full implementation, you would:
        // 1. Get the current dashboard ID
        // 2. Call apiService.saveDashboardToSupabase(dashboardId)
        // 3. Handle the response
      }
    } catch (error) {
      console.error('Error saving dashboard:', error);
      toast.error('Failed to save dashboard');
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => {
        console.error(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(err => {
          console.error(`Error attempting to exit fullscreen: ${err.message}`);
        });
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const handleDragStart = (e: React.DragEvent, sectionIndex: number, chartIndex: number) => {
    if (!isDragEnabled) return;

    setDraggedChart({ sectionIndex, chartIndex });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', `${sectionIndex}-${chartIndex}`);

    // Add visual feedback
    e.currentTarget.classList.add('opacity-50');
  };

  const handleDragEnd = (e: React.DragEvent) => {
    setDraggedChart(null);
    setDragOverIndex(null);
    e.currentTarget.classList.remove('opacity-50');
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    if (!isDragEnabled) return;

    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (!isDragEnabled) return;

    // Clear the drag over index when mouse leaves the drop target
    setDragOverIndex(null);
  };

  const toggleDragMode = () => {
    setIsDragEnabled(prev => {
      const newState = !prev;
      toast.info(newState ? 'Drag mode enabled' : 'Drag mode disabled');
      return newState;
    });
  };

  const handleDrop = (e: React.DragEvent, targetSectionIndex: number, targetChartIndex: number) => {
    if (!isDragEnabled || !draggedChart) return;

    e.preventDefault();
    setDragOverIndex(null);
    const { sectionIndex: sourceSectionIndex, chartIndex: sourceChartIndex } = draggedChart;

    // Don't allow dropping on the same chart
    if (sourceSectionIndex === targetSectionIndex && sourceChartIndex === targetChartIndex) {
      return;
    }

    setDashboardData(prev => {
      if (!prev) return prev;

      const newSections = [...prev.sections];

      // Find source and target sections
      const sourceSection = newSections[sourceSectionIndex];

      // Only allow reordering within the same section for now
      if (sourceSectionIndex !== targetSectionIndex) {
        toast.warn('Charts can only be reordered within the same section');
        return prev;
      }

      if (sourceSection && sourceSection.type === 'charts_section' && Array.isArray(sourceSection.charts)) {
        const newCharts = [...sourceSection.charts];

        // Remove source chart
        const [movedChart] = newCharts.splice(sourceChartIndex, 1);

        // Insert at target position
        newCharts.splice(targetChartIndex, 0, movedChart);

        // Update the section
        newSections[sourceSectionIndex] = {
          ...sourceSection,
          charts: newCharts
        };

        toast.success('Chart moved successfully');
        return { ...prev, sections: newSections };
      }

      return prev;
    });

    setDraggedChart(null);
  };

  const handleThemeChange = (newTheme: any) => {
    setCurrentTheme(newTheme);
    setShowColorGrid(false);

    // Regenerate dashboard with new theme if we have data
    if (dashboardData && selectedFileId) {
      generateDashboard();
    }
  };

  const renderKpiCard = (card: any) => (
    <div 
      key={card.title} 
      className="kpi-card"
      style={{
        backgroundColor: currentTheme?.colors?.background || '#ffffff',
        color: currentTheme?.colors?.text || '#333333',
        border: `1px solid ${currentTheme?.colors?.chart || '#1f77b4'}`
      }}
    >
      <div 
        className="kpi-value" 
        style={{ color: currentTheme?.colors?.chart || '#1f77b4' }}
      >
        {card.value}
      </div>
      <div className="kpi-title">{card.title}</div>
      {card.description && (
        <div 
          className="text-sm mt-2" 
          style={{ color: currentTheme?.colors?.text || '#333333' }}
        >
          {card.description}
        </div>
      )}
    </div>
  );

  const renderChart = (chart: any, index: number, sectionIndex?: number) => {
    // Normalize chart payloads coming from backend.
    // Some generators return { data: [...traces], layout: {...} }
    // while others return { data: { data: [...], layout: {...} } } (full fig JSON).
    // Normalize to an array of traces and filter out empty/invalid traces (e.g. empty heatmaps).
    let chartData = chart?.data;
    if (!chartData) {
      console.warn(`Chart ${index} has no data:`, chart);
      return (
        <div
          key={`chart-${index}-empty`}
          className="chart-container p-4 border border-red-200 rounded-lg"
          style={{
            backgroundColor: currentTheme?.colors?.background || '#ffffff',
            color: currentTheme?.colors?.text || '#333333'
          }}
        >
          <h3
            className="text-lg font-medium mb-2 text-red-500"
          >
            {chart?.title || 'Untitled Chart'}
          </h3>
          <p className="text-sm text-gray-500">No data available for this chart</p>
        </div>
      );
    }

    // If backend returned full figure JSON, unwrap the traces
    if (!Array.isArray(chartData)) {
      if (chartData.data && Array.isArray(chartData.data)) {
        chartData = chartData.data;
      } else {
        chartData = [chartData];
      }
    }

    // Remove traces that are clearly invalid/empty. This prevents empty heatmaps from rendering.
    chartData = chartData.filter((trace: any) => {
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
      // Fallback: keep if any of x/y/z present with length
      return (Array.isArray(trace.x) && trace.x.length > 0) || (Array.isArray(trace.y) && trace.y.length > 0) || (Array.isArray(trace.z) && trace.z.length > 0);
    });

    if (!chartData || chartData.length === 0) {
      console.warn(`Chart ${index} has no valid traces after normalization:`, chart);
      return (
        <div
          key={`chart-${index}-empty`}
          className="chart-container p-4 border border-red-200 rounded-lg"
          style={{
            backgroundColor: currentTheme?.colors?.background || '#ffffff',
            color: currentTheme?.colors?.text || '#333333'
          }}
        >
          <h3
            className="text-lg font-medium mb-2 text-red-500"
          >
            {chart?.title || 'Untitled Chart'}
          </h3>
          <p className="text-sm text-gray-500">No data available for this chart</p>
        </div>
      );
    }

    // Add theme colors to chart data if not present
    chartData = chartData.map((trace: any) => ({
      ...trace,
      marker: trace.marker || {
        color: currentTheme?.colors?.chart || '#1f77b4',
        ...(trace.marker || {})
      },
      line: trace.line || {
        color: currentTheme?.colors?.chart || '#1f77b4',
        ...(trace.line || {})
      }
    }));

    // Prepare layout with theme
    const chartLayout = {
      ...(chart.layout || {}),
      plot_bgcolor: currentTheme?.colors?.background || '#ffffff',
      paper_bgcolor: currentTheme?.colors?.background || '#ffffff',
      font: {
        color: currentTheme?.colors?.text || '#333333',
        ...(chart.layout?.font || {})
      },
      margin: { t: 40, b: 40, l: 60, r: 20 },
      autosize: true
    };

    // Add theme to axes
    if (chartLayout.xaxis) {
      chartLayout.xaxis = {
        ...chartLayout.xaxis,
        title: {
          ...(chartLayout.xaxis.title || { text: 'X-Axis' }),
          font: {
            ...(chartLayout.xaxis.title?.font || {}),
            color: currentTheme?.colors?.text || '#333333'
          }
        },
        tickfont: {
          ...(chartLayout.xaxis.tickfont || {}),
          color: currentTheme?.colors?.text || '#333333'
        }
      };
    }

    if (chartLayout.yaxis) {
      chartLayout.yaxis = {
        ...chartLayout.yaxis,
        title: {
          ...(chartLayout.yaxis.title || { text: 'Y-Axis' }),
          font: {
            ...(chartLayout.yaxis.title?.font || {}),
            color: currentTheme?.colors?.text || '#333333'
          }
        },
        tickfont: {
          ...(chartLayout.yaxis.tickfont || {}),
          color: currentTheme?.colors?.text || '#333333'
        }
      };
    }

    return (
      <div
        key={`chart-${index}`}
        className={`chart-container bg-white rounded-lg shadow p-4 ${isDragEnabled ? 'cursor-move' : ''} ${dragOverIndex === index ? 'ring-2 ring-blue-500' : ''}`}
        style={{
          backgroundColor: currentTheme?.colors?.background || '#ffffff',
          color: currentTheme?.colors?.text || '#333333',
          minHeight: '400px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative'
        }}
        draggable={isDragEnabled}
        onDragStart={(e) => handleDragStart(e, sectionIndex || 0, index)}
        onDragEnd={handleDragEnd}
        onDragOver={(e) => handleDragOver(e, index)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, sectionIndex || 0, index)}
      >
        {/* Drag Handle */}
        {isDragEnabled && (
          <div
            className="absolute top-2 right-2 z-10 p-1 rounded cursor-move hover:bg-gray-100"
            style={{ color: currentTheme?.colors?.chart || '#1f77b4' }}
            title="Drag to reorder"
          >
            <FaGripVertical className="h-4 w-4" />
          </div>
        )}

        {/* Chart Header */}
        <div className="flex items-center justify-between mb-2 px-2">
          <h3
            className="text-lg font-medium"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            {chart.title || `Chart ${index + 1}`}
          </h3>
          <div className="flex items-center gap-2">
            <button
              aria-label={`remove-chart-${index}`}
              className="text-red-500 hover:text-red-700"
              onClick={() => {
                if (!dashboardData || sectionIndex === undefined) return;
                const confirmRemove = window.confirm('Remove this chart from the dashboard?');
                if (!confirmRemove) return;
                // Remove the chart from state
                setDashboardData(prev => {
                  if (!prev) return prev;
                  const newSections = prev.sections.map((s: any, si: number) => {
                    if (si !== sectionIndex) return s;
                    if (s.type === 'charts_section' && Array.isArray(s.charts)) {
                      const newCharts = s.charts.filter((_: any, ci: number) => ci !== index);
                      return { ...s, charts: newCharts };
                    }
                    return s;
                  });
                  const updated = { ...prev, sections: newSections };
                  toast.success('Chart removed');
                  return updated;
                });
              }}
            >
              <FaTrash />
            </button>
          </div>
        </div>

        {/* Chart Content */}
        <div className="flex-1">
          <PlotlyChart
            data={chartData}
            layout={chartLayout}
            config={{
              ...(chart.config || {}),
              displayModeBar: true,
              responsive: true,
              displaylogo: false
            }}
            theme={currentTheme}
            style={{
              width: '100%',
              height: '100%',
              minHeight: '350px'
            }}
          />
        </div>
      </div>
    );
  };

  const renderSection = (section: any, sectionIndex: number) => {
    switch (section.type) {
      case 'kpi_section':
        return (
          <div 
            key={section.title} 
            className="mb-8"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            <h2 
              className="text-xl font-semibold mb-4"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              {section.title}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {section.cards?.map(renderKpiCard)}
            </div>
          </div>
        );

      case 'charts_section':
        return (
          <div 
            key={section.title} 
            className="mb-8"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            <h2 
              className="text-xl font-semibold mb-4"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              {section.title}
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {section.charts?.map((chart: any, index: number) => renderChart(chart, index, sectionIndex))}
            </div>
          </div>
        );

      case 'insights_section':
        return (
          <div 
            key={section.title} 
            className="mb-8"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            <h2 
              className="text-xl font-semibold mb-4"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              {section.title}
            </h2>
            <div className="space-y-4">
              {section.insights?.map((insight: any, idx: number) => (
                <div 
                  key={idx} 
                  className="border-l-4 p-4 rounded flex items-start justify-between"
                  style={{
                    backgroundColor: `${currentTheme?.colors?.chart || '#1f77b4'}10`,
                    borderColor: currentTheme?.colors?.chart || '#1f77b4'
                  }}
                >
                  <div className="flex items-start">
                    <FaLightbulb 
                      className="mt-0.5 mr-3 flex-shrink-0" 
                      style={{ color: currentTheme?.colors?.chart || '#1f77b4' }}
                    />
                    <div>
                      <h3 
                        className="font-medium"
                        style={{ color: currentTheme?.colors?.text || '#333333' }}
                      >
                        {insight.title}
                      </h3>
                      <p 
                        className="mt-1"
                        style={{ color: currentTheme?.colors?.text || '#333333' }}
                      >
                        {insight.description}
                      </p>
                    </div>
                  </div>
                  <div>
                    <button
                      aria-label={`remove-insight-${idx}`}
                      className="text-red-500 hover:text-red-700"
                      onClick={() => {
                        const confirmRemove = window.confirm('Remove this insight?');
                        if (!confirmRemove) return;
                        setDashboardData(prev => {
                          if (!prev) return prev;
                          const newSections = prev.sections.map((s: any, si: number) => {
                            if (si !== sectionIndex) return s;
                            if (s.type === 'insights_section' && Array.isArray(s.insights)) {
                              const newItems = s.insights.filter((_: any, i2: number) => i2 !== idx);
                              return { ...s, insights: newItems };
                            }
                            return s;
                          });
                          toast.success('Insight removed');
                          return { ...prev, sections: newSections };
                        });
                      }}
                    >
                      <FaTrash />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'recommendations_section':
        return (
          <div 
            key={section.title} 
            className="mb-8"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            <h2 
              className="text-xl font-semibold mb-4"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              {section.title}
            </h2>
            <div className="space-y-4">
              {section.recommendations?.map((rec: any, idx: number) => (
                <div 
                  key={idx} 
                  className="border-l-4 p-4 rounded flex items-start justify-between"
                  style={{
                    backgroundColor: `${currentTheme?.colors?.chart || '#1f77b4'}10`,
                    borderColor: currentTheme?.colors?.chart || '#1f77b4'
                  }}
                >
                  <div className="flex items-start">
                    <FaChartBar 
                      className="mt-0.5 mr-3 flex-shrink-0" 
                      style={{ color: currentTheme?.colors?.chart || '#1f77b4' }}
                    />
                    <div>
                      <h3 
                        className="font-medium"
                        style={{ color: currentTheme?.colors?.text || '#333333' }}
                      >
                        {rec.title}
                      </h3>
                      <p 
                        className="mt-1"
                        style={{ color: currentTheme?.colors?.text || '#333333' }}
                      >
                        {rec.description}
                      </p>
                    </div>
                  </div>
                  <div>
                    <button
                      aria-label={`remove-rec-${idx}`}
                      className="text-red-500 hover:text-red-700"
                      onClick={() => {
                        const confirmRemove = window.confirm('Remove this recommendation?');
                        if (!confirmRemove) return;
                        setDashboardData(prev => {
                          if (!prev) return prev;
                          const newSections = prev.sections.map((s: any, si: number) => {
                            if (si !== sectionIndex) return s;
                            if (s.type === 'recommendations_section' && Array.isArray(s.recommendations)) {
                              const newItems = s.recommendations.filter((_: any, i2: number) => i2 !== idx);
                              return { ...s, recommendations: newItems };
                            }
                            return s;
                          });
                          toast.success('Recommendation removed');
                          return { ...prev, sections: newSections };
                        });
                      }}
                    >
                      <FaTrash />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

    // Render a structured summary that emphasizes charts generated and important recommendations.
    const renderSummary = () => {
      if (!dashboardData) return null;

      const charts: { title: string; section: string }[] = [];
      const recommendations: any[] = [];

      (dashboardData.sections || []).forEach((s: any) => {
        if (s.type === 'charts_section' && Array.isArray(s.charts)) {
          s.charts.forEach((c: any) => charts.push({ title: c.title || 'Untitled Chart', section: s.title || 'Charts' }));
        }
        if (s.type === 'recommendations_section' && Array.isArray(s.recommendations)) {
          s.recommendations.forEach((r: any) => recommendations.push(r));
        }
      });

      return (
        <>
          <p className="leading-relaxed" style={{ color: currentTheme?.colors?.text || '#333333' }}>
            This dashboard contains <strong>{charts.length}</strong> {charts.length === 1 ? 'chart' : 'charts'} generated to help you explore the data and identify patterns.
          </p>

          {charts.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium">Charts generated</h3>
              <ul className="list-disc ml-6 mt-2">
                {charts.map((ch, idx) => (
                  <li key={idx}>
                    <strong>{ch.title}</strong>
                    {ch.section ? ` — ${ch.section}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {recommendations.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium">Top recommendations</h3>
              <ol className="list-decimal ml-6 mt-2">
                {recommendations.slice(0, 3).map((rec: any, idx: number) => (
                  <li key={idx} className="mb-2">
                    <div>
                      <strong>{rec.title || `Recommendation ${idx + 1}`}</strong>
                    </div>
                    {rec.description && (
                      <div className="mt-1" style={{ color: currentTheme?.colors?.text || '#333333' }}>
                        {rec.description}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
              {recommendations.length > 3 && (
                <div className="mt-2 text-sm text-gray-500">(Showing top 3 recommendations)</div>
              )}
            </div>
          )}

          {dashboardData.narrative && (
            <div className="mt-4">
              <h3 className="font-medium">Additional narrative</h3>
              <p className="mt-1" style={{ color: currentTheme?.colors?.text || '#333333' }}>{dashboardData.narrative}</p>
            </div>
          )}
        </>
      );
    };

  return (
    <div 
      className="space-y-6"
      style={{
        backgroundColor: currentTheme?.colors?.background || '#ffffff',
        color: currentTheme?.colors?.text || '#333333'
      }}
    >
      {/* Controls */}
      <div 
        className="panel p-6"
        style={{
          backgroundColor: currentTheme?.colors?.background || '#ffffff',
          color: currentTheme?.colors?.text || '#333333'
        }}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0 lg:space-x-4">
          <div className="flex-1">
            <label 
              htmlFor="file-select" 
              className="block text-sm font-medium mb-2"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              Data Source
            </label>
            <select
              id="file-select"
              value={selectedFileId || ''}
              onChange={(e) => setSelectedFileId(Number(e.target.value))}
              className="input-field"
              style={{
                backgroundColor: currentTheme?.colors?.background || '#ffffff',
                color: currentTheme?.colors?.text || '#333333',
                borderColor: currentTheme?.colors?.chart || '#1f77b4'
              }}
            >
              <option value="">Select a file...</option>
              {files.map((file) => (
                <option 
                  key={file.id} 
                  value={file.id}
                  style={{
                    backgroundColor: currentTheme?.colors?.background || '#ffffff',
                    color: currentTheme?.colors?.text || '#333333'
                  }}
                >
                  {file.file_name} ({file.file_type})
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1">
            <label 
              htmlFor="query" 
              className="block text-sm font-medium mb-2"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              Analysis Query
            </label>
            <input
              type="text"
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your analysis question..."
              className="input-field"
              style={{
                backgroundColor: currentTheme?.colors?.background || '#ffffff',
                color: currentTheme?.colors?.text || '#333333',
                borderColor: currentTheme?.colors?.chart || '#1f77b4'
              }}
            />
          </div>

          <div className="flex space-x-2">
            <button
              onClick={() => setShowColorGrid(!showColorGrid)}
              className="btn-secondary flex items-center"
              title="Customize theme"
              style={{
                backgroundColor: currentTheme?.colors?.chart || '#1f77b4',
                color: currentTheme?.colors?.background === '#ffffff' ? '#ffffff' : '#333333'
              }}
            >
              <FaCog className="mr-2 h-4 w-4" />
              Theme
            </button>

            <button
              onClick={toggleDragMode}
              className={`btn-secondary flex items-center ${isDragEnabled ? 'ring-2 ring-blue-500' : ''}`}
              title={isDragEnabled ? 'Disable drag mode' : 'Enable drag mode'}
              style={{
                backgroundColor: isDragEnabled ? '#10b981' : '#6b7280',
                color: '#ffffff'
              }}
            >
              <FaGripVertical className="mr-2 h-4 w-4" />
              {isDragEnabled ? 'Drag ON' : 'Drag OFF'}
            </button>

            <button
              onClick={generateDashboard}
              disabled={generating || !selectedFileId}
              className="btn-primary flex items-center"
              style={{
                backgroundColor: currentTheme?.colors?.chart || '#1f77b4',
                color: '#ffffff'
              }}
            >
              {generating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Generating...
                </>
              ) : (
                <>
                  <FaChartBar className="mr-2 h-4 w-4" />
                  Generate Dashboard
                </>
              )}
            </button>
          </div>
        </div>

        {/* Saved Dashboards Selector */}
        {savedDashboards.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <label 
              htmlFor="saved-dashboards" 
              className="block text-sm font-medium mb-2"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              Saved Dashboards
            </label>
            <div className="flex flex-wrap gap-2">
              {savedDashboards.map((dashboard) => (
                <button
                  key={dashboard.id}
                  onClick={() => loadSavedDashboard(dashboard.file_name)}
                  className="btn-secondary px-3 py-1 text-sm"
                  style={{
                    backgroundColor: currentTheme?.colors?.chart || '#1f77b4',
                    color: '#ffffff'
                  }}
                >
                  {dashboard.file_name.replace(/^dashboard_\d+_/, '').replace(/_\d{8}_\d{6}\.json$/, '') || 'Dashboard'} 
                  ({formatDate(dashboard.created_at)})
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Color Grid */}
        {showColorGrid && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <ColorGrid
              onThemeChange={handleThemeChange}
              currentTheme={currentTheme}
            />
          </div>
        )}
      </div>

      {/* Dashboard Content */}
      {dashboardData ? (
        <div className="space-y-6">
          {/* Dashboard Title */}
          <div 
            className="shadow-sm rounded-lg p-6"
            style={{
              backgroundColor: currentTheme?.colors?.background || '#ffffff',
              color: currentTheme?.colors?.text || '#333333'
            }}
          >
            <div className="flex items-center justify-between">
              <h1 
                className="text-2xl md:text-3xl font-bold"
                style={{ color: currentTheme?.colors?.text || '#333333' }}
              >
                {dashboardData.title}
              </h1>
              <button
                onClick={toggleFullscreen}
                className="flex items-center px-3 py-2 rounded-lg text-white shadow"
                style={{
                  background: `linear-gradient(90deg, ${currentTheme?.colors?.chart || '#1f77b4'}, ${currentTheme?.colors?.chart ? '#6b46c1' : '#155a8a'})`,
                }}
                title={isFullscreen ? 'Exit presentation mode' : 'Enter presentation mode'}
              >
                {isFullscreen ? <FaCompress className="mr-2" /> : <FaExpand className="mr-2" />}
                {isFullscreen ? 'Exit Presentation' : 'Presentation Mode'}
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={restoreDashboard}
                  className="btn-ghost px-3 py-1 border rounded"
                >
                  Restore
                </button>
                <button
                  onClick={() => {
                    if (!dashboardData || !dashboardData.narrative) {
                      toast.warn('No summary available to remove');
                      return;
                    }
                    const confirmRemove = window.confirm('Remove the dashboard summary?');
                    if (!confirmRemove) return;
                    setDashboardData(prev => prev ? { ...prev, narrative: '' } : prev);
                    toast.success('Summary removed');
                  }}
                  className="btn-ghost px-3 py-1 border rounded text-red-500"
                >
                  Remove Summary
                </button>
              </div>
            </div>
          </div>

          {/* Dashboard Sections */}
          {(dashboardData.sections || []).map((s: any, i: number) => renderSection(s, i))}

          {/* Narrative / Structured Summary */}
          <div 
            className="shadow-sm rounded-lg p-6"
            style={{
              backgroundColor: currentTheme?.colors?.background || '#ffffff',
              color: currentTheme?.colors?.text || '#333333'
            }}
          >
            <h2 
              className="text-xl font-semibold mb-4"
              style={{ color: currentTheme?.colors?.text || '#333333' }}
            >
              Summary
            </h2>
            <div className="prose prose-gray max-w-none">
              {renderSummary()}
            </div>
          </div>
        </div>
      ) : (
        <div 
          className="shadow-sm rounded-lg p-12 text-center"
          style={{
            backgroundColor: currentTheme?.colors?.background || '#ffffff',
            color: currentTheme?.colors?.text || '#333333'
          }}
        >
          <FaChartBar 
            className="h-16 w-16 mx-auto mb-4" 
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          />
          <h3 
            className="text-lg font-medium mb-2"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            No Dashboard Generated
          </h3>
          <p 
            className="mb-6"
            style={{ color: currentTheme?.colors?.text || '#333333' }}
          >
            Select a file and click "Generate Dashboard" to create your data visualization
          </p>

          {files.length === 0 && (
            <div 
              className="border-l-4 p-4 rounded"
              style={{
                backgroundColor: `${currentTheme?.colors?.chart || '#1f77b4'}10`,
                borderColor: currentTheme?.colors?.chart || '#1f77b4'
              }}
            >
              <div className="flex">
                <FaTable 
                  className="h-5 w-5" 
                  style={{ color: currentTheme?.colors?.chart || '#1f77b4' }}
                />
                <div className="ml-3">
                  <p 
                    className="text-sm"
                    style={{ color: currentTheme?.colors?.text || '#333333' }}
                  >
                    No processed files available. Please upload and process a file first.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;