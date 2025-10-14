import React, { useState, useRef, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { FaPaperPlane, FaRobot, FaUser, FaSpinner, FaFileAlt } from 'react-icons/fa';
import apiService from '../services/api';

interface Message {
  id: string;
  message: string;
  isUser: boolean;
  timestamp: Date;
  sqlQuery?: string;
  data?: any[];
}

interface File {
  id: number;
  file_name: string;
  file_type: string;
  is_processed: boolean;
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadFiles = useCallback(async () => {
    try {
      const response = await apiService.getFiles();
      const processedFiles = response.files?.filter((file: File) => file.is_processed) || [];
      setFiles(processedFiles);

      // Auto-select first available file
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputMessage.trim() || !selectedFileId) {
      toast.error('Please select a file and enter a message');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      message: inputMessage.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await apiService.sendChatMessage(inputMessage, selectedFileId, sessionId || undefined);

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        message: response.response,
        isUser: false,
        timestamp: new Date(),
        sqlQuery: response.sql_query,
        data: response.data,
      };

      setMessages(prev => [...prev, aiMessage]);

      // Update session ID if provided
      if (response.session_id) {
        setSessionId(response.session_id);
      }

    } catch (error) {
      toast.error('Failed to send message');

      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        message: 'Sorry, I encountered an error. Please try again.',
        isUser: false,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const renderMessage = (message: Message) => {
    const isUser = message.isUser;

    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`flex max-w-xs lg:max-w-md ${isUser ? 'order-2' : 'order-1'}`}>
          {/* Avatar */}
          <div className={`flex-shrink-0 ${isUser ? 'order-2' : 'order-1'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              isUser ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600'
            }`}>
              {isUser ? <FaUser className="h-4 w-4" /> : <FaRobot className="h-4 w-4" />}
            </div>
          </div>

          {/* Message bubble */}
          <div className={`mx-3 ${isUser ? 'order-1' : 'order-2'}`}>
            <div className={`px-4 py-2 rounded-lg ${
              isUser
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-800'
            }`}>
              <p className="text-sm whitespace-pre-wrap">{message.message}</p>

              {/* Show SQL query if available */}
              {message.sqlQuery && (
                <div className="mt-2 pt-2 border-t border-gray-300">
                  <p className="text-xs text-gray-500 mb-1">Generated SQL:</p>
                  <code className="text-xs bg-gray-200 p-1 rounded block overflow-x-auto">
                    {message.sqlQuery}
                  </code>
                </div>
              )}

              {/* Show data preview if available */}
              {message.data && message.data.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-300">
                  <p className="text-xs text-gray-500 mb-1">Data Preview:</p>
                  <div className="max-h-32 overflow-y-auto">
                    <table className="text-xs w-full">
                      <thead>
                        <tr className="border-b">
                          {Object.keys(message.data[0]).map(key => (
                            <th key={key} className="text-left py-1 px-2 border-r">
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {message.data.slice(0, 3).map((row, idx) => (
                          <tr key={idx} className="border-b">
                            {Object.values(row).map((value: any, cellIdx) => (
                              <td key={cellIdx} className="py-1 px-2 border-r">
                                {String(value)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {message.data.length > 3 && (
                    <p className="text-xs text-gray-500 mt-1">
                      ... and {message.data.length - 3} more rows
                    </p>
                  )}
                </div>
              )}
            </div>

            <p className={`text-xs mt-1 ${isUser ? 'text-right' : 'text-left'} text-gray-500`}>
              {formatTimestamp(message.timestamp)}
            </p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* File Selection */}
      <div className="panel p-4 rounded-b-none">
        <div className="flex items-center space-x-4">
          <label htmlFor="file-select" className="text-sm font-medium text-gray-700">
            Data Source:
          </label>
          <select
            id="file-select"
            value={selectedFileId || ''}
            onChange={(e) => setSelectedFileId(Number(e.target.value))}
            className="input-field max-w-sm"
          >
            <option value="">Select a file...</option>
            {files.map((file) => (
              <option key={file.id} value={file.id}>
                {file.file_name} ({file.file_type})
              </option>
            ))}
          </select>

          {files.length === 0 && (
            <p className="text-sm text-gray-500 flex items-center">
              <FaFileAlt className="mr-1 h-4 w-4" />
              No processed files available. Please upload and process a file first.
            </p>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-white/60 to-gray-50">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <FaRobot className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
              <p className="text-sm">
                Ask me anything about your data! Try questions like:
              </p>
              <div className="mt-4 space-y-2 text-left max-w-md mx-auto">
                <div className="bg-white p-3 rounded-lg shadow-sm text-sm">
                  "What are the total sales by category?"
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm text-sm">
                  "Show me the average revenue per month"
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm text-sm">
                  "Which products have the highest profit margins?"
                </div>
              </div>
            </div>
          ) : (
            messages.map(renderMessage)
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="flex max-w-xs lg:max-w-md">
                <div className="flex-shrink-0 mr-3">
                  <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                    <FaRobot className="h-4 w-4 text-gray-600" />
                  </div>
                </div>
                <div className="bg-white rounded-lg px-4 py-2 shadow-sm">
                  <div className="flex items-center space-x-2">
                    <FaSpinner className="h-4 w-4 animate-spin text-gray-600" />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="panel p-4 rounded-t-none">
        <form onSubmit={handleSubmit} className="flex space-x-4 max-w-4xl mx-auto">
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                selectedFileId
                  ? "Ask me anything about your data..."
                  : "Please select a file first..."
              }
              disabled={!selectedFileId}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent resize-none"
              rows={3}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !inputMessage.trim() || !selectedFileId}
            className="px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {loading ? (
              <FaSpinner className="h-4 w-4 animate-spin" />
            ) : (
              <FaPaperPlane className="h-4 w-4" />
            )}
          </button>
        </form>

        <div className="mt-2 text-xs text-gray-500 text-center">
          Press Enter to send, Shift + Enter for new line
        </div>
      </div>
    </div>
  );
};

export default Chat;
