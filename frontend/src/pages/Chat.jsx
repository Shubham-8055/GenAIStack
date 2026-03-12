import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Loader2, Menu } from 'lucide-react';
import Sidebar from '../components/chat/Sidebar';
import MessageBubble from '../components/chat/MessageBubble';

const API_BASE = 'http://localhost:8000';

const Chat = () => {
    // State
    const [sessionId, setSessionId] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [initError, setInitError] = useState(null);
    const [isCreatingSession, setIsCreatingSession] = useState(false);

    const messagesEndRef = useRef(null);

    // Initialize
    useEffect(() => {
        const init = async () => {
            try {
                await fetchSessions();
                await createSession();
                setInitError(null);
            } catch (err) {
                console.error("Initialization failed:", err);
                setInitError("Failed to connect to backend. Is it running?");
            }
        };
        init();
    }, []);

    // Fetch History when session changes
    useEffect(() => {
        if (sessionId) {
            fetchHistory(sessionId);
        }
    }, [sessionId]);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    // --- API CALLS ---

    const fetchSessions = async () => {
        try {
            const res = await axios.get(`${API_BASE}/sessions`);
            setSessions(res.data);
        } catch (err) {
            console.error("Error fetching sessions:", err);
        }
    };

    const createSession = async () => {
        if (isCreatingSession) return;
        setIsCreatingSession(true);
        try {
            const res = await axios.post(`${API_BASE}/sessions`);
            const newId = res.data.session_id;
            setSessionId(newId);
            setMessages([]);
            await fetchSessions();
            if (window.innerWidth < 768) setSidebarOpen(false);
            setInitError(null);
        } catch (err) {
            console.error("Error creating session:", err);
            setInitError("Could not create chat session. Backend unreachable.");
        } finally {
            setIsCreatingSession(false);
        }
    };

    const fetchHistory = async (id) => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_BASE}/history/${id}`);
            setMessages(res.data);
        } catch (err) {
            console.error("Error fetching history:", err);
        } finally {
            setLoading(false);
        }
    };

    const clearHistory = async (id) => {
        if (!id) return;
        try {
            await axios.delete(`${API_BASE}/history/${id}`);
            setMessages([]);
            fetchSessions();
        } catch (err) {
            console.error("Error clearing history:", err);
        }
    };

    const renameSession = async (id, newName) => {
        try {
            await axios.put(`${API_BASE}/sessions/${id}/name`, { name: newName });
            fetchSessions();
        } catch (err) {
            console.error("Failed to rename:", err);
        }
    }

    const handleSend = async () => {
        if (!input.trim() || !sessionId) return;

        const userMsg = input;
        setInput('');

        // Optimistic Update
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await axios.post(`${API_BASE}/chat`, {
                session_id: sessionId,
                message: userMsg
            });
            setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: "⚠️ Error: Backend unavailable." }]);
        } finally {
            setLoading(false);
        }
    };

    const handleSelectSession = (id) => {
        setSessionId(id);
        if (window.innerWidth < 768) setSidebarOpen(false);
    };

    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 font-outfit overflow-hidden transition-colors duration-300">

            {/* Sidebar (Responsive) */}
            <Sidebar
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                sessions={sessions}
                currentSessionId={sessionId}
                onSelectSession={handleSelectSession}
                onNewChat={createSession}
                onClearHistory={clearHistory}
                onRenameSession={renameSession}
                isCreating={isCreatingSession}
            />

            {/* Main Content */}
            <div className="flex-1 flex flex-col h-full relative">

                {/* Error Banner */}
                {initError && (
                    <div className="bg-red-500/10 border-b border-red-500/20 text-red-500 p-2 text-center text-sm font-medium">
                        ⚠️ {initError}
                    </div>
                )}

                {/* Top Bar */}
                <div className="h-16 border-b border-slate-200 dark:border-slate-800 flex items-center px-4 justify-between bg-white/80 dark:bg-slate-900/80 backdrop-blur-md z-10 transition-colors">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500 dark:text-slate-400 transition-colors"
                        >
                            <Menu size={20} />
                        </button>
                        <div className="flex items-center gap-2">
                            {/* CUSTOM LOGO: HEADER */}
                            <img
                                src="/logo finance.png"
                                alt="AEPS Logo"
                                className="h-12 w-auto object-contain"
                            />
                            <span className="font-bold text-lg text-slate-800 dark:text-slate-200">FinAssist</span>
                        </div>
                    </div>
                </div>

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto px-4 md:px-0 custom-scrollbar bg-slate-50 dark:bg-slate-950">
                    <div className="max-w-3xl mx-auto pt-8 pb-32">

                        {/* Welcome State */}
                        {messages.length === 0 && !loading && (
                            <div className="flex flex-col items-center justify-center mt-20 text-center px-6 animate-in fade-in zoom-in duration-500">
                                {/* CUSTOM LOGO: WELCOME SCREEN */}
                                <div className="mb-6 bg-white/50 dark:bg-slate-800/50 p-4 rounded-2xl backdrop-blur-sm border border-slate-200 dark:border-slate-800 shadow-xl shadow-slate-200/50 dark:shadow-none">
                                    <img
                                        src="/logo finance.png"
                                        alt="AEPS Logo"
                                        className="h-20 w-auto object-contain"
                                    />
                                </div>

                                <h2 className="text-3xl font-bold text-slate-800 dark:text-slate-100 mb-2">
                                    FinAssist
                                </h2>
                                <p className="text-slate-500 dark:text-slate-400 max-w-md mb-8">
                                    How can I assist you with your finance queries today?
                                </p>

                                {/* SUGGESTIONS */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-lg">
                                    {['Account operations', 'Banking limits', 'Forms & guidelines'].map((text) => (
                                        <button
                                            key={text}
                                            onClick={() => setInput(text)}
                                            className="p-4 text-sm text-left bg-white dark:bg-slate-900 hover:bg-saffron-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-xl transition-all text-slate-700 dark:text-slate-300 hover:text-saffron-500 dark:hover:text-saffron-400 hover:border-saffron-500/30 shadow-sm"
                                        >
                                            {text}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Messages */}
                        {messages.map((msg, idx) => (
                            <MessageBubble key={idx} role={msg.role} content={msg.content} />
                        ))}

                        {/* Loading Indicator */}
                        {loading && (
                            <div className="flex items-center gap-3 px-4 animate-pulse">
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-saffron-500/20 to-orange-500/20 flex items-center justify-center">
                                    <div className="w-4 h-4 border-2 border-saffron-500 border-t-transparent rounded-full animate-spin"></div>
                                </div>
                                <div className="flex gap-1">
                                    <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </div>

                {/* Input Area (Bottom Fixed) WITH FIXED GRADIENT */}
                <div className="absolute bottom-0 left-0 right-0 z-20 pt-10 pb-6 px-4 backdrop-blur-sm bg-gradient-to-t from-slate-50 via-slate-50/80 to-transparent dark:from-slate-950 dark:via-slate-950/80 dark:to-transparent">
                    <div className="max-w-3xl mx-auto relative group">
                        <div className="relative flex items-center bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden transition-colors">
                            <input
                                type="text"
                                className="flex-1 bg-transparent border-none py-4 px-5 text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none ring-0 font-medium"
                                placeholder="Message FinAssist..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                disabled={loading}
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || loading}
                                className="p-3 mr-2 bg-saffron-500 hover:bg-saffron-400 disabled:opacity-0 disabled:scale-75 text-white rounded-xl transition-all duration-200 shadow-lg shadow-saffron-500/20"
                            >
                                {loading ? <Loader2 size={18} className="animate-spin text-white" /> : <Send size={18} />}
                            </button>
                        </div>
                        <p className="text-center text-[10px] text-slate-500 dark:text-slate-500 mt-2">
                            AI generated content may be inaccurate.
                        </p>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default Chat;
