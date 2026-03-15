import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { scholarshipsAPI, applicationsAPI, llmAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import { Search, Calendar, ExternalLink, Sparkles, X, CheckCircle, AlertTriangle, Lightbulb } from 'lucide-react';

export default function Scholarships() {
  const [scholarships, setScholarships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [applying, setApplying] = useState(null);
  const [llmAvailable, setLlmAvailable] = useState(false);
  const [matchExplanation, setMatchExplanation] = useState(null);
  const [loadingMatch, setLoadingMatch] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadScholarships();
    checkLlmStatus();
  }, []);

  const checkLlmStatus = async () => {
    try {
      const response = await llmAPI.status();
      setLlmAvailable(response.data.available);
    } catch {
      setLlmAvailable(false);
    }
  };

  const loadScholarships = async (searchTerm = '') => {
    setLoading(true);
    try {
      const params = searchTerm ? { search: searchTerm } : {};
      const response = await scholarshipsAPI.list(params);
      setScholarships(response.data.scholarships);
    } catch (err) {
      console.error('Failed to load scholarships', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadScholarships(search);
  };

  const handleStartApplication = async (scholarshipId) => {
    setApplying(scholarshipId);
    try {
      const response = await applicationsAPI.create(scholarshipId);
      navigate(`/applications/${response.data.id}`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start application');
    } finally {
      setApplying(null);
    }
  };

  const handleGetMatchExplanation = async (scholarship) => {
    setLoadingMatch(scholarship.id);
    try {
      const response = await llmAPI.getMatchExplanation(scholarship.id);
      if (response.data.success) {
        setMatchExplanation({
          scholarship,
          ...response.data.explanation,
        });
      } else {
        alert(response.data.error || 'Failed to get match explanation');
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to get match explanation. Make sure your profile is filled out.');
    } finally {
      setLoadingMatch(null);
    }
  };

  const formatDeadline = (deadline) => {
    if (!deadline) return { text: 'No deadline', color: 'text-gray-600' };
    const date = new Date(deadline);
    const days = Math.ceil((date - new Date()) / (1000 * 60 * 60 * 24));
    const formatted = date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

    if (days < 0) return { text: `Closed ${formatted}`, color: 'text-red-600' };
    if (days <= 7) return { text: `${formatted} (${days} days)`, color: 'text-red-600' };
    if (days <= 30) return { text: `${formatted} (${days} days)`, color: 'text-yellow-600' };
    return { text: formatted, color: 'text-gray-600' };
  };

  const formatAmount = (scholarship) => {
    if (scholarship.award_amount) {
      return `$${scholarship.award_amount.toLocaleString()}`;
    }
    if (scholarship.award_amount_min && scholarship.award_amount_max) {
      return `$${scholarship.award_amount_min.toLocaleString()} - $${scholarship.award_amount_max.toLocaleString()}`;
    }
    return 'Varies';
  };

  const getMatchScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Find Scholarships</h1>
          {llmAvailable && (
            <span className="flex items-center text-sm text-green-600">
              <Sparkles className="w-4 h-4 mr-1" />
              AI Match Analysis Available
            </span>
          )}
        </div>

        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="flex-1">
            <Input
              placeholder="Search scholarships by name, description, or provider..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button type="submit">
            <Search className="w-4 h-4 mr-2" />
            Search
          </Button>
        </form>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        ) : scholarships.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <Search className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500">
                {search ? 'No scholarships found matching your search.' : 'No scholarships available.'}
              </p>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {scholarships.map((scholarship) => {
              const deadline = formatDeadline(scholarship.deadline);
              return (
                <Card key={scholarship.id}>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">{scholarship.name}</h3>
                          {scholarship.provider && (
                            <p className="text-sm text-gray-500">{scholarship.provider}</p>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-green-600">
                            {formatAmount(scholarship)}
                          </p>
                          {scholarship.num_awards > 1 && (
                            <p className="text-xs text-gray-500">
                              {scholarship.num_awards} awards
                            </p>
                          )}
                        </div>
                      </div>

                      {scholarship.description && (
                        <p className="mt-2 text-gray-600 line-clamp-2">{scholarship.description}</p>
                      )}

                      <div className="mt-4 flex items-center space-x-6 text-sm">
                        <span className={`flex items-center ${deadline.color}`}>
                          <Calendar className="w-4 h-4 mr-1" />
                          {deadline.text}
                        </span>
                        {scholarship.renewable && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-800 rounded text-xs">
                            Renewable
                          </span>
                        )}
                        {scholarship.url && (
                          <a
                            href={scholarship.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center text-indigo-600 hover:text-indigo-800"
                          >
                            <ExternalLink className="w-4 h-4 mr-1" />
                            Website
                          </a>
                        )}
                      </div>
                    </div>

                    <div className="ml-6 flex flex-col space-y-2">
                      {llmAvailable && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleGetMatchExplanation(scholarship)}
                          loading={loadingMatch === scholarship.id}
                        >
                          <Sparkles className="w-4 h-4 mr-1" />
                          See My Match
                        </Button>
                      )}
                      <Button
                        onClick={() => handleStartApplication(scholarship.id)}
                        loading={applying === scholarship.id}
                        disabled={deadline.color === 'text-red-600' && deadline.text.includes('Closed')}
                      >
                        Start Application
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Match Explanation Modal */}
      {matchExplanation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Match Analysis</h2>
                  <p className="text-gray-500">{matchExplanation.scholarship.name}</p>
                </div>
                <button
                  onClick={() => setMatchExplanation(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Match Score */}
              <div className="flex items-center mb-6">
                <div className={`px-4 py-2 rounded-full text-2xl font-bold ${getMatchScoreColor(matchExplanation.match_score)}`}>
                  {matchExplanation.match_score}%
                </div>
                <p className="ml-4 text-gray-600">{matchExplanation.summary}</p>
              </div>

              {/* Strengths */}
              {matchExplanation.strengths?.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-semibold text-gray-900 flex items-center mb-2">
                    <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                    Your Strengths
                  </h3>
                  <ul className="space-y-1 ml-7">
                    {matchExplanation.strengths.map((strength, i) => (
                      <li key={i} className="text-gray-600">{strength}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Considerations */}
              {matchExplanation.considerations?.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-semibold text-gray-900 flex items-center mb-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2" />
                    Things to Consider
                  </h3>
                  <ul className="space-y-1 ml-7">
                    {matchExplanation.considerations.map((consideration, i) => (
                      <li key={i} className="text-gray-600">{consideration}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tips */}
              {matchExplanation.tips?.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-semibold text-gray-900 flex items-center mb-2">
                    <Lightbulb className="w-5 h-5 text-indigo-600 mr-2" />
                    Application Tips
                  </h3>
                  <ul className="space-y-1 ml-7">
                    {matchExplanation.tips.map((tip, i) => (
                      <li key={i} className="text-gray-600">{tip}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-6 flex justify-end space-x-3">
                <Button variant="secondary" onClick={() => setMatchExplanation(null)}>
                  Close
                </Button>
                <Button onClick={() => {
                  setMatchExplanation(null);
                  handleStartApplication(matchExplanation.scholarship.id);
                }}>
                  Start Application
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
