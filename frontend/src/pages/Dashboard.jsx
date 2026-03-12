import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, FolderOpen, Loader2, AlertCircle, Download, Upload } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import { getProjects, createProject, deleteProject, exportProject, importProject } from '../services/api';

const Dashboard = () => {
    const navigate = useNavigate();
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newDesc, setNewDesc] = useState('');
    const [creating, setCreating] = useState(false);
    const importRef = useRef(null);

    useEffect(() => { fetchProjects(); }, []);

    const fetchProjects = async () => {
        try {
            setLoading(true);
            const data = await getProjects();
            setProjects(data.projects || []);
            setError(null);
        } catch { setError('Failed to connect to backend. Is it running?'); }
        finally { setLoading(false); }
    };

    const handleCreate = async () => {
        if (!newName.trim()) return;
        setCreating(true);
        try {
            await createProject(newName.trim(), newDesc.trim());
            setNewName(''); setNewDesc(''); setShowCreate(false);
            fetchProjects();
        } catch (err) { setError(err.response?.data?.detail || 'Failed to create project.'); }
        finally { setCreating(false); }
    };

    const handleDelete = async (e, id) => {
        e.stopPropagation();
        if (!confirm('Delete this project and all related data?')) return;
        try { await deleteProject(id); fetchProjects(); }
        catch { setError('Failed to delete project.'); }
    };

    const handleExport = async (e, id) => {
        e.stopPropagation();
        try { await exportProject(id); }
        catch { setError('Failed to export project.'); }
    };

    const handleImport = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try { await importProject(file); fetchProjects(); }
        catch (err) { setError(err.response?.data?.detail || 'Failed to import project.'); }
        e.target.value = '';
    };

    return (
        <Layout>
            <div className="p-8 max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-slate-100">Dashboard</h1>
                        <p className="text-gray-500 dark:text-slate-500 mt-1">Manage your GenAI projects</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <input ref={importRef} type="file" accept=".zip,.json" onChange={handleImport} className="hidden" />
                        <button
                            onClick={() => importRef.current?.click()}
                            className="flex items-center gap-2 text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
                            title="Import project from ZIP or JSON"
                        >
                            <Upload size={16} /> Import
                        </button>
                        <button
                            onClick={() => setShowCreate(!showCreate)}
                            className="flex items-center gap-2 bg-gradient-to-r from-saffron-400 to-orange-500 text-white px-5 py-2.5 rounded-xl font-medium shadow-lg shadow-saffron-500/20 hover:shadow-saffron-500/40 transition-all hover:scale-[1.02]"
                        >
                            <Plus size={18} /> New Project
                        </button>
                    </div>
                </div>

                {/* Error */}
                {error && (
                    <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400 p-4 rounded-xl mb-6 flex items-center gap-3">
                        <AlertCircle size={18} />
                        <span className="text-sm">{error}</span>
                        <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">✕</button>
                    </div>
                )}

                {/* Create Form */}
                <AnimatePresence>
                    {showCreate && (
                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden mb-6">
                            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm dark:shadow-none">
                                <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-200 mb-4">Create New Project</h3>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm text-gray-500 dark:text-slate-400 mb-1.5">Project Name *</label>
                                        <input type="text" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g., Finance Chatbot"
                                            className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-800 dark:text-slate-200 placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-saffron-500/50 focus:border-saffron-500/50 transition-all"
                                            onKeyDown={e => e.key === 'Enter' && handleCreate()} autoFocus />
                                    </div>
                                    <div>
                                        <label className="block text-sm text-gray-500 dark:text-slate-400 mb-1.5">Description</label>
                                        <input type="text" value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Optional description..."
                                            className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-800 dark:text-slate-200 placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-saffron-500/50 focus:border-saffron-500/50 transition-all" />
                                    </div>
                                    <div className="flex gap-3 pt-2">
                                        <button onClick={handleCreate} disabled={!newName.trim() || creating}
                                            className="bg-saffron-500 hover:bg-saffron-400 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium transition-all flex items-center gap-2">
                                            {creating && <Loader2 size={16} className="animate-spin" />} Create
                                        </button>
                                        <button onClick={() => setShowCreate(false)} className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 px-4 py-2 rounded-lg transition-colors">Cancel</button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Loading */}
                {loading && (
                    <div className="flex justify-center items-center py-20">
                        <Loader2 size={32} className="animate-spin text-saffron-500" />
                    </div>
                )}

                {/* Empty */}
                {!loading && projects.length === 0 && (
                    <div className="text-center py-20">
                        <FolderOpen size={48} className="mx-auto text-gray-300 dark:text-slate-700 mb-4" />
                        <p className="text-gray-500 dark:text-slate-500 text-lg">No projects yet</p>
                        <p className="text-gray-400 dark:text-slate-600 text-sm mt-1">Create your first project or import one from a ZIP.</p>
                    </div>
                )}

                {/* Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map((project, i) => (
                        <motion.div key={project.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                            onClick={() => navigate(`/project/${project.id}/playground`)}
                            className="group bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-5 cursor-pointer hover:border-saffron-500/30 hover:shadow-lg hover:shadow-saffron-500/5 transition-all"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/20 flex items-center justify-center">
                                    <FolderOpen size={18} className="text-indigo-500 dark:text-indigo-400" />
                                </div>
                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                                    <button onClick={(e) => handleExport(e, project.id)}
                                        className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-saffron-500 dark:hover:text-saffron-400 hover:bg-saffron-500/10 rounded-lg transition-all"
                                        title="Download pipeline">
                                        <Download size={14} />
                                    </button>
                                    <button onClick={(e) => handleDelete(e, project.id)}
                                        className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                        title="Delete project">
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                            <h3 className="text-base font-semibold text-gray-800 dark:text-slate-200 mb-1 group-hover:text-saffron-500 dark:group-hover:text-saffron-400 transition-colors">
                                {project.name}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-slate-500 line-clamp-2">
                                {project.description || 'No description'}
                            </p>
                            <p className="text-[10px] text-gray-400 dark:text-slate-600 mt-3">
                                Created {new Date(project.created_at).toLocaleDateString()}
                            </p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </Layout>
    );
};

export default Dashboard;
