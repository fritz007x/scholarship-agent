import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { applicationsAPI, essaysAPI, documentsAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import {
  ArrowLeft,
  CheckCircle,
  Circle,
  Calendar,
  ExternalLink,
  FileText,
  FolderOpen,
  Trash2,
} from 'lucide-react';

export default function ApplicationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [application, setApplication] = useState(null);
  const [essays, setEssays] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      const [appRes, essaysRes, docsRes] = await Promise.all([
        applicationsAPI.get(id),
        essaysAPI.list(),
        documentsAPI.list(),
      ]);
      setApplication(appRes.data);
      setEssays(essaysRes.data.essays);
      setDocuments(docsRes.data.documents);
    } catch (err) {
      console.error('Failed to load application', err);
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleChecklistToggle = async (itemId, completed) => {
    setSaving(true);
    try {
      await applicationsAPI.updateChecklistItem(id, itemId, { completed });
      loadData();
    } catch (err) {
      alert('Failed to update checklist');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    setSaving(true);
    try {
      await applicationsAPI.update(id, { status: newStatus });
      loadData();
    } catch (err) {
      alert('Failed to update status');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this application?')) return;

    try {
      await applicationsAPI.delete(id);
      navigate('/dashboard');
    } catch (err) {
      alert('Failed to delete application');
    }
  };

  const handleAttachEssay = async (itemId, essayId) => {
    setSaving(true);
    try {
      await applicationsAPI.updateChecklistItem(id, itemId, {
        completed: true,
        essay_id: essayId,
      });
      loadData();
    } catch (err) {
      alert('Failed to attach essay');
    } finally {
      setSaving(false);
    }
  };

  const handleAttachDocument = async (itemId, documentId) => {
    setSaving(true);
    try {
      await applicationsAPI.updateChecklistItem(id, itemId, {
        completed: true,
        document_id: documentId,
      });
      loadData();
    } catch (err) {
      alert('Failed to attach document');
    } finally {
      setSaving(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      saved: 'bg-gray-100 text-gray-800',
      in_progress: 'bg-blue-100 text-blue-800',
      submitted: 'bg-green-100 text-green-800',
      awarded: 'bg-purple-100 text-purple-800',
      rejected: 'bg-red-100 text-red-800',
      withdrawn: 'bg-yellow-100 text-yellow-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      </Layout>
    );
  }

  if (!application) {
    return (
      <Layout>
        <Card>
          <p className="text-center text-gray-500">Application not found</p>
        </Card>
      </Layout>
    );
  }

  const checklist = application.checklist || [];
  const completedCount = checklist.filter((item) => item.completed).length;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link to="/dashboard" className="text-gray-400 hover:text-gray-600">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{application.scholarship_name}</h1>
              {application.scholarship_provider && (
                <p className="text-gray-500">{application.scholarship_provider}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <select
              value={application.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium ${getStatusColor(
                application.status
              )} border-0 cursor-pointer`}
              disabled={saving}
            >
              <option value="saved">Saved</option>
              <option value="in_progress">In Progress</option>
              <option value="submitted">Submitted</option>
              <option value="awarded">Awarded</option>
              <option value="rejected">Rejected</option>
              <option value="withdrawn">Withdrawn</option>
            </select>
            <Button variant="danger" size="sm" onClick={handleDelete}>
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <div className="flex items-center">
              <Calendar className="w-8 h-8 text-gray-400 mr-3" />
              <div>
                <p className="text-sm text-gray-500">Deadline</p>
                <p className="font-medium">
                  {application.deadline
                    ? new Date(application.deadline).toLocaleDateString()
                    : 'No deadline'}
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-gray-400 mr-3" />
              <div>
                <p className="text-sm text-gray-500">Progress</p>
                <p className="font-medium">
                  {completedCount} / {checklist.length} items
                </p>
              </div>
            </div>
          </Card>

          {application.scholarship_url && (
            <Card>
              <a
                href={application.scholarship_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-indigo-600 hover:text-indigo-800"
              >
                <ExternalLink className="w-8 h-8 mr-3" />
                <div>
                  <p className="text-sm text-gray-500">Scholarship</p>
                  <p className="font-medium">Visit Website</p>
                </div>
              </a>
            </Card>
          )}
        </div>

        {/* Checklist */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Application Checklist</h2>

          <div className="space-y-4">
            {checklist.map((item) => (
              <div
                key={item.id}
                className={`p-4 border rounded-lg ${item.completed ? 'bg-green-50 border-green-200' : 'bg-white'}`}
              >
                <div className="flex items-start">
                  <button
                    onClick={() => handleChecklistToggle(item.id, !item.completed)}
                    className="mt-0.5 mr-3 flex-shrink-0"
                    disabled={saving}
                  >
                    {item.completed ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <Circle className="w-5 h-5 text-gray-300" />
                    )}
                  </button>

                  <div className="flex-1">
                    <p className={`font-medium ${item.completed ? 'text-green-800' : 'text-gray-900'}`}>
                      {item.description}
                    </p>
                    {item.word_count && (
                      <p className="text-sm text-gray-500">Word limit: {item.word_count}</p>
                    )}

                    {/* Attach essay selector */}
                    {item.type === 'essay' && !item.completed && (
                      <div className="mt-2">
                        <select
                          onChange={(e) => {
                            if (e.target.value) handleAttachEssay(item.id, parseInt(e.target.value));
                          }}
                          className="text-sm border border-gray-300 rounded px-2 py-1"
                          defaultValue=""
                        >
                          <option value="">Attach an essay...</option>
                          {essays.map((essay) => (
                            <option key={essay.id} value={essay.id}>
                              {essay.title}
                            </option>
                          ))}
                        </select>
                        <Link
                          to="/essays"
                          className="ml-2 text-sm text-indigo-600 hover:text-indigo-800"
                        >
                          <FileText className="w-4 h-4 inline mr-1" />
                          Go to Essays
                        </Link>
                      </div>
                    )}

                    {/* Attach document selector */}
                    {item.type === 'document' && !item.completed && (
                      <div className="mt-2">
                        <select
                          onChange={(e) => {
                            if (e.target.value) handleAttachDocument(item.id, parseInt(e.target.value));
                          }}
                          className="text-sm border border-gray-300 rounded px-2 py-1"
                          defaultValue=""
                        >
                          <option value="">Attach a document...</option>
                          {documents.map((doc) => (
                            <option key={doc.id} value={doc.id}>
                              {doc.title || doc.original_filename}
                            </option>
                          ))}
                        </select>
                        <Link
                          to="/documents"
                          className="ml-2 text-sm text-indigo-600 hover:text-indigo-800"
                        >
                          <FolderOpen className="w-4 h-4 inline mr-1" />
                          Go to Documents
                        </Link>
                      </div>
                    )}

                    {/* Show attached resource */}
                    {item.essay_id && (
                      <p className="text-sm text-green-600 mt-1">
                        <FileText className="w-4 h-4 inline mr-1" />
                        Essay attached
                      </p>
                    )}
                    {item.document_id && (
                      <p className="text-sm text-green-600 mt-1">
                        <FolderOpen className="w-4 h-4 inline mr-1" />
                        Document attached
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {checklist.length === 0 && (
              <p className="text-center text-gray-500 py-4">No checklist items</p>
            )}
          </div>
        </Card>

        {/* Notes */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Notes</h2>
          <textarea
            className="w-full border border-gray-300 rounded-md p-3"
            rows={4}
            placeholder="Add notes about this application..."
            defaultValue={application.notes || ''}
            onBlur={async (e) => {
              if (e.target.value !== application.notes) {
                await applicationsAPI.update(id, { notes: e.target.value });
              }
            }}
          />
        </Card>
      </div>
    </Layout>
  );
}
