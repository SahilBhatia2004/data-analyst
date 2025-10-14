import React, { useState, useCallback } from 'react';
import { FaEdit, FaTrash, FaExpand, FaCompress } from 'react-icons/fa';
import ChartComponent from './ChartComponent';

interface EditableRecommendationProps {
  recommendation: any;
  onSave: (newContent: string) => void;
  onDelete: () => void;
  theme: any;
  index: number;
}

const EditableRecommendation: React.FC<EditableRecommendationProps> = React.memo(({ 
  recommendation: rec, 
  onSave, 
  onDelete, 
  theme,
  index 
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(rec?.description || '');
  const [chartSize, setChartSize] = useState(1);

  const handleSave = useCallback(() => {
    onSave(editedContent);
    setIsEditing(false);
  }, [editedContent, onSave]);

  if (!rec) return null;

  return (
    <div 
      className="bg-white rounded-lg shadow-md overflow-hidden transition-all duration-300 p-4 mb-4"
      style={{
        borderLeft: `4px solid ${theme?.colors?.chart || '#1f77b4'}`,
        backgroundColor: theme?.colors?.background || '#ffffff',
        color: theme?.colors?.text || '#333333'
      }}
    >
      {isEditing ? (
        <div className="space-y-2">
          <textarea
            className="w-full p-2 border rounded"
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            style={{
              backgroundColor: theme?.colors?.background || '#ffffff',
              color: theme?.colors?.text || '#333333',
              borderColor: theme?.colors?.chart || '#1f77b4'
            }}
            rows={4}
          />
          <div className="flex space-x-2">
            <button
              onClick={handleSave}
              className="px-3 py-1 text-sm rounded text-white"
              style={{ backgroundColor: theme?.colors?.chart || '#1f77b4' }}
            >
              Save
            </button>
            <button
              onClick={() => {
                setEditedContent(rec.description);
                setIsEditing(false);
              }}
              className="px-3 py-1 text-sm border rounded"
              style={{
                borderColor: theme?.colors?.chart || '#1f77b4',
                color: theme?.colors?.text || '#333333'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <p className="text-gray-700" style={{ color: theme?.colors?.text || '#333333' }}>
                {rec.description}
              </p>
            </div>
            <div className="flex space-x-2 ml-2">
              <button
                onClick={() => {
                  setEditedContent(rec.description);
                  setIsEditing(true);
                }}
                className="p-1 rounded hover:bg-gray-200"
                style={{ color: theme?.colors?.text || '#333333' }}
                title="Edit recommendation"
              >
                <FaEdit />
              </button>
              <button
                onClick={onDelete}
                className="p-1 rounded hover:bg-red-100 text-red-500"
                title="Delete recommendation"
              >
                <FaTrash />
              </button>
            </div>
          </div>
          
          {rec.chart && (
            <div className="mt-4">
              <ChartComponent
                chart={rec.chart}
                chartData={rec.chart.data}
                index={index}
                theme={theme}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default EditableRecommendation;
