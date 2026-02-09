import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentIcon } from '@heroicons/react/24/outline';

export default function DragDropZone({ title, onFilesAdded, multiple = true, currentFiles = [] }) {
  const onDrop = useCallback(acceptedFiles => {
    // Pass the files back to the parent component
    onFilesAdded(acceptedFiles);
  }, [onFilesAdded]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: multiple,
    accept: {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        'application/vnd.ms-excel': ['.xls']
    }
  });

  return (
    <div 
      {...getRootProps()} 
      className={`p-6 rounded-xl border-2 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center h-48 group
        ${isDragActive 
          ? 'border-blue-500 bg-blue-900/20' 
          : 'border-gray-700 bg-gray-800 hover:border-gray-500 hover:bg-gray-700/50'
        }`}
    >
      <input {...getInputProps()} />
      
      <CloudArrowUpIcon className={`h-10 w-10 mb-3 transition-colors ${isDragActive ? 'text-blue-400' : 'text-gray-500 group-hover:text-white'}`} />
      
      <h3 className="text-lg font-medium text-gray-300 mb-1">{title}</h3>
      
      <p className="text-xs text-gray-500 text-center">
        {isDragActive ? "Drop the files here..." : "Drag & drop files here, or click to select"}
      </p>

      {/* Show count of selected files */}
      {currentFiles && currentFiles.length > 0 && (
          <div className="mt-3 bg-green-900/30 text-green-400 text-xs px-2 py-1 rounded border border-green-900/50 flex items-center gap-2">
              <DocumentIcon className="h-4 w-4" />
              {currentFiles.length} file(s) ready
          </div>
      )}
    </div>
  );
}