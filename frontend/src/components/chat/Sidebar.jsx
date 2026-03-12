import React, { useState } from 'react';
import { MessageSquare, Plus, Trash2, X, Edit2, Check, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import ThemeToggle from '../ui/ThemeToggle';

export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

const Sidebar = ({
    isOpen,
    onClose,
    sessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    onClearHistory,
    onRenameSession,
    isCreating
}) => {
    const [editingId, setEditingId] = useState(null);
    const [editName, setEditName] = useState("");

    const startEditing = (e, session) => {
        e.stopPropagation();
        setEditingId(session.id);
        setEditName(session.name);
    };

    const cancelEditing = (e) => {
        e.stopPropagation();
        setEditingId(null);
        setEditName("");
    };

    const saveName = async (e) => {
        e.stopPropagation();
        if (editName.trim()) {
            await onRenameSession(editingId, editName);
        }
        setEditingId(null);
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop for mobile */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 md:hidden"
                    />

                    {/* Sidebar Panel */}
                    <motion.div
                        initial={{ x: -280 }}
                        animate={{ x: 0 }}
                        exit={{ x: -280 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className="fixed md:static inset-y-0 left-0 z-40 w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col h-full shadow-xl md:shadow-none"
                    >
                        {/* Header */}
                        <div className="p-4 flex items-center justify-between">
                            <button
                                onClick={onNewChat}
                                disabled={isCreating}
                                className="flex-1 flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-4 py-3 rounded-xl transition-all border border-transparent dark:border-slate-700 shadow-sm group disabled:opacity-70 disabled:cursor-wait"
                            >
                                <Plus size={18} className={`text-indigo-500 dark:text-indigo-400 ${isCreating ? 'animate-spin' : 'group-hover:scale-110'} transition-transform`} />
                                <span className="text-sm font-medium">{isCreating ? 'Creating...' : 'New Chat'}</span>
                            </button>
                            <button onClick={onClose} className="md:hidden ml-2 p-2 text-slate-400">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Session List */}
                        <div className="flex-1 overflow-y-auto px-3 py-2 custom-scrollbar">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2">Recent Chats</h3>
                            <div className="space-y-1">
                                {sessions.map((session) => (
                                    <div key={session.id} className="group relative">
                                        {editingId === session.id ? (
                                            <div className="flex items-center gap-1 p-2 bg-indigo-50/50 dark:bg-indigo-500/10 rounded-lg border border-indigo-200 dark:border-indigo-500/30">
                                                <input
                                                    autoFocus
                                                    className="flex-1 bg-transparent text-sm text-slate-700 dark:text-slate-200 outline-none min-w-0"
                                                    value={editName}
                                                    onChange={(e) => setEditName(e.target.value)}
                                                    onKeyDown={(e) => e.key === 'Enter' && saveName(e)}
                                                />
                                                <button onClick={saveName} className="p-1 hover:bg-emerald-500/20 text-emerald-500 rounded"><Check size={14} /></button>
                                                <button onClick={cancelEditing} className="p-1 hover:bg-red-500/20 text-red-500 rounded"><XCircle size={14} /></button>
                                            </div>
                                        ) : (
                                            <button
                                                onClick={() => onSelectSession(session.id)}
                                                className={cn(
                                                    "w-full text-left px-3 py-3 rounded-lg text-sm transition-all flex items-center gap-3 pr-16 relative",
                                                    currentSessionId === session.id
                                                        ? "bg-saffron-50 dark:bg-slate-800 text-saffron-700 dark:text-saffron-300 border border-saffron-200 dark:border-slate-700 shadow-md ring-1 ring-saffron-200 dark:ring-0 font-medium"
                                                        : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50"
                                                )}
                                            >
                                                <MessageSquare size={16} className={currentSessionId === session.id ? "text-indigo-500 dark:text-indigo-400" : "text-slate-400 dark:text-slate-600"} />
                                                <span className="truncate flex-1">
                                                    {session.name || `Chat ${session.id.slice(-4)}`}
                                                </span>

                                                {/* Hover Actions */}
                                                <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex items-center transition-opacity bg-gradient-to-l from-slate-50 dark:from-slate-800/90 via-slate-50 dark:via-slate-800/90 to-transparent pl-4">
                                                    <div
                                                        onClick={(e) => startEditing(e, session)}
                                                        className="p-1.5 text-slate-400 hover:text-indigo-400 rounded-md transition-colors"
                                                    >
                                                        <Edit2 size={12} />
                                                    </div>
                                                </div>
                                            </button>
                                        )}
                                    </div>
                                ))}
                                {sessions.length === 0 && (
                                    <div className="text-center py-10 px-4">
                                        <p className="text-slate-400 dark:text-slate-600 text-xs">No history yet.</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-2 pb-4">
                            <ThemeToggle />

                            <div className="px-4">
                                <button
                                    onClick={() => onClearHistory(currentSessionId)}
                                    disabled={!currentSessionId}
                                    className="w-full flex items-center justify-center gap-2 text-slate-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 p-2 rounded-lg transition-all text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Trash2 size={14} />
                                    <span>Clear Conversation</span>
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};

export default React.memo(Sidebar);
