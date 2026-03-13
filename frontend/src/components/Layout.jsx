import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Settings, FileUp, MessageSquare, ChevronLeft, Sparkles, ScrollText, Sun, Moon, Receipt } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
];

const projectNavItems = [
    { path: 'settings', icon: Settings, label: 'Agent Settings' },
    { path: 'documents', icon: FileUp, label: 'Documents' },
    { path: 'transactions', icon: Receipt, label: 'Transactions' },
    { path: 'playground', icon: MessageSquare, label: 'Playground' },
    { path: 'logs', icon: ScrollText, label: 'Query Logs' },
];

const Layout = ({ children, projectId = null, projectName = null }) => {
    const navigate = useNavigate();
    const { theme, toggleTheme } = useTheme();

    return (
        <div className="flex h-screen bg-gray-50 dark:bg-slate-950 text-gray-800 dark:text-slate-200 font-outfit overflow-hidden transition-colors duration-300">
            {/* Sidebar */}
            <aside className="w-64 bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 flex flex-col transition-colors duration-300">
                {/* Logo */}
                <div className="p-5 border-b border-gray-200 dark:border-slate-800">
                    <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => navigate('/')}>
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-saffron-400 to-orange-500 flex items-center justify-center shadow-lg shadow-saffron-500/20">
                            <Sparkles size={18} className="text-white" />
                        </div>
                        <div>
                            <h1 className="text-base font-bold text-gray-900 dark:text-slate-100 leading-tight">GenAI Platform</h1>
                            <p className="text-[10px] text-gray-400 dark:text-slate-500 leading-tight">Config-Driven AI</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-3 space-y-1">
                    {/* Main nav */}
                    {navItems.map(item => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                                    ? 'bg-saffron-500/10 text-saffron-400 border border-saffron-500/20'
                                    : 'text-gray-500 dark:text-slate-400 hover:text-gray-800 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/50'
                                }`
                            }
                        >
                            <item.icon size={18} />
                            {item.label}
                        </NavLink>
                    ))}

                    {/* Project nav */}
                    {projectId && (
                        <>
                            <div className="pt-4 pb-2 px-2">
                                <button
                                    onClick={() => navigate('/')}
                                    className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors mb-2"
                                >
                                    <ChevronLeft size={14} />
                                    Back to Dashboard
                                </button>
                                <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider truncate">
                                    {projectName || 'Project'}
                                </p>
                            </div>
                            {projectNavItems.map(item => (
                                <NavLink
                                    key={item.path}
                                    to={`/project/${projectId}/${item.path}`}
                                    className={({ isActive }) =>
                                        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                                            ? 'bg-indigo-500/10 text-indigo-500 dark:text-indigo-400 border border-indigo-500/20'
                                            : 'text-gray-500 dark:text-slate-400 hover:text-gray-800 dark:hover:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/50'
                                        }`
                                    }
                                >
                                    <item.icon size={18} />
                                    {item.label}
                                </NavLink>
                            ))}
                        </>
                    )}
                </nav>

                {/* Footer with theme toggle */}
                <div className="p-4 border-t border-gray-200 dark:border-slate-800 space-y-3">
                    <button
                        onClick={toggleTheme}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-700 hover:text-gray-800 dark:hover:text-slate-200"
                    >
                        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                        {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                    </button>
                    <p className="text-[10px] text-gray-400 dark:text-slate-600 text-center">
                        v1.0.0 · Open Source GenAI
                    </p>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto">
                {children}
            </main>
        </div>
    );
};

export default Layout;
