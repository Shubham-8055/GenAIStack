import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Save, Loader2, RotateCcw, AlertCircle, CheckCircle, Database, Plus, Trash2, Upload, Plug, Download } from 'lucide-react';
import Layout from '../components/Layout';
import { getProject, getAgentConfig, updateAgentConfig, seedTransactions, importCSV, testExternalConnection } from '../services/api';

const ProjectSettings = () => {
    const { projectId } = useParams();
    const [project, setProject] = useState(null);
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [seeding, setSeeding] = useState(false);
    const [importing, setImporting] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState(null);
    const [downloading, setDownloading] = useState(false);
    const [toast, setToast] = useState(null);

    useEffect(() => { loadData(); }, [projectId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [proj, cfg] = await Promise.all([getProject(projectId), getAgentConfig(projectId)]);
            setProject(proj); setConfig(cfg);
        } catch { showToast('Failed to load settings', 'error'); }
        finally { setLoading(false); }
    };

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const updated = await updateAgentConfig(projectId, {
                guardrail_prompt: config.guardrail_prompt,
                orchestrator_prompt: config.orchestrator_prompt,
                rag_prompt: config.rag_prompt,
                formatter_prompt: config.formatter_prompt,
                enable_guardrail: config.enable_guardrail,
                enable_rag: config.enable_rag,
                enable_formatter: config.enable_formatter,
                model_name: config.model_name,
                temperature: config.temperature,
                top_k: config.top_k,
                chunk_size: config.chunk_size,
                chunk_overlap: config.chunk_overlap,
                enable_tool_agent: config.enable_tool_agent,
                tool_agent_prompt: config.tool_agent_prompt,
                tool_agent_fields: config.tool_agent_fields || [],
                tool_data_source: config.tool_data_source || 'internal',
                external_db_connection: config.external_db_connection || '',
                external_db_table: config.external_db_table || '',
                external_db_columns: config.external_db_columns || {},
            });
            setConfig(updated);
            showToast('Settings saved successfully!');
        } catch { showToast('Failed to save settings', 'error'); }
        finally { setSaving(false); }
    };

    const updateField = (field, value) => setConfig(prev => ({ ...prev, [field]: value }));

    if (loading) {
        return (
            <Layout projectId={projectId} projectName={project?.name}>
                <div className="flex justify-center items-center h-full">
                    <Loader2 size={32} className="animate-spin text-saffron-500" />
                </div>
            </Layout>
        );
    }

    return (
        <Layout projectId={projectId} projectName={project?.name}>
            <div className="p-8 max-w-4xl mx-auto">
                {/* Toast */}
                {toast && (
                    <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg border ${toast.type === 'error'
                        ? 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400'
                        : 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                        }`}>
                        {toast.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
                        <span className="text-sm">{toast.message}</span>
                    </div>
                )}

                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Agent Settings</h1>
                        <p className="text-gray-500 dark:text-slate-500 mt-1">Configure prompts, toggles, and model for <span className="text-gray-700 dark:text-slate-300">{project?.name}</span></p>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={loadData} className="p-2.5 text-gray-400 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 rounded-lg transition-all" title="Reset">
                            <RotateCcw size={16} />
                        </button>
                        <button onClick={async () => {
                            setDownloading(true);
                            try {
                                const resp = await fetch(`http://localhost:8000/api/v1/projects/${projectId}/export`);
                                if (!resp.ok) throw new Error('Export failed');
                                const blob = await resp.blob();
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = (project?.name || 'project').toLowerCase().replace(/\s+/g, '_') + '_chatbot.zip';
                                a.click();
                                URL.revokeObjectURL(url);
                                showToast('Project downloaded!');
                            } catch { showToast('Download failed', 'error'); }
                            finally { setDownloading(false); }
                        }} disabled={downloading}
                            className="flex items-center gap-2 bg-violet-500 hover:bg-violet-600 text-white px-4 py-2.5 rounded-xl font-medium text-sm transition-all disabled:opacity-50"
                            title="Download standalone chatbot project">
                            {downloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                            Download Project
                        </button>
                        <button onClick={handleSave} disabled={saving}
                            className="flex items-center gap-2 bg-gradient-to-r from-saffron-400 to-orange-500 text-white px-5 py-2.5 rounded-xl font-medium shadow-lg shadow-saffron-500/20 hover:shadow-saffron-500/40 transition-all disabled:opacity-50">
                            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                            Save Changes
                        </button>
                    </div>
                </div>

                {/* Agent Toggles */}
                <section className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 mb-6 shadow-sm dark:shadow-none transition-colors">
                    <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200 mb-4">Agent Toggles</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {[
                            { key: 'enable_guardrail', label: 'Guardrails Agent', desc: 'Safety filter for queries' },
                            { key: 'enable_rag', label: 'RAG Agent', desc: 'Knowledge base retrieval' },
                            { key: 'enable_formatter', label: 'Formatter Agent', desc: 'Output formatting' },
                            { key: 'enable_tool_agent', label: 'Tool Call Agent', desc: 'Transaction lookup via SQL' },
                        ].map(toggle => (
                            <div key={toggle.key} className="flex items-center justify-between bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700/50">
                                <div>
                                    <p className="text-sm font-medium text-gray-700 dark:text-slate-200">{toggle.label}</p>
                                    <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">{toggle.desc}</p>
                                </div>
                                <button onClick={() => updateField(toggle.key, !config[toggle.key])}
                                    className={`relative w-11 h-6 rounded-full transition-colors ${config[toggle.key] ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-slate-600'}`}>
                                    <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${config[toggle.key] ? 'translate-x-5' : 'translate-x-0'}`} />
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Chunking Settings */}
                <section className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 mb-6 shadow-sm dark:shadow-none transition-colors">
                    <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200 mb-1">Chunking Settings</h2>
                    <p className="text-xs text-gray-400 dark:text-slate-500 mb-4">Controls how uploaded documents are split into chunks for retrieval. Changes apply to newly uploaded documents only.</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm text-gray-500 dark:text-slate-400 mb-1.5">Top K (RAG chunks)</label>
                            <input type="number" min="1" max="20" value={config.top_k === undefined ? '' : config.top_k}
                                onChange={e => updateField('top_k', e.target.value === '' ? '' : Number(e.target.value))}
                                className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                            <p className="text-[10px] text-gray-400 dark:text-slate-600 mt-1">Number of chunks to retrieve during RAG</p>
                        </div>
                        <div>
                            <label className="block text-sm text-gray-500 dark:text-slate-400 mb-1.5">Chunk Size (characters)</label>
                            <input type="number" min="0" step="1" value={config.chunk_size === undefined ? '' : config.chunk_size}
                                onChange={e => updateField('chunk_size', e.target.value === '' ? '' : Number(e.target.value))}
                                className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                            <p className="text-[10px] text-gray-400 dark:text-slate-600 mt-1">Larger chunks = more context per retrieval, smaller = more precise matching</p>
                        </div>
                        <div>
                            <label className="block text-sm text-gray-500 dark:text-slate-400 mb-1.5">Chunk Overlap (characters)</label>
                            <input type="number" min="0" step="1" value={config.chunk_overlap === undefined ? '' : config.chunk_overlap}
                                onChange={e => updateField('chunk_overlap', e.target.value === '' ? '' : Number(e.target.value))}
                                className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                            <p className="text-[10px] text-gray-400 dark:text-slate-600 mt-1">Overlap prevents information loss at chunk boundaries</p>
                        </div>
                    </div>
                </section>

                {/* Data Source Config */}
                {config.enable_tool_agent && (
                    <section className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 mb-6 shadow-sm dark:shadow-none transition-colors">
                        <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200 mb-1">Data Source</h2>
                        <p className="text-xs text-gray-400 dark:text-slate-500 mb-4">Choose where the tool agent queries transaction data from.</p>

                        {/* Source Toggle */}
                        <div className="flex gap-3 mb-5">
                            {['internal', 'external'].map(src => (
                                <button key={src} onClick={() => updateField('tool_data_source', src)}
                                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${(config.tool_data_source || 'internal') === src
                                        ? 'bg-saffron-500 text-white shadow-md'
                                        : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-700'
                                        }`}>
                                    {src === 'internal' ? '📦 Internal (Seed / CSV)' : '🔗 External Database'}
                                </button>
                            ))}
                        </div>

                        {/* Internal: Seed + CSV */}
                        {(config.tool_data_source || 'internal') === 'internal' && (
                            <div className="space-y-4">
                                <div className="flex gap-3 flex-wrap">
                                    <button onClick={async () => {
                                        setSeeding(true);
                                        try {
                                            const res = await seedTransactions(projectId);
                                            showToast(`Seeded ${res.count} sample transactions!`);
                                        } catch { showToast('Failed to seed transactions', 'error'); }
                                        finally { setSeeding(false); }
                                    }}
                                        disabled={seeding}
                                        className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2.5 rounded-xl font-medium text-sm transition-all disabled:opacity-50">
                                        {seeding ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
                                        Seed Sample Data
                                    </button>

                                    <label className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2.5 rounded-xl font-medium text-sm transition-all cursor-pointer">
                                        {importing ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                                        Import CSV
                                        <input type="file" accept=".csv" className="hidden" onChange={async (e) => {
                                            const file = e.target.files[0];
                                            if (!file) return;
                                            setImporting(true);
                                            try {
                                                const res = await importCSV(projectId, file);
                                                showToast(`Imported ${res.rows_imported} transactions!${res.total_errors > 0 ? ` (${res.total_errors} errors)` : ''}`);
                                            } catch { showToast('CSV import failed', 'error'); }
                                            finally { setImporting(false); e.target.value = ''; }
                                        }} />
                                    </label>
                                </div>
                                <p className="text-[11px] text-gray-400 dark:text-slate-600">CSV columns: date, amount, status, txn_type, bank_name, rrn, remarks, plus your custom field names</p>
                            </div>
                        )}

                        {/* External DB Config */}
                        {(config.tool_data_source || 'internal') === 'external' && (
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 mb-1">Connection String</label>
                                    <input value={config.external_db_connection || ''} placeholder="postgresql://user:pass@host:5432/dbname"
                                        onChange={e => updateField('external_db_connection', e.target.value)}
                                        className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 mb-1">Table Name</label>
                                        <input value={config.external_db_table || ''} placeholder="transactions"
                                            onChange={e => updateField('external_db_table', e.target.value)}
                                            className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                                    </div>
                                    <div>
                                        <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 mb-1">Date Column</label>
                                        <input value={(config.external_db_columns || {}).date_col || ''} placeholder="txn_date"
                                            onChange={e => updateField('external_db_columns', { ...(config.external_db_columns || {}), date_col: e.target.value })}
                                            className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                                    </div>
                                    <div>
                                        <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 mb-1">Amount Column</label>
                                        <input value={(config.external_db_columns || {}).amount_col || ''} placeholder="amount"
                                            onChange={e => updateField('external_db_columns', { ...(config.external_db_columns || {}), amount_col: e.target.value })}
                                            className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                                    </div>
                                    <div>
                                        <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 mb-1">Status Column</label>
                                        <input value={(config.external_db_columns || {}).status_col || ''} placeholder="status"
                                            onChange={e => updateField('external_db_columns', { ...(config.external_db_columns || {}), status_col: e.target.value })}
                                            className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-saffron-500/50" />
                                    </div>
                                </div>
                                <p className="text-[11px] text-gray-400 dark:text-slate-600">For custom lookup fields, the column name should match the field name, or add a mapping above.</p>

                                {/* Test Connection */}
                                <div className="flex items-center gap-3 flex-wrap">
                                    <button onClick={async () => {
                                        setTesting(true); setTestResult(null);
                                        try {
                                            const res = await testExternalConnection(projectId, config.external_db_connection, config.external_db_table);
                                            setTestResult(res);
                                        } catch { setTestResult({ success: false, message: 'Request failed' }); }
                                        finally { setTesting(false); }
                                    }}
                                        disabled={testing || !config.external_db_connection || !config.external_db_table}
                                        className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2.5 rounded-xl font-medium text-sm transition-all disabled:opacity-50">
                                        {testing ? <Loader2 size={16} className="animate-spin" /> : <Plug size={16} />}
                                        Test Connection
                                    </button>
                                    {testResult && (
                                        <span className={`text-sm font-medium ${testResult.success ? 'text-green-500' : 'text-red-400'}`}>
                                            {testResult.success ? '✅' : '❌'} {testResult.message}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}
                    </section>
                )}



                {/* Prompts */}
                <section className="space-y-6">
                    {[
                        { key: 'guardrail_prompt', label: 'Guardrail Prompt', rows: 8 },
                        { key: 'orchestrator_prompt', label: 'Orchestrator Prompt', rows: 12 },
                        { key: 'rag_prompt', label: 'RAG Synthesis Prompt', rows: 6 },
                        { key: 'formatter_prompt', label: 'Formatter Prompt', rows: 6 },
                        { key: 'tool_agent_prompt', label: 'Tool Agent Prompt (Parameter Extractor)', rows: 8 },
                    ].map(prompt => (
                        <div key={prompt.key} className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm dark:shadow-none transition-colors">
                            <label className="block text-base font-semibold text-gray-800 dark:text-slate-200 mb-3">{prompt.label}</label>
                            <textarea value={config[prompt.key]} onChange={e => updateField(prompt.key, e.target.value)} rows={prompt.rows}
                                className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-xl px-4 py-3 text-sm text-gray-800 dark:text-slate-200 font-mono leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-saffron-500/50 focus:border-saffron-500/50 transition-all" />
                        </div>
                    ))}
                </section>
            </div>
        </Layout>
    );
};

export default ProjectSettings;
