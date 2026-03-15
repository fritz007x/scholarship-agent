import { useState, useEffect, useCallback } from 'react';
import { scraperAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import {
  Play,
  Square,
  RefreshCw,
  Settings,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Database,
  Activity,
  List,
  ChevronDown,
  ChevronUp,
  Loader,
  Globe,
  FileText,
} from 'lucide-react';

function StatusBadge({ status }) {
  const styles = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800',
  };

  const icons = {
    pending: Clock,
    running: Loader,
    completed: CheckCircle,
    failed: XCircle,
    cancelled: AlertTriangle,
  };

  const Icon = icons[status] || Clock;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
      <Icon className={`w-3 h-3 mr-1 ${status === 'running' ? 'animate-spin' : ''}`} />
      {status}
    </span>
  );
}

function StatCard({ icon: Icon, label, value, subtext }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="flex items-center">
        <div className="p-2 bg-indigo-100 rounded-lg">
          <Icon className="w-5 h-5 text-indigo-600" />
        </div>
        <div className="ml-4">
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {subtext && <p className="text-xs text-gray-400">{subtext}</p>}
        </div>
      </div>
    </div>
  );
}

function JobRow({ job, onViewDetails, onCancel }) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm text-gray-900">#{job.id}</td>
      <td className="px-4 py-3 text-sm">
        <span className="font-medium text-gray-900">{job.source}</span>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={job.status} />
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {job.started_at ? new Date(job.started_at).toLocaleString() : '-'}
      </td>
      <td className="px-4 py-3 text-sm text-gray-900">
        +{job.scholarships_added || 0}
      </td>
      <td className="px-4 py-3 text-sm text-red-600">
        {job.errors_count || 0}
      </td>
      <td className="px-4 py-3 text-sm">
        <div className="flex space-x-2">
          <button
            onClick={() => onViewDetails(job.id)}
            className="text-indigo-600 hover:text-indigo-800"
          >
            Details
          </button>
          {job.status === 'running' && (
            <button
              onClick={() => onCancel(job.id)}
              className="text-red-600 hover:text-red-800"
            >
              Cancel
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function JobDetails({ job, logs, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-4 border-b flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              Job #{job.id} - {job.source}
            </h2>
            <StatusBadge status={job.status} />
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <div className="p-4 border-b">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-gray-500">Started</p>
              <p className="text-sm font-medium">
                {job.started_at ? new Date(job.started_at).toLocaleString() : '-'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Completed</p>
              <p className="text-sm font-medium">
                {job.completed_at ? new Date(job.completed_at).toLocaleString() : '-'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Found</p>
              <p className="text-sm font-medium">{job.scholarships_found || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Added</p>
              <p className="text-sm font-medium text-green-600">+{job.scholarships_added || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Updated</p>
              <p className="text-sm font-medium text-blue-600">{job.scholarships_updated || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Skipped</p>
              <p className="text-sm font-medium text-gray-600">{job.scholarships_skipped || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Errors</p>
              <p className="text-sm font-medium text-red-600">{job.errors_count || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Mode</p>
              <p className="text-sm font-medium">{job.mode || 'incremental'}</p>
            </div>
          </div>

          {job.error_message && (
            <div className="mt-4 p-3 bg-red-50 rounded-lg">
              <p className="text-sm text-red-600">{job.error_message}</p>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Logs</h3>
          {logs.length === 0 ? (
            <p className="text-sm text-gray-500">No logs available</p>
          ) : (
            <div className="space-y-1 font-mono text-xs">
              {logs.map((log, i) => (
                <div
                  key={i}
                  className={`p-2 rounded ${
                    log.level === 'ERROR'
                      ? 'bg-red-50 text-red-800'
                      : log.level === 'WARNING'
                      ? 'bg-yellow-50 text-yellow-800'
                      : 'bg-gray-50 text-gray-700'
                  }`}
                >
                  <span className="text-gray-400">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>{' '}
                  <span className="font-medium">[{log.level}]</span>{' '}
                  {log.message}
                  {log.url && (
                    <span className="block text-gray-500 truncate">{log.url}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

function ConfigPanel({ configs, onUpdate, onClose }) {
  const [editingSource, setEditingSource] = useState(null);
  const [formData, setFormData] = useState({});

  const handleEdit = (config) => {
    setEditingSource(config.source);
    setFormData({
      enabled: config.enabled,
      rate_limit_delay: config.rate_limit_delay,
      jitter: config.jitter,
      max_retries: config.max_retries,
    });
  };

  const handleSave = async () => {
    await onUpdate(editingSource, formData);
    setEditingSource(null);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="text-lg font-bold text-gray-900">Scraper Configuration</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            {configs.map((config) => (
              <div key={config.source} className="border rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-medium text-gray-900">{config.source}</h3>
                    <p className="text-xs text-gray-500">
                      Last run: {config.last_successful_run
                        ? new Date(config.last_successful_run).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${
                    config.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {config.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>

                {editingSource === config.source ? (
                  <div className="space-y-3">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id={`enabled-${config.source}`}
                        checked={formData.enabled}
                        onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                        className="h-4 w-4 text-indigo-600 rounded"
                      />
                      <label htmlFor={`enabled-${config.source}`} className="ml-2 text-sm text-gray-700">
                        Enabled
                      </label>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Delay (sec)</label>
                        <input
                          type="number"
                          value={formData.rate_limit_delay}
                          onChange={(e) => setFormData({ ...formData, rate_limit_delay: parseInt(e.target.value) })}
                          className="w-full px-2 py-1 border rounded text-sm"
                          min="1"
                          max="60"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Jitter (sec)</label>
                        <input
                          type="number"
                          value={formData.jitter}
                          onChange={(e) => setFormData({ ...formData, jitter: parseInt(e.target.value) })}
                          className="w-full px-2 py-1 border rounded text-sm"
                          min="0"
                          max="10"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Max Retries</label>
                        <input
                          type="number"
                          value={formData.max_retries}
                          onChange={(e) => setFormData({ ...formData, max_retries: parseInt(e.target.value) })}
                          className="w-full px-2 py-1 border rounded text-sm"
                          min="1"
                          max="10"
                        />
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <Button size="sm" onClick={handleSave}>Save</Button>
                      <Button size="sm" variant="secondary" onClick={() => setEditingSource(null)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-600">
                      Delay: {config.rate_limit_delay}s | Jitter: {config.jitter}s | Retries: {config.max_retries}
                    </div>
                    <Button size="sm" variant="secondary" onClick={() => handleEdit(config)}>
                      Edit
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 border-t">
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
}

export default function AdminScraper() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);
  const [sources, setSources] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [configs, setConfigs] = useState([]);

  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetails, setJobDetails] = useState(null);
  const [jobLogs, setJobLogs] = useState([]);

  const [showConfig, setShowConfig] = useState(false);
  const [startingJob, setStartingJob] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [statusRes, sourcesRes, jobsRes, configsRes] = await Promise.all([
        scraperAPI.status(),
        scraperAPI.sources(),
        scraperAPI.listJobs({ limit: 20 }),
        scraperAPI.listConfigs(),
      ]);

      setStatus(statusRes.data);
      setSources(sourcesRes.data.sources || []);
      setJobs(jobsRes.data.jobs || []);
      setConfigs(configsRes.data.configs || []);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('Admin access required to view scraper management.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load scraper data');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Refresh every 10 seconds if there are running jobs
    const interval = setInterval(() => {
      if (jobs.some(j => j.status === 'running')) {
        loadData();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [loadData, jobs]);

  const handleStartJob = async (source) => {
    setStartingJob(source);
    try {
      await scraperAPI.startJob(source, 'incremental');
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start job');
    } finally {
      setStartingJob(null);
    }
  };

  const handleCancelJob = async (jobId) => {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    try {
      await scraperAPI.cancelJob(jobId);
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to cancel job');
    }
  };

  const handleViewDetails = async (jobId) => {
    try {
      const response = await scraperAPI.getJob(jobId);
      setJobDetails(response.data.job);
      setJobLogs(response.data.logs || []);
      setSelectedJob(jobId);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to load job details');
    }
  };

  const handleUpdateConfig = async (source, config) => {
    try {
      await scraperAPI.updateConfig(source, config);
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update config');
    }
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

  if (error) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <AlertTriangle className="w-16 h-16 mx-auto text-red-500 mb-4" />
              <h2 className="text-xl font-bold text-gray-900 mb-2">Access Denied</h2>
              <p className="text-gray-600">{error}</p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Scraper Management</h1>
            <p className="text-gray-500">Manage scholarship web scraping jobs</p>
          </div>
          <div className="flex space-x-2">
            <Button variant="secondary" onClick={() => setShowConfig(true)}>
              <Settings className="w-4 h-4 mr-2" />
              Config
            </Button>
            <Button variant="secondary" onClick={loadData}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            icon={Database}
            label="Total Added"
            value={status?.statistics?.total_scholarships_added || 0}
            subtext="scholarships"
          />
          <StatCard
            icon={RefreshCw}
            label="Total Updated"
            value={status?.statistics?.total_scholarships_updated || 0}
            subtext="scholarships"
          />
          <StatCard
            icon={Activity}
            label="Running Jobs"
            value={status?.statistics?.jobs_by_status?.running || 0}
          />
          <StatCard
            icon={AlertTriangle}
            label="Total Errors"
            value={status?.statistics?.total_errors || 0}
          />
        </div>

        {/* Sources */}
        <Card>
          <div className="p-4 border-b">
            <h2 className="font-bold text-gray-900">Available Sources</h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sources.map((source) => {
                const config = configs.find(c => c.source === source.name);
                const isRunning = jobs.some(j => j.source === source.name && j.status === 'running');
                const isEnabled = config?.enabled !== false;

                return (
                  <div
                    key={source.name}
                    className={`border rounded-lg p-4 ${!isEnabled ? 'opacity-50' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center">
                        <Globe className="w-5 h-5 text-indigo-600 mr-2" />
                        <h3 className="font-medium text-gray-900">{source.name}</h3>
                      </div>
                      {isRunning && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-full">
                          Running
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mb-3">{source.description}</p>
                    {config?.last_successful_run && (
                      <p className="text-xs text-gray-400 mb-3">
                        Last run: {new Date(config.last_successful_run).toLocaleDateString()}
                      </p>
                    )}
                    <Button
                      size="sm"
                      onClick={() => handleStartJob(source.name)}
                      loading={startingJob === source.name}
                      disabled={isRunning || !isEnabled}
                    >
                      <Play className="w-4 h-4 mr-1" />
                      {isRunning ? 'Running...' : 'Start Job'}
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>

        {/* Jobs Table */}
        <Card>
          <div className="p-4 border-b flex justify-between items-center">
            <h2 className="font-bold text-gray-900">Recent Jobs</h2>
            <span className="text-sm text-gray-500">{jobs.length} jobs</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Added</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Errors</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                      No scraping jobs yet. Start one from the sources above.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <JobRow
                      key={job.id}
                      job={job}
                      onViewDetails={handleViewDetails}
                      onCancel={handleCancelJob}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Job Details Modal */}
      {selectedJob && jobDetails && (
        <JobDetails
          job={jobDetails}
          logs={jobLogs}
          onClose={() => {
            setSelectedJob(null);
            setJobDetails(null);
            setJobLogs([]);
          }}
        />
      )}

      {/* Config Modal */}
      {showConfig && (
        <ConfigPanel
          configs={configs}
          onUpdate={handleUpdateConfig}
          onClose={() => setShowConfig(false)}
        />
      )}
    </Layout>
  );
}
