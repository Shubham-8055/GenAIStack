import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
    Loader2, Clock, Route, Database, ChevronDown, ChevronRight,
    Search, RefreshCw, Zap, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import { getProject, getQueryLogs } from '../services/api';

const LogEntry = ({ log, isExpanded, onToggle }) => {
    const agentPath = Array.isArray(log.agent_path) ? log.agent_path : [];
    const chunks = Array.isArray(log.retrieved_chunks) ? log.retrieved_chunks : [];

    return (
        <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl overflow-hidden hover:border-gray-300 dark:hover:border-slate-700 transition-all shadow-sm dark:shadow-none">
            {/* Summary row */}
            <button onClick={onToggle} className="w-full flex items-center gap-4 px-5 py-4 text-left">
                <div className="flex-shrink-0">
                    {isExpanded
                        ? <ChevronDown size={14} className="text-gray-400 dark:text-slate-500" />
                        : <ChevronRight size={14} className="text-gray-400 dark:text-slate-500" />
                    }
                </div>

                {/* Query */}
                <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 dark:text-slate-200 truncate font-medium">{log.query}</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">
                        {new Date(log.timestamp).toLocaleString()}
                    </p>
                </div>

                {/* Badges */}
                <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-xs text-gray-500 dark:text-slate-400">
                        <Clock size={10} /> {log.latency}s
                    </span>
                    <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${log.used_rag
                        ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20'
                        : 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-500 border-gray-200 dark:border-slate-700'
                        }`}>
                        {log.used_rag ? 'RAG' : 'Direct'}
                    </span>
                    <span className="flex items-center gap-1 px-2 py-1 bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-600 dark:text-indigo-300 rounded-lg text-xs">
                        <Route size={10} /> {agentPath.length}
                    </span>
                </div>
            </button>

            {/* Expanded detail */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="px-5 pb-5 pt-0 border-t border-gray-100 dark:border-slate-800/50 space-y-4">
                            {/* Agent Path */}
                            <div className="pt-4">
                                <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Agent Path</span>
                                <div className="flex flex-wrap items-center gap-1.5 mt-2">
                                    {agentPath.map((agent, i) => (
                                        <React.Fragment key={i}>
                                            <span className="px-2.5 py-1 bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-600 dark:text-indigo-300 rounded-lg text-xs font-medium">
                                                {agent}
                                            </span>
                                            {i < agentPath.length - 1 && <ChevronRight size={10} className="text-gray-300 dark:text-slate-600" />}
                                        </React.Fragment>
                                    ))}
                                </div>
                            </div>

                            {/* Answer */}
                            <div>
                                <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">Final Answer</span>
                                <div className="mt-2 bg-gray-50 dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700/50 rounded-xl p-4">
                                    <p className="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{log.final_answer}</p>
                                </div>
                            </div>

                            {/* Retrieved Chunks */}
                            {chunks.length > 0 && (
                                <div>
                                    <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                                        Retrieved Chunks ({chunks.length})
                                    </span>
                                    <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                                        {chunks.map((chunk, i) => (
                                            <div key={i} className="bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg p-3">
                                                <p className="text-xs text-gray-500 dark:text-slate-400 line-clamp-3 leading-relaxed">
                                                    {typeof chunk === 'string' ? chunk : JSON.stringify(chunk)}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Meta row */}
                            <div className="flex items-center gap-4 text-[10px] text-gray-400 dark:text-slate-600 pt-1">
                                <span>ID: {log.id?.slice(0, 8)}...</span>
                                <span>Latency: {log.latency}s</span>
                                <span>RAG: {log.used_rag ? 'Yes' : 'No'}</span>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const QueryLogs = () => {
    const { projectId } = useParams();
    const [project, setProject] = useState(null);
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState(null);
    const [search, setSearch] = useState('');
    const [filterRag, setFilterRag] = useState('all');

    useEffect(() => { loadData(); }, [projectId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [proj, logData] = await Promise.all([getProject(projectId), getQueryLogs(projectId, 100)]);
            setProject(proj); setLogs(logData);
        } catch (err) { console.error('Failed to load logs:', err); }
        finally { setLoading(false); }
    };

    const filteredLogs = logs.filter(log => {
        const matchesSearch = !search ||
            log.query?.toLowerCase().includes(search.toLowerCase()) ||
            log.final_answer?.toLowerCase().includes(search.toLowerCase());
        const matchesFilter = filterRag === 'all' ||
            (filterRag === 'rag' && log.used_rag) ||
            (filterRag === 'direct' && !log.used_rag);
        return matchesSearch && matchesFilter;
    });

    const totalQueries = logs.length;
    const ragQueries = logs.filter(l => l.used_rag).length;
    const avgLatency = logs.length > 0
        ? (logs.reduce((sum, l) => sum + (l.latency || 0), 0) / logs.length).toFixed(2) : '0.00';

    return (
        <Layout projectId={projectId} projectName={project?.name}>
            <div className="p-8 max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Query Logs</h1>
                        <p className="text-gray-500 dark:text-slate-500 mt-1">Inspect every query processed by <span className="text-gray-700 dark:text-slate-300">{project?.name}</span></p>
                    </div>
                    <button onClick={loadData}
                        className="flex items-center gap-2 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 px-4 py-2 rounded-lg transition-all text-sm">
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-none transition-colors">
                        <div className="flex items-center gap-2 mb-1">
                            <Zap size={14} className="text-saffron-400" />
                            <p className="text-xs text-gray-500 dark:text-slate-500 uppercase tracking-wider font-semibold">Total Queries</p>
                        </div>
                        <p className="text-2xl font-bold text-gray-900 dark:text-slate-100">{totalQueries}</p>
                    </div>
                    <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-none transition-colors">
                        <div className="flex items-center gap-2 mb-1">
                            <Database size={14} className="text-emerald-500 dark:text-emerald-400" />
                            <p className="text-xs text-gray-500 dark:text-slate-500 uppercase tracking-wider font-semibold">RAG Queries</p>
                        </div>
                        <p className="text-2xl font-bold text-emerald-500 dark:text-emerald-400">{ragQueries}</p>
                    </div>
                    <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-none transition-colors">
                        <div className="flex items-center gap-2 mb-1">
                            <Clock size={14} className="text-indigo-500 dark:text-indigo-400" />
                            <p className="text-xs text-gray-500 dark:text-slate-500 uppercase tracking-wider font-semibold">Avg Latency</p>
                        </div>
                        <p className="text-2xl font-bold text-indigo-500 dark:text-indigo-400">{avgLatency}s</p>
                    </div>
                </div>

                {/* Search & Filter Bar */}
                <div className="flex gap-3 mb-4">
                    <div className="flex-1 relative">
                        <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500" />
                        <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search queries or answers..."
                            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-gray-800 dark:text-slate-200 placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-saffron-500/30 transition-colors" />
                    </div>
                    <div className="flex items-center bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg overflow-hidden transition-colors">
                        {[
                            { value: 'all', label: 'All' },
                            { value: 'rag', label: 'RAG' },
                            { value: 'direct', label: 'Direct' },
                        ].map(opt => (
                            <button key={opt.value} onClick={() => setFilterRag(opt.value)}
                                className={`px-3 py-2.5 text-xs font-medium transition-colors ${filterRag === opt.value
                                    ? 'bg-saffron-500/10 text-saffron-500 dark:text-saffron-400'
                                    : 'text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300'
                                    }`}>
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Log List */}
                {loading ? (
                    <div className="flex justify-center py-20">
                        <Loader2 size={28} className="animate-spin text-saffron-500" />
                    </div>
                ) : filteredLogs.length === 0 ? (
                    <div className="text-center py-20">
                        <AlertCircle size={36} className="mx-auto text-gray-300 dark:text-slate-700 mb-3" />
                        <p className="text-gray-500 dark:text-slate-500">
                            {logs.length === 0 ? 'No queries logged yet. Use the Playground to send a query.' : 'No logs match your search.'}
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {filteredLogs.map(log => (
                            <LogEntry
                                key={log.id}
                                log={log}
                                isExpanded={expandedId === log.id}
                                onToggle={() => setExpandedId(expandedId === log.id ? null : log.id)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default QueryLogs;
