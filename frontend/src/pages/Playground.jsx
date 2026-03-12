import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Loader2, ChevronRight, ChevronDown, Clock, Route, Database, Zap } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Layout from '../components/Layout';
import { getProject, sendMessage } from '../services/api';
import { usePlayground } from '../context/PlaygroundContext';

const Playground = () => {
    const { projectId } = useParams();
    const { getState, setMessages, setLastDebug } = usePlayground();
    const { messages, lastDebug } = getState(projectId);

    const [project, setProject] = useState(null);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [debugOpen, setDebugOpen] = useState(true);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        getProject(projectId).then(setProject).catch(() => { });
    }, [projectId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;
        const userMsg = input;
        setInput('');
        setMessages(projectId, prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            // Build history from existing messages (role + content only)
            const history = messages.map(m => ({ role: m.role, content: m.content }));
            const result = await sendMessage(projectId, userMsg, history);
            const debug = {
                agent_path: result.agent_path,
                used_rag: result.used_rag,
                latency: result.latency,
                retrieved_chunks: result.retrieved_chunks,
            };
            setMessages(projectId, prev => [...prev, {
                role: 'assistant',
                content: result.answer,
                debug,
            }]);
            setLastDebug(projectId, debug);
        } catch (err) {
            setMessages(projectId, prev => [...prev, {
                role: 'assistant',
                content: '⚠️ Error: ' + (err.response?.data?.detail || 'Backend unavailable.'),
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout projectId={projectId} projectName={project?.name}>
            <div className="flex h-full">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col h-full">
                    {/* Header */}
                    <div className="h-14 border-b border-gray-200 dark:border-slate-800 flex items-center px-5 justify-between bg-white/80 dark:bg-slate-900/80 backdrop-blur-md transition-colors">
                        <div className="flex items-center gap-2">
                            <Zap size={16} className="text-saffron-400" />
                            <span className="font-semibold text-gray-800 dark:text-slate-200">Playground</span>
                            <span className="text-xs text-gray-400 dark:text-slate-500">· {project?.name}</span>
                        </div>
                        <button
                            onClick={() => setDebugOpen(!debugOpen)}
                            className="text-xs flex items-center gap-1 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 bg-gray-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg transition-all"
                        >
                            Debug Panel
                            {debugOpen ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                        </button>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto px-4">
                        <div className="max-w-3xl mx-auto pt-6 pb-32">
                            {messages.length === 0 && !loading && (
                                <div className="flex flex-col items-center justify-center mt-20 text-center px-6">
                                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-saffron-500/20 to-orange-500/20 border border-saffron-500/20 flex items-center justify-center mb-4">
                                        <Zap size={28} className="text-saffron-400" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-gray-800 dark:text-slate-200 mb-2">Chat Playground</h2>
                                    <p className="text-gray-500 dark:text-slate-500 max-w-md">
                                        Test your agent pipeline here. Responses include debug info showing agent path, latency, and retrieved chunks.
                                    </p>
                                </div>
                            )}

                            {messages.map((msg, idx) => (
                                <div key={idx} className={`flex mb-5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${msg.role === 'user'
                                        ? 'bg-gradient-to-br from-saffron-400 to-orange-500 text-white rounded-tr-none'
                                        : 'bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 text-gray-800 dark:text-slate-200 rounded-tl-none shadow-sm dark:shadow-none'
                                        }`}>
                                        {msg.role === 'assistant' ? (
                                            <div className="prose dark:prose-invert prose-sm max-w-none prose-p:leading-relaxed">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                            </div>
                                        ) : msg.content}
                                    </div>
                                </div>
                            ))}

                            {loading && (
                                <div className="flex items-center gap-3 px-4">
                                    <div className="flex gap-1">
                                        <div className="w-1.5 h-1.5 bg-saffron-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <div className="w-1.5 h-1.5 bg-saffron-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <div className="w-1.5 h-1.5 bg-saffron-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    </div>

                    {/* Input */}
                    <div className="absolute bottom-0 left-64 z-20 pt-8 pb-5 px-4 bg-gradient-to-t from-gray-50 via-gray-50/80 dark:from-slate-950 dark:via-slate-950/80 to-transparent transition-colors" style={{ right: debugOpen ? '320px' : '0' }}>
                        <div className="max-w-3xl mx-auto">
                            <div className="flex items-center bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 overflow-hidden shadow-xl dark:shadow-2xl transition-colors">
                                <input
                                    type="text"
                                    className="flex-1 bg-transparent border-none py-3.5 px-5 text-gray-800 dark:text-slate-200 placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none"
                                    placeholder="Type a message..."
                                    value={input}
                                    onChange={e => setInput(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                                    disabled={loading}
                                />
                                <button
                                    onClick={handleSend}
                                    disabled={!input.trim() || loading}
                                    className="p-3 mr-1.5 bg-saffron-500 hover:bg-saffron-400 disabled:opacity-0 text-white rounded-lg transition-all"
                                >
                                    {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Debug Panel */}
                {debugOpen && (
                    <div className="w-80 border-l border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col overflow-hidden transition-colors">
                        <div className="p-4 border-b border-gray-200 dark:border-slate-800">
                            <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300">Debug Info</h3>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4">
                            {lastDebug ? (
                                <div className="space-y-4">
                                    {/* Agent Path */}
                                    <div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <Route size={14} className="text-indigo-500 dark:text-indigo-400" />
                                            <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Agent Path</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1.5">
                                            {lastDebug.agent_path.map((agent, i) => (
                                                <React.Fragment key={i}>
                                                    <span className="px-2.5 py-1 bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-600 dark:text-indigo-300 rounded-lg text-xs font-medium">
                                                        {agent}
                                                    </span>
                                                    {i < lastDebug.agent_path.length - 1 && (
                                                        <ChevronRight size={12} className="text-gray-300 dark:text-slate-600 self-center" />
                                                    )}
                                                </React.Fragment>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Latency */}
                                    <div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <Clock size={14} className="text-emerald-500 dark:text-emerald-400" />
                                            <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Latency</span>
                                        </div>
                                        <p className="text-lg font-semibold text-emerald-500 dark:text-emerald-400">{lastDebug.latency}s</p>
                                    </div>

                                    {/* RAG Used */}
                                    <div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <Database size={14} className="text-purple-500 dark:text-purple-400" />
                                            <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Used RAG</span>
                                        </div>
                                        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${lastDebug.used_rag
                                            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'
                                            : 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-500 border border-gray-200 dark:border-slate-700'
                                            }`}>
                                            {lastDebug.used_rag ? 'Yes' : 'No'}
                                        </span>
                                    </div>

                                    {/* Retrieved Chunks */}
                                    {lastDebug.retrieved_chunks.length > 0 && (
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <Database size={14} className="text-amber-500 dark:text-amber-400" />
                                                <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                                                    Retrieved Chunks ({lastDebug.retrieved_chunks.length})
                                                </span>
                                            </div>
                                            <div className="space-y-2 max-h-60 overflow-y-auto">
                                                {lastDebug.retrieved_chunks.map((chunk, i) => (
                                                    <div key={i} className="bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg p-3">
                                                        <p className="text-xs text-gray-600 dark:text-slate-300 line-clamp-4 leading-relaxed">
                                                            {typeof chunk === 'string' ? chunk : JSON.stringify(chunk)}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="text-center py-10">
                                    <p className="text-gray-400 dark:text-slate-600 text-sm">Send a message to see debug info.</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default Playground;
