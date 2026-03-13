import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

/**
 * PlaygroundContext — persists chat messages and debug info across route changes.
 * Messages are stored per-project so navigating between settings/docs/playground
 * won't wipe the conversation.
 */
const PlaygroundContext = createContext(null);

export const usePlayground = () => useContext(PlaygroundContext);

const STORAGE_KEY = 'genai_playground_store';

export const PlaygroundProvider = ({ children }) => {
    // { [projectId]: { messages: [], lastDebug: null } }
    const [store, setStore] = useState(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) return JSON.parse(saved);
        } catch (e) {
            console.error('Failed to load playground state from localStorage', e);
        }
        return {};
    });

    // Save to localStorage whenever store changes
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    }, [store]);

    const getState = useCallback((projectId) => {
        return store[projectId] || { messages: [], lastDebug: null };
    }, [store]);

    const setMessages = useCallback((projectId, updater) => {
        setStore(prev => {
            const current = prev[projectId] || { messages: [], lastDebug: null };
            const newMessages = typeof updater === 'function' ? updater(current.messages) : updater;
            return { ...prev, [projectId]: { ...current, messages: newMessages } };
        });
    }, []);

    const setLastDebug = useCallback((projectId, debug) => {
        setStore(prev => {
            const current = prev[projectId] || { messages: [], lastDebug: null };
            return { ...prev, [projectId]: { ...current, lastDebug: debug } };
        });
    }, []);

    const clearChat = useCallback((projectId) => {
        setStore(prev => ({ ...prev, [projectId]: { messages: [], lastDebug: null } }));
    }, []);

    return (
        <PlaygroundContext.Provider value={{ getState, setMessages, setLastDebug, clearChat }}>
            {children}
        </PlaygroundContext.Provider>
    );
};
