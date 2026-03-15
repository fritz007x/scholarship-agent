import { useState, useEffect, useRef } from 'react';
import { agentAPI } from '../services/api';
import Layout from '../components/layout/Layout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import {
  Send,
  Bot,
  User,
  Sparkles,
  History,
  X,
  Search,
  GraduationCap,
  FileText,
  ChevronRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

function Message({ message, isUser }) {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      >
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-indigo-600 ml-2' : 'bg-gray-200 mr-2'
          }`}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-gray-600" />
          )}
        </div>
        <div
          className={`px-4 py-2 rounded-lg ${
            isUser
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
          {message.suggestedActions && message.suggestedActions.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {message.suggestedActions.map((action, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-1 bg-white/20 rounded cursor-pointer hover:bg-white/30"
                >
                  {action}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function QuickAction({ icon: Icon, label, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-start p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left w-full"
    >
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center mr-3">
        <Icon className="w-5 h-5 text-indigo-600" />
      </div>
      <div>
        <div className="font-medium text-gray-900">{label}</div>
        <div className="text-sm text-gray-500">{description}</div>
      </div>
      <ChevronRight className="w-5 h-5 text-gray-400 ml-auto self-center" />
    </button>
  );
}

function SessionItem({ session, onClick, onArchive }) {
  return (
    <div className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg cursor-pointer">
      <div onClick={onClick} className="flex-1">
        <div className="text-sm font-medium text-gray-900">
          {session.total_messages} messages
        </div>
        <div className="text-xs text-gray-500">
          {new Date(session.last_activity).toLocaleDateString()}
        </div>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onArchive(session.session_id);
        }}
        className="p-1 text-gray-400 hover:text-red-500"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export default function AgentChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [agentAvailable, setAgentAvailable] = useState(false);
  const [checking, setChecking] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    checkAgentStatus();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const checkAgentStatus = async () => {
    setChecking(true);
    try {
      const response = await agentAPI.status();
      setAgentAvailable(response.data.available);
    } catch {
      setAgentAvailable(false);
    } finally {
      setChecking(false);
    }
  };

  const loadSessions = async () => {
    try {
      const response = await agentAPI.listSessions();
      setSessions(response.data.sessions || []);
    } catch (err) {
      console.error('Failed to load sessions', err);
    }
  };

  const handleShowHistory = () => {
    setShowHistory(true);
    loadSessions();
  };

  const handleLoadSession = async (session) => {
    try {
      const response = await agentAPI.getSession(session.session_id);
      setSessionId(session.session_id);

      // Convert session messages to display format
      const displayMessages = (response.data.messages || [])
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      setMessages(displayMessages);
      setShowHistory(false);
    } catch (err) {
      console.error('Failed to load session', err);
    }
  };

  const handleArchiveSession = async (sid) => {
    try {
      await agentAPI.archiveSession(sid);
      setSessions(sessions.filter((s) => s.session_id !== sid));
      if (sessionId === sid) {
        setSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to archive session', err);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);

    // Add user message to display
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await agentAPI.chat(userMessage, sessionId);

      // Update session ID
      if (response.data.session_id) {
        setSessionId(response.data.session_id);
      }

      // Add assistant response
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.data.message,
          suggestedActions: response.data.suggested_actions,
        },
      ]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message');
      // Remove the user message if failed
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleQuickAction = (message) => {
    setInput(message);
    inputRef.current?.focus();
  };

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setError(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (checking) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      </Layout>
    );
  }

  if (!agentAvailable) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <AlertCircle className="w-16 h-16 mx-auto text-yellow-500 mb-4" />
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                Agent Not Available
              </h2>
              <p className="text-gray-600 mb-4">
                The AI agent requires a Google API key to be configured.
                Please contact your administrator.
              </p>
              <Button onClick={checkAgentStatus}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Check Again
              </Button>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto h-[calc(100vh-180px)] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center mr-3">
              <Sparkles className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Scholarship Assistant
              </h1>
              <p className="text-sm text-gray-500">
                AI-powered help for your scholarship search
              </p>
            </div>
          </div>
          <div className="flex space-x-2">
            <Button variant="secondary" size="sm" onClick={handleNewChat}>
              New Chat
            </Button>
            <Button variant="secondary" size="sm" onClick={handleShowHistory}>
              <History className="w-4 h-4 mr-1" />
              History
            </Button>
          </div>
        </div>

        {/* Chat Container */}
        <Card className="flex-1 flex flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Bot className="w-16 h-16 text-gray-300 mb-4" />
                <h2 className="text-lg font-medium text-gray-900 mb-2">
                  How can I help you today?
                </h2>
                <p className="text-gray-500 mb-6 text-center max-w-md">
                  I can help you find scholarships, evaluate your match, manage
                  applications, and more.
                </p>

                {/* Quick Actions */}
                <div className="w-full max-w-md space-y-2">
                  <QuickAction
                    icon={Search}
                    label="Find Scholarships"
                    description="Search for scholarships that match your profile"
                    onClick={() =>
                      handleQuickAction(
                        'Find scholarships that match my profile'
                      )
                    }
                  />
                  <QuickAction
                    icon={GraduationCap}
                    label="Get Recommendations"
                    description="Get personalized scholarship recommendations"
                    onClick={() =>
                      handleQuickAction(
                        'What scholarships do you recommend for me?'
                      )
                    }
                  />
                  <QuickAction
                    icon={FileText}
                    label="Application Help"
                    description="Get help with your scholarship applications"
                    onClick={() =>
                      handleQuickAction(
                        'Help me with my scholarship applications'
                      )
                    }
                  />
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <Message
                    key={i}
                    message={msg}
                    isUser={msg.role === 'user'}
                  />
                ))}
                {loading && (
                  <div className="flex justify-start mb-4">
                    <div className="flex">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mr-2">
                        <Bot className="w-5 h-5 text-gray-600" />
                      </div>
                      <div className="px-4 py-2 rounded-lg bg-gray-100">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div
                            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                            style={{ animationDelay: '0.1s' }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                            style={{ animationDelay: '0.2s' }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="mx-4 mb-2 p-2 bg-red-50 text-red-600 text-sm rounded-lg flex items-center">
              <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t">
            <div className="flex space-x-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me about scholarships..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
                rows={1}
                disabled={loading}
              />
              <Button onClick={handleSend} disabled={!input.trim() || loading}>
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </Card>

        {/* History Sidebar */}
        {showHistory && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-end">
            <div className="w-80 bg-white h-full shadow-xl">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="font-bold text-gray-900">Chat History</h2>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 overflow-y-auto h-[calc(100%-60px)]">
                {sessions.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">
                    No previous conversations
                  </p>
                ) : (
                  <div className="space-y-2">
                    {sessions.map((session) => (
                      <SessionItem
                        key={session.session_id}
                        session={session}
                        onClick={() => handleLoadSession(session)}
                        onArchive={handleArchiveSession}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
