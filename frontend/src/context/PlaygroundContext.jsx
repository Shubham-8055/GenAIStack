import React, { createContext, useContext, useState, useCallback } from 'react';

/**
 * PlaygroundContext — persists chat messages and debug info across route changes.
 * Messages are stored per-project so navigating between settings/docs/playground
 * won't wipe the conversation.
 */
const PlaygroundContext = createContext(null);

export const usePlayground = () => useContext(PlaygroundContext);

export const PlaygroundProvider = ({ children }) => {
    // { [projectId]: { messages: [], lastDebug: null } }
    const [store, setStore] = useState({});

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
