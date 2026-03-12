import React, { useEffect, useState } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { motion } from 'framer-motion';

const ThemeToggle = () => {
    const [theme, setTheme] = useState(
        localStorage.getItem('theme') || 'system'
    );

    useEffect(() => {
        const root = window.document.documentElement;

        const removeTheme = () => {
            root.classList.remove('dark');
            root.classList.remove('light');
        }

        const applyTheme = (t) => {
            removeTheme();
            if (t === 'system') {
                const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                root.classList.add(systemTheme);
            } else {
                root.classList.add(t);
            }
        };

        applyTheme(theme);
        localStorage.setItem('theme', theme);

        // Listener for system changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = () => {
            if (theme === 'system') applyTheme('system');
        };
        mediaQuery.addEventListener('change', handleChange);

        return () => mediaQuery.removeEventListener('change', handleChange);
    }, [theme]);

    return (
        <div className="flex bg-[#1a1d26] dark:bg-[#1a1d26] bg-slate-200 p-1 rounded-lg border border-white/5 mx-4 mb-2">
            {[
                { name: 'light', icon: Sun },
                { name: 'system', icon: Monitor },
                { name: 'dark', icon: Moon },
            ].map((t) => (
                <button
                    key={t.name}
                    onClick={() => setTheme(t.name)}
                    className={`
                        flex-1 p-1.5 rounded-md flex justify-center items-center transition-all relative
                        ${theme === t.name ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-400'}
                    `}
                >
                    {theme === t.name && (
                        <motion.div
                            layoutId="theme-pill"
                            className="absolute inset-0 bg-[#0f1117] dark:bg-[#0f1117] bg-white shadow-sm rounded-md"
                            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                        />
                    )}
                    <span className="relative z-10">
                        <t.icon size={14} />
                    </span>
                </button>
            ))}
        </div>
    );
};

export default ThemeToggle;
