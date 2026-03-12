import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Sparkles, Copy, Check } from 'lucide-react';

const MessageBubble = ({ role, content }) => {
    const isUser = role === 'user';
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[85%] md:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-3 group`}>

                {/* Avatar with Tiranga Theme: User = Saffron, Bot = Green/Blue/Chakra */}
                <div className={`
            flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-md border-2
            ${isUser
                        ? 'bg-saffron-500 border-saffron-400 text-white'
                        : 'bg-white dark:bg-slate-900 border-india-green-500 text-india-green-500'}
        `}>
                    {isUser ? <User size={16} /> : <img src="/logo finance.png" alt="FinAssist" className="w-5 h-5 object-contain" />}
                </div>

                {/* Bubble */}
                <div className={`relative flex flex-col items-start`}>
                    {/* Optional Author Name */}
                    <span className={`text-[10px] text-slate-500 mb-1 px-1 ${isUser ? 'text-right w-full' : 'text-left'}`}>
                        {isUser ? 'You' : 'FinAssist'}
                    </span>

                    <div className={`
              relative px-5 py-3.5 rounded-2xl text-[15px] leading-relaxed shadow-sm
              ${isUser
                            ? 'bg-gradient-to-br from-saffron-400 to-orange-500 text-white rounded-tr-none border border-orange-400/20'
                            : 'bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-india-green-500/20 dark:border-slate-800 shadow-md'} 
            `}>
                        {/* Markdown Content */}
                        <div className={`prose dark:prose-invert prose-p:leading-relaxed 
                ${isUser ? 'text-white prose-p:text-white prose-headings:text-white' : ''}
                prose-pre:bg-slate-100 dark:prose-pre:bg-[#111] prose-pre:border prose-pre:border-slate-200 dark:prose-pre:border-white/5 prose-pre:rounded-xl max-w-none ${!isUser && "w-full"}`}>
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    code({ node, inline, className, children, ...props }) {
                                        return !inline ? (
                                            <div className="relative group/code my-4">
                                                <div className="absolute right-2 top-2 opacity-0 group-hover/code:opacity-100 transition-opacity">
                                                    <div className="text-[10px] text-slate-500 bg-black/50 px-2 py-1 rounded">Copy code</div>
                                                </div>
                                                <code className={`${className} block bg-[#1e1e1e] p-4 rounded-lg text-sm font-mono overflow-x-auto border border-white/5`} {...props}>
                                                    {children}
                                                </code>
                                            </div>
                                        ) : (
                                            <code className="bg-slate-200 dark:bg-[#2d2d2d] text-slate-800 dark:text-orange-300 px-1.5 py-0.5 rounded text-sm font-mono border border-slate-300 dark:border-white/5" {...props}>
                                                {children}
                                            </code>
                                        )
                                    },
                                    a({ node, children, ...props }) {
                                        return (
                                            <a
                                                className="text-blue-600 dark:text-blue-400 hover:underline font-medium break-all"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                {...props}
                                            >
                                                {children}
                                            </a>
                                        )
                                    }
                                }}
                            >
                                {content}
                            </ReactMarkdown>
                        </div>
                    </div>

                    {/* Action Buttons (Bot only) */}
                    {!isUser && (
                        <div className="flex items-center gap-2 mt-2 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                                onClick={handleCopy}
                                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                                title="Copy Response"
                            >
                                {copied ? <Check size={14} className="text-india-green-500" /> : <Copy size={14} />}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MessageBubble;
