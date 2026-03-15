import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { applicationsAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { Calendar, CheckCircle, Clock, AlertCircle, Plus } from 'lucide-react';

export default function Dashboard() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      const response = await applicationsAPI.list();
      setApplications(response.data.applications);
    } catch (err) {
      setError('Failed to load applications');
    } finally {
      setLoading(false);
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

  const getDeadlineStatus = (deadline) => {
    if (!deadline) return null;
    const days = Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
    if (days < 0) return { color: 'text-red-600', text: 'Past due' };
    if (days <= 7) return { color: 'text-red-600', text: `${days} days left` };
    if (days <= 30) return { color: 'text-yellow-600', text: `${days} days left` };
    return { color: 'text-gray-600', text: `${days} days left` };
  };

  const stats = {
    total: applications.length,
    inProgress: applications.filter((a) => a.status === 'in_progress').length,
    submitted: applications.filter((a) => a.status === 'submitted').length,
    awarded: applications.filter((a) => a.status === 'awarded').length,
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

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <Link to="/scholarships">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Find Scholarships
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-indigo-100 rounded-lg">
                <Clock className="w-6 h-6 text-indigo-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500">Total Applications</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg">
                <AlertCircle className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500">In Progress</p>
                <p className="text-2xl font-bold">{stats.inProgress}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500">Submitted</p>
                <p className="text-2xl font-bold">{stats.submitted}</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Calendar className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500">Awarded</p>
                <p className="text-2xl font-bold">{stats.awarded}</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Applications List */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Your Applications</h2>

          {error && (
            <div className="p-4 bg-red-50 text-red-600 rounded-md mb-4">{error}</div>
          )}

          {applications.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">You haven't started any applications yet.</p>
              <Link to="/scholarships">
                <Button>Browse Scholarships</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {applications.map((app) => {
                const deadlineStatus = getDeadlineStatus(app.deadline);
                return (
                  <Link
                    key={app.id}
                    to={`/applications/${app.id}`}
                    className="block p-4 border rounded-lg hover:border-indigo-300 transition-colors"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-gray-900">{app.scholarship_name}</h3>
                        {app.scholarship_provider && (
                          <p className="text-sm text-gray-500">{app.scholarship_provider}</p>
                        )}
                        <div className="mt-2 flex items-center space-x-4">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(app.status)}`}>
                            {app.status.replace('_', ' ')}
                          </span>
                          {deadlineStatus && (
                            <span className={`text-sm ${deadlineStatus.color}`}>
                              {deadlineStatus.text}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        {app.scholarship_award_amount && (
                          <p className="font-medium text-green-600">
                            ${app.scholarship_award_amount.toLocaleString()}
                          </p>
                        )}
                        <div className="mt-2">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-indigo-600 h-2 rounded-full"
                              style={{ width: `${app.checklist_total > 0 ? (app.checklist_completed / app.checklist_total) * 100 : 0}%` }}
                            ></div>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {app.checklist_completed}/{app.checklist_total} complete
                          </p>
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}
