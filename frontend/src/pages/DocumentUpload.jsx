import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Upload, FileText, Trash2, Loader2, CheckCircle, AlertCircle, File } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import { getProject, getDocuments, uploadDocument, deleteDocument } from '../services/api';

const DocumentUpload = () => {
    const { projectId } = useParams();
    const [project, setProject] = useState(null);
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const [toast, setToast] = useState(null);
    const fileInputRef = useRef(null);

    useEffect(() => { loadData(); }, [projectId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [proj, docs] = await Promise.all([getProject(projectId), getDocuments(projectId)]);
            setProject(proj); setDocuments(docs);
        } catch { showToast('Failed to load documents', 'error'); }
        finally { setLoading(false); }
    };

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    const handleUpload = async (files) => {
        if (!files || files.length === 0) return;
        setUploading(true);
        for (const file of files) {
            try { await uploadDocument(projectId, file); showToast(`"${file.name}" uploaded and indexed!`); }
            catch (err) { showToast(`Failed to upload "${file.name}": ${err.response?.data?.detail || err.message}`, 'error'); }
        }
        setUploading(false); loadData();
    };

    const handleDelete = async (docId, filename) => {
        if (!confirm(`Delete "${filename}" and all its vectors?`)) return;
        try { await deleteDocument(projectId, docId); showToast(`"${filename}" deleted.`); loadData(); }
        catch { showToast('Failed to delete document.', 'error'); }
    };

    const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleUpload(Array.from(e.dataTransfer.files)); };
    const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

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
                <div className="mb-8">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Documents</h1>
                    <p className="text-gray-500 dark:text-slate-500 mt-1">Upload knowledge base documents for <span className="text-gray-700 dark:text-slate-300">{project?.name}</span></p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-none transition-colors">
                        <p className="text-sm text-gray-500 dark:text-slate-500">Total Documents</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-slate-100 mt-1">{documents.length}</p>
                    </div>
                    <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-none transition-colors">
                        <p className="text-sm text-gray-500 dark:text-slate-500">Total Chunks</p>
                        <p className="text-2xl font-bold text-indigo-500 dark:text-indigo-400 mt-1">{totalChunks}</p>
                    </div>
                </div>

                {/* Upload Zone */}
                <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all mb-6 ${dragOver
                        ? 'border-saffron-500 bg-saffron-500/5'
                        : 'border-gray-300 dark:border-slate-700 hover:border-gray-400 dark:hover:border-slate-600 bg-white/50 dark:bg-slate-900/50 hover:bg-gray-50 dark:hover:bg-slate-900'
                        }`}
                >
                    <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt,.md" onChange={e => handleUpload(Array.from(e.target.files))} className="hidden" />
                    {uploading ? (
                        <div className="flex flex-col items-center gap-3">
                            <Loader2 size={36} className="animate-spin text-saffron-500" />
                            <p className="text-gray-500 dark:text-slate-400">Processing and indexing...</p>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-3">
                            <Upload size={36} className="text-gray-400 dark:text-slate-500" />
                            <p className="text-gray-700 dark:text-slate-300 font-medium">Drop files here or click to upload</p>
                            <p className="text-gray-400 dark:text-slate-500 text-sm">Supports PDF, TXT, MD files</p>
                        </div>
                    )}
                </div>

                {/* Document List */}
                {loading ? (
                    <div className="flex justify-center py-10">
                        <Loader2 size={24} className="animate-spin text-saffron-500" />
                    </div>
                ) : (
                    <div className="space-y-2">
                        <AnimatePresence>
                            {documents.map((doc, i) => (
                                <motion.div key={doc.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -50 }} transition={{ delay: i * 0.03 }}
                                    className="group flex items-center justify-between bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl px-5 py-3.5 hover:border-gray-300 dark:hover:border-slate-700 transition-all shadow-sm dark:shadow-none"
                                >
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${doc.status === 'ready'
                                            ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-500 dark:text-emerald-400'
                                            : doc.status === 'error'
                                                ? 'bg-red-100 dark:bg-red-500/10 text-red-500 dark:text-red-400'
                                                : 'bg-yellow-100 dark:bg-yellow-500/10 text-yellow-500 dark:text-yellow-400'
                                            }`}>
                                            {doc.status === 'ready' ? <FileText size={18} /> : doc.status === 'error' ? <AlertCircle size={18} /> : <Loader2 size={18} className="animate-spin" />}
                                        </div>
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{doc.filename}</p>
                                            <p className="text-xs text-gray-400 dark:text-slate-500">
                                                {doc.chunk_count} chunks · {doc.status} · {new Date(doc.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>
                                    <button onClick={() => handleDelete(doc.id, doc.filename)}
                                        className="opacity-0 group-hover:opacity-100 p-2 text-gray-400 dark:text-slate-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-all">
                                        <Trash2 size={14} />
                                    </button>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        {documents.length === 0 && !loading && (
                            <div className="text-center py-10">
                                <File size={36} className="mx-auto text-gray-300 dark:text-slate-700 mb-3" />
                                <p className="text-gray-500 dark:text-slate-500">No documents uploaded yet.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default DocumentUpload;
