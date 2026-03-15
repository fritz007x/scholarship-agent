import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { essaysAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { Plus, Edit2, Trash2, FileText, Tag } from 'lucide-react';

export default function Essays() {
  const [essays, setEssays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', content: '', prompt: '', prompt_category: '' });
  const navigate = useNavigate();

  useEffect(() => {
    loadEssays();
  }, []);

  const loadEssays = async () => {
    try {
      const response = await essaysAPI.list();
      setEssays(response.data.essays);
    } catch (err) {
      console.error('Failed to load essays', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const response = await essaysAPI.create({
        title: 'New Essay',
        content: '',
        prompt: '',
        prompt_category: 'other',
      });
      setEditingId(response.data.id);
      setEditForm({
        title: response.data.title,
        content: response.data.content || '',
        prompt: response.data.prompt || '',
        prompt_category: response.data.prompt_category || 'other',
      });
      loadEssays();
    } catch (err) {
      alert('Failed to create essay');
    }
  };

  const handleEdit = (essay) => {
    setEditingId(essay.id);
    setEditForm({
      title: essay.title,
      content: essay.content || '',
      prompt: essay.prompt || '',
      prompt_category: essay.prompt_category || 'other',
    });
  };

  const handleSave = async () => {
    try {
      await essaysAPI.update(editingId, editForm);
      setEditingId(null);
      loadEssays();
    } catch (err) {
      alert('Failed to save essay');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this essay?')) return;

    try {
      await essaysAPI.delete(id);
      loadEssays();
    } catch (err) {
      alert('Failed to delete essay');
    }
  };

  const categoryLabels = {
    career_goals: 'Career Goals',
    overcoming_challenges: 'Overcoming Challenges',
    community_service: 'Community Service',
    leadership: 'Leadership',
    personal_growth: 'Personal Growth',
    academic_interests: 'Academic Interests',
    why_this_school: 'Why This School',
    other: 'Other',
  };

  const countWords = (text) => {
    if (!text) return 0;
    return text.trim().split(/\s+/).filter(Boolean).length;
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Essay Library</h1>
          <Button onClick={handleCreate}>
            <Plus className="w-4 h-4 mr-2" />
            New Essay
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        ) : editingId ? (
          <Card>
            <div className="space-y-4">
              <input
                type="text"
                value={editForm.title}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                placeholder="Essay Title"
                className="w-full text-xl font-bold border-0 border-b-2 border-gray-200 focus:border-indigo-500 focus:ring-0 pb-2"
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={editForm.prompt_category}
                    onChange={(e) => setEditForm({ ...editForm, prompt_category: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    {Object.entries(categoryLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Word Count: {countWords(editForm.content)}
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
                <textarea
                  value={editForm.prompt}
                  onChange={(e) => setEditForm({ ...editForm, prompt: e.target.value })}
                  placeholder="Enter the essay prompt..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Essay Content</label>
                <textarea
                  value={editForm.content}
                  onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                  placeholder="Write your essay..."
                  rows={15}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono"
                />
              </div>

              <div className="flex justify-end space-x-3">
                <Button variant="secondary" onClick={() => setEditingId(null)}>
                  Cancel
                </Button>
                <Button onClick={handleSave}>Save Essay</Button>
              </div>
            </div>
          </Card>
        ) : essays.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500 mb-4">
                No essays yet. Start building your essay library for scholarship applications.
              </p>
              <Button onClick={handleCreate}>Create Your First Essay</Button>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {essays.map((essay) => (
              <Card key={essay.id} className="hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{essay.title}</h3>
                    <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                      <span>{countWords(essay.content)} words</span>
                      {essay.prompt_category && (
                        <span className="flex items-center">
                          <Tag className="w-3 h-3 mr-1" />
                          {categoryLabels[essay.prompt_category] || essay.prompt_category}
                        </span>
                      )}
                    </div>
                    {essay.used_in_applications?.length > 0 && (
                      <p className="text-xs text-gray-400 mt-1">
                        Used in {essay.used_in_applications.length} applications
                      </p>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleEdit(essay)}
                      className="p-2 text-gray-400 hover:text-indigo-600"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(essay.id)}
                      className="p-2 text-gray-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
