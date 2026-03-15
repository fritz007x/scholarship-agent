import { useState, useEffect, useRef } from 'react';
import { documentsAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { Upload, Download, Trash2, FileText, File, Image } from 'lucide-react';

// File validation constants
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'image/png',
  'image/jpeg',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await documentsAPI.list();
      setDocuments(response.data.documents);
    } catch (err) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  };

  const validateFile = (file) => {
    if (file.size > MAX_FILE_SIZE) {
      return `File "${file.name}" exceeds 10MB size limit`;
    }
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      return `File type not allowed for "${file.name}". Allowed: PDF, DOC, DOCX, TXT, PNG, JPG, XLS, XLSX`;
    }
    return null;
  };

  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    const errors = [];

    for (const file of files) {
      const validationError = validateFile(file);
      if (validationError) {
        errors.push(validationError);
        continue;
      }

      try {
        await documentsAPI.upload(file, {
          title: file.name,
          document_type: guessDocumentType(file.name),
        });
      } catch (err) {
        errors.push(`Failed to upload ${file.name}: ${err.response?.data?.detail || 'Unknown error'}`);
      }
    }

    if (errors.length > 0) {
      alert(errors.join('\n'));
    }

    loadDocuments();
    setUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDownload = async (doc) => {
    try {
      const response = await documentsAPI.download(doc.id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.original_filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to download file');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await documentsAPI.delete(id);
      loadDocuments();
    } catch (err) {
      alert('Failed to delete document');
    }
  };

  const guessDocumentType = (filename) => {
    const lower = filename.toLowerCase();
    if (lower.includes('transcript')) return 'transcript';
    if (lower.includes('resume') || lower.includes('cv')) return 'resume';
    if (lower.includes('recommendation') || lower.includes('letter')) return 'recommendation_letter';
    if (lower.includes('financial') || lower.includes('fafsa')) return 'financial_document';
    return 'other';
  };

  const getFileIcon = (mimeType) => {
    if (mimeType?.startsWith('image/')) return Image;
    if (mimeType === 'application/pdf') return FileText;
    return File;
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const documentTypeLabels = {
    transcript: 'Transcript',
    recommendation_letter: 'Recommendation Letter',
    resume: 'Resume/CV',
    financial_document: 'Financial Document',
    essay: 'Essay',
    other: 'Other',
  };

  // Group documents by type
  const groupedDocuments = documents.reduce((acc, doc) => {
    const type = doc.document_type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(doc);
    return acc;
  }, {});

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Document Vault</h1>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleUpload}
              className="hidden"
              accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.xls,.xlsx"
            />
            <Button onClick={() => fileInputRef.current?.click()} loading={uploading}>
              <Upload className="w-4 h-4 mr-2" />
              Upload Documents
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        ) : documents.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <File className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500 mb-4">
                No documents uploaded yet. Upload your transcripts, resumes, and other application materials.
              </p>
              <Button onClick={() => fileInputRef.current?.click()}>
                Upload Your First Document
              </Button>
            </div>
          </Card>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedDocuments).map(([type, docs]) => (
              <Card key={type}>
                <h2 className="text-lg font-semibold mb-4">{documentTypeLabels[type] || type}</h2>
                <div className="space-y-3">
                  {docs.map((doc) => {
                    const FileIcon = getFileIcon(doc.mime_type);
                    return (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center">
                          <FileIcon className="w-8 h-8 text-gray-400 mr-3" />
                          <div>
                            <p className="font-medium text-gray-900">{doc.title || doc.original_filename}</p>
                            <p className="text-sm text-gray-500">
                              {formatFileSize(doc.file_size)}
                              {doc.used_in_applications?.length > 0 && (
                                <span> | Used in {doc.used_in_applications.length} applications</span>
                              )}
                            </p>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleDownload(doc)}
                            className="p-2 text-gray-400 hover:text-indigo-600"
                            title="Download"
                          >
                            <Download className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-2 text-gray-400 hover:text-red-600"
                            title="Delete"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
