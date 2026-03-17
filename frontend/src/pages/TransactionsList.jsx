import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTransactions, seedTransactions } from '../services/api';
import { Receipt, RefreshCcw, Database, Search, AlertCircle, Loader2, ArrowLeft } from 'lucide-react';

const TransactionsList = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [transactions, setTransactions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSeeding, setIsSeeding] = useState(false);
    const [error, setError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    const fetchTransactions = async () => {
        setIsLoading(true);
        setError('');
        try {
            const data = await getTransactions(projectId);
            setTransactions(data);
        } catch (err) {
            console.error('Failed to fetch transactions:', err);
            setError('Failed to load transactions. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSeed = async () => {
        setIsSeeding(true);
        setError('');
        try {
            await seedTransactions(projectId);
            await fetchTransactions();
        } catch (err) {
            console.error('Failed to seed transactions:', err);
            setError('Failed to seed sample data.');
        } finally {
            setIsSeeding(false);
        }
    };

    useEffect(() => {
        if (projectId) {
            fetchTransactions();
        }
    }, [projectId]);

    const filteredTransactions = transactions.filter(t => {
        const term = searchTerm.toLowerCase();
        return (
            t.bank_name?.toLowerCase().includes(term) ||
            t.rrn?.toLowerCase().includes(term) ||
            t.status?.toLowerCase().includes(term) ||
            t.amount?.toString().includes(term) ||
            Object.values(t.custom_fields || {}).some(v => v?.toString().toLowerCase().includes(term))
        );
    });

    // Extract dynamic custom field keys from all transactions to render headers dynamically
    const customHeaders = new Set();
    transactions.forEach(t => {
        if (t.custom_fields) {
            Object.keys(t.custom_fields).forEach(k => customHeaders.add(k));
        }
    });
    const dynamicColumns = Array.from(customHeaders);

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR'
        }).format(amount || 0);
    };

    const StatusBadge = ({ status }) => {
        const config = {
            success: { bg: 'bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20' },
            failed: { bg: 'bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20' },
            pending: { bg: 'bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20' }
        };
        const style = config[status?.toLowerCase()] || { bg: 'bg-gray-50 text-gray-600 border-gray-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700' };
        return (
            <span className={`px-2.5 py-1 text-[11px] font-semibold tracking-wider rounded-md border uppercase ${style.bg}`}>
                {status}
            </span>
        );
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                    <button
                        onClick={() => navigate(-1)}
                        className="mt-1 p-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-800 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                        title="Go back"
                    >
                        <ArrowLeft size={18} />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            <Receipt className="text-indigo-500" />
                            Transactions
                        </h1>
                        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
                            View and manage transaction records for the tool-call agent.
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={fetchTransactions}
                        disabled={isLoading}
                        className="px-4 py-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        <RefreshCcw size={16} className={isLoading ? 'animate-spin' : ''} />
                        Refresh
                    </button>
                    <button
                        onClick={handleSeed}
                        disabled={isSeeding}
                        className="px-4 py-2 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 rounded-lg text-sm font-medium hover:bg-indigo-100 dark:hover:bg-indigo-500/20 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {isSeeding ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
                        Seed Sample Data
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-4 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 rounded-xl flex items-center gap-3 text-rose-600 dark:text-rose-400 text-sm">
                    <AlertCircle size={18} className="shrink-0" />
                    <p>{error}</p>
                </div>
            )}

            {/* Table Container */}
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">

                {/* Search Bar */}
                <div className="p-4 border-b border-gray-200 dark:border-slate-800 flex items-center gap-3">
                    <div className="relative w-full max-w-md cursor-text">
                        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 pointer-events-none" />
                        <input
                            type="text"
                            placeholder="Search by amount, bank, RRN, or custom field..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-slate-950 border border-gray-200 dark:border-slate-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center p-12 text-gray-500 dark:text-slate-400">
                            <Loader2 size={32} className="animate-spin mb-4 text-indigo-500" />
                            <p>Loading transactions...</p>
                        </div>
                    ) : filteredTransactions.length === 0 ? (
                        <div className="flex flex-col items-center justify-center p-16 text-center">
                            <Receipt size={48} className="text-gray-300 dark:text-slate-700 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 dark:text-slate-100">No transactions found</h3>
                            <p className="text-sm text-gray-500 dark:text-slate-400 mt-1 max-w-sm">
                                {searchTerm ? "No transactions match your search filter." : "Click 'Seed Sample Data' to generate dummy records for testing."}
                            </p>
                        </div>
                    ) : (
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-gray-500 dark:text-slate-400 uppercase bg-gray-50/50 dark:bg-slate-950/50 border-b border-gray-200 dark:border-slate-800">
                                <tr>
                                    <th className="px-6 py-4 font-medium whitespace-nowrap">Date</th>
                                    <th className="px-6 py-4 font-medium whitespace-nowrap">Amount</th>
                                    <th className="px-6 py-4 font-medium whitespace-nowrap">Status</th>
                                    <th className="px-6 py-4 font-medium whitespace-nowrap">Bank</th>
                                    <th className="px-6 py-4 font-medium whitespace-nowrap">RRN</th>
                                    {dynamicColumns.map(col => (
                                        <th key={col} className="px-6 py-4 font-medium whitespace-nowrap">{col.replace(/_/g, ' ')}</th>
                                    ))}
                                    <th className="px-6 py-4 font-medium">Remarks</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-slate-800">
                                {filteredTransactions.map(txn => (
                                    <tr key={txn.id} className="hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-slate-400">
                                            {new Date(txn.txn_date).toLocaleString(undefined, {
                                                year: 'numeric', month: 'short', day: 'numeric',
                                                hour: '2-digit', minute: '2-digit'
                                            })}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900 dark:text-slate-100">
                                            {formatCurrency(txn.amount)}
                                            <span className="text-[10px] text-gray-400 dark:text-slate-500 ml-2 uppercase tracking-wider">{txn.txn_type}</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <StatusBadge status={txn.status} />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-700 dark:text-slate-300">
                                            {txn.bank_name || '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500 dark:text-slate-400 font-mono">
                                            {txn.rrn || '-'}
                                        </td>
                                        {dynamicColumns.map(col => (
                                            <td key={col} className="px-6 py-4 whitespace-nowrap font-medium text-indigo-600 dark:text-indigo-400">
                                                {txn.custom_fields?.[col] || '-'}
                                            </td>
                                        ))}
                                        <td className="px-6 py-4 text-xs text-gray-500 dark:text-slate-400 truncate max-w-[200px]" title={txn.remarks}>
                                            {txn.remarks || '-'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TransactionsList;
