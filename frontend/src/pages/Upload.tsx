import React, { useState, useRef } from 'react';
import { toast } from 'react-toastify';
import { FaUpload, FaLink, FaFileExcel, FaFileCsv, FaCheck, FaTimes } from 'react-icons/fa';
import apiService from '../services/api';
import { AxiosError } from 'axios';

interface FileUpload {
  id: number;
  file_name: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  is_processed: boolean;
  processing_status: string;
  row_count?: number;
  column_count?: number;
}

const Upload: React.FC = () => {
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [sheetUrl, setSheetUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const response = await apiService.getFiles();
      setFiles(response.files || []);
    } catch (error) {
      toast.error('Failed to load files');
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'text/csv'
    ];

    if (!allowedTypes.includes(file.type) && !file.name.endsWith('.csv') && !file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error('Please upload an Excel (.xlsx, .xls) or CSV file');
      return;
    }

    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size must be less than 10MB');
      return;
    }

    setUploading(true);

    try {
      const response = await apiService.uploadFile(file);
      
      if (response && response.file_id) {
        // Add the new file to the beginning of the files list
        setFiles(prevFiles => [
          {
            id: response.file_id,
            file_name: response.filename,
            file_type: file.name.endsWith('.csv') ? 'csv' : 'excel',
            file_size: file.size,
            uploaded_at: new Date().toISOString(),
            is_processed: response.status === 'processed',
            processing_status: response.status || 'pending'
          },
          ...prevFiles
        ]);
        
        toast.success(response.message || 'File uploaded successfully!');
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('File upload error:', error);
      if (error instanceof AxiosError) {
        toast.error(error.response?.data?.error || 'Failed to upload file');
      } else if (error instanceof Error) {
        toast.error(error.message || 'Failed to upload file');
      } else {
        toast.error('An unexpected error occurred');
      }
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleGoogleSheetConnect = async () => {
    if (!sheetUrl.trim()) {
      toast.error('Please enter a Google Sheet URL');
      return;
    }

    // Basic URL validation
    const sheetUrlPattern = /https:\/\/docs\.google\.com\/spreadsheets\/d\/[a-zA-Z0-9_-]+/;
    if (!sheetUrlPattern.test(sheetUrl)) {
      toast.error('Please enter a valid Google Sheet URL');
      return;
    }

    setConnecting(true);

    try {
      await apiService.connectGoogleSheet(sheetUrl);
      toast.success('Google Sheet connected successfully!');
      setSheetUrl('');
      loadFiles();
    } catch (error) {
      toast.error('Failed to connect Google Sheet');
    } finally {
      setConnecting(false);
    }
  };

  const handleDeleteFile = async (fileId: number) => {
    try {
      await apiService.deleteFile(fileId);
      toast.success('File deleted successfully');
      loadFiles();
    } catch (error) {
      toast.error('Failed to delete file');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'excel':
        return <FaFileExcel className="h-8 w-8 text-green-600" />;
      case 'csv':
        return <FaFileCsv className="h-8 w-8 text-blue-600" />;
      case 'google_sheet':
        return <FaLink className="h-8 w-8 text-purple-600" />;
      default:
        return <FaUpload className="h-8 w-8 text-gray-600" />;
    }
  };

  const getStatusIcon = (status: string, isProcessed: boolean) => {
    if (isProcessed) {
      return <FaCheck className="h-5 w-5 text-green-600" />;
    }
    if (status === 'failed') {
      return <FaTimes className="h-5 w-5 text-red-600" />;
    }
    return <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>;
  };

  return (
    <div className="space-y-6">
      <div className="panel">
        <div className="px-6 py-6 border-b border-gray-100">
          <h2 className="text-2xl font-bold text-gray-900">Upload Data</h2>
          <p className="mt-1 text-sm text-gray-600">
            Upload Excel files, CSV files, or connect to Google Sheets
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* File Upload */}
          <div>
            <h3 className="text-md font-medium text-gray-900 mb-4">Upload File</h3>
            <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center bg-gradient-to-br from-white to-blue-50">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center"
              >
                <FaUpload className="h-12 w-12 text-gray-400 mb-4" />
                <span className="text-sm text-gray-600 mb-2">
                  Click to upload or drag and drop
                </span>
                <span className="text-xs text-gray-500">
                  Excel (.xlsx, .xls) or CSV files up to 10MB
                </span>
              </label>
            </div>
            {uploading && (
              <div className="mt-4 text-center">
                <div className="inline-flex items-center text-blue-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                  Uploading...
                </div>
              </div>
            )}
          </div>

          {/* Google Sheets */}
          <div>
            <h3 className="text-md font-medium text-gray-900 mb-4">Connect Google Sheet</h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="sheet-url" className="block text-sm font-medium text-gray-700">
                  Google Sheet URL
                </label>
                <input
                  type="url"
                  id="sheet-url"
                  value={sheetUrl}
                  onChange={(e) => setSheetUrl(e.target.value)}
                  placeholder="https://docs.google.com/spreadsheets/d/..."
                  className="input-field mt-1"
                />
              </div>
              <button
                onClick={handleGoogleSheetConnect}
                disabled={connecting || !sheetUrl.trim()}
                className="btn-primary"
              >
                {connecting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Connecting...
                  </>
                ) : (
                  <>
                    <FaLink className="mr-2 h-4 w-4" />
                    Connect Sheet
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Files List */}
      <div className="panel">
        <div className="px-6 py-6 border-b border-gray-100">
          <h2 className="text-2xl font-bold text-gray-900">Your Files</h2>
          <p className="mt-1 text-sm text-gray-600">
            Manage your uploaded files and data sources
          </p>
        </div>

        <div className="divide-y divide-gray-100">
          {files.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              <FaUpload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium">No files uploaded yet</p>
              <p className="text-sm">Upload a file or connect a Google Sheet to get started</p>
            </div>
          ) : (
            files.map((file) => (
              <div key={file.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 flex items-center justify-center rounded-lg bg-gradient-to-br from-blue-50 to-purple-50">
                      {getFileIcon(file.file_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">
                        {file.file_name}
                      </p>
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span>{formatFileSize(file.file_size)}</span>
                        <span>{new Date(file.uploaded_at).toLocaleDateString()}</span>
                        {file.row_count && file.column_count && (
                          <span>{file.row_count} rows  d7 {file.column_count} cols</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(file.processing_status, file.is_processed)}
                      <span className="text-sm text-gray-500">
                        {file.is_processed ? 'Ready' : file.processing_status}
                      </span>
                    </div>

                    <button
                      onClick={() => handleDeleteFile(file.id)}
                      className="text-red-600 hover:text-red-800 p-2 rounded-md hover:bg-red-50"
                      title="Delete file"
                    >
                      <FaTimes className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Upload;
