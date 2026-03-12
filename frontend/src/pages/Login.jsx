import React, { useState } from 'react';
import { ShieldCheck, TrendingUp, Users } from 'lucide-react';

const Login = ({ onLogin }) => {
    const [mobile, setMobile] = useState('');
    const [captcha, setCaptcha] = useState('');
    const [isChecked, setIsChecked] = useState(false);

    // Mock captcha
    const mockCaptcha = "0 8 1 2";

    const handleLogin = () => {
        if (mobile && isChecked) {
            onLogin();
        }
    };

    return (
        <div className="min-h-screen w-full flex relative overflow-hidden font-outfit bg-white">

            {/* Background Shading Effects */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-orange-300/40 rounded-full blur-[100px] pointer-events-none"></div>
            <div className="absolute top-[10%] left-[20%] w-[30%] h-[30%] bg-saffron-500/20 rounded-full blur-[80px] pointer-events-none"></div>
            <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-green-300/30 rounded-full blur-[100px] pointer-events-none"></div>

            {/* LEFT SIDE: Content */}
            <div className="hidden lg:flex w-1/2 flex-col justify-center px-16 xl:px-24 z-10">
                <div className="max-w-xl">
                    <h1 className="text-4xl font-semibold text-slate-900 mb-12">
                        Understand • Assist • Simplify
                    </h1>

                    <div className="space-y-10">
                        {/* Feature 1 */}
                        <div className="flex gap-4 items-start">
                            <div className="mt-1 text-saffron-500">
                                <Users size={24} className="fill-current" />
                            </div>
                            <div>
                                <h3 className="text-xl font-medium text-slate-800 mb-2">
                                    FinAssist
                                </h3>
                                <p className="text-slate-500 leading-relaxed font-light">
                                    Smart help for banking and finance—understand products, complete account tasks, and get clear answers quickly.
                                </p>
                            </div>
                        </div>

                        {/* Feature 2 */}
                        <div className="flex gap-4 items-start">
                            <div className="mt-1 text-saffron-500">
                                <TrendingUp size={24} className="fill-current" />
                            </div>
                            <div>
                                <h3 className="text-xl font-medium text-slate-800 mb-2">
                                    Account & Service Help
                                </h3>
                                <p className="text-slate-500 leading-relaxed font-light">
                                    Simple, step-by-step guidance for KYC updates, reactivation, form filling, and everyday banking services.
                                </p>
                            </div>
                        </div>

                        {/* Feature 3 */}
                        <div className="flex gap-4 items-start">
                            <div className="mt-1 text-saffron-500">
                                <ShieldCheck size={24} className="fill-current" />
                            </div>
                            <div>
                                <h3 className="text-xl font-medium text-slate-800 mb-2">
                                    Products & Payments Q&A
                                </h3>
                                <p className="text-slate-500 leading-relaxed font-light">
                                    Clear answers on savings accounts, credit cards, loans, charges, limits, and digital payments—all in one place.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Links (Left) */}
                <div className="absolute bottom-8 text-xs text-slate-400 flex gap-6 font-light">
                    <span>Terms of use</span>
                    <span>Privacy policy</span>
                    <span>Disclaimer</span>
                    <span>FAQs</span>
                </div>
            </div>

            {/* RIGHT SIDE: Login Card */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-6">
                <div className="bg-white rounded-[2rem] shadow-2xl shadow-slate-200/50 w-full max-w-md p-10 border border-slate-100 relative overflow-hidden">

                    {/* Header Logos */}
                    <div className="flex justify-center items-center gap-6 mb-10">
                        {/* AePS Logo */}
                        <div className="flex flex-col items-center">
                            <img src="/logo finance.png" alt="AePS" className="h-24 object-contain" />
                            <span className="text-sm font-semibold text-slate-700 mt-2">FinAssist</span>
                        </div>
                    </div>

                    <h2 className="text-center text-xl font-medium text-slate-800 mb-8">Login</h2>

                    {/* Form */}
                    <div className="space-y-6">
                        {/* Mobile Input */}
                        <div className="space-y-2">
                            <label className="text-xs font-normal text-slate-500 ml-1">Enter your mobile number</label>
                            <input
                                type="text"
                                placeholder="Eg. 9876543210"
                                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-slate-800 outline-none focus:border-saffron-400 focus:ring-1 focus:ring-saffron-400 transition-all placeholder:text-slate-400 font-normal"
                                value={mobile}
                                onChange={(e) => setMobile(e.target.value)}
                            />
                            <div className="flex items-center gap-1 text-[10px] text-orange-500 font-normal">
                                <span className="w-3 h-3 rounded-full border border-orange-500 flex items-center justify-center text-[8px]">!</span>
                                Please enter a mobile number which is linked to your account
                            </div>
                        </div>

                        {/* Captcha */}
                        <div className="space-y-2">
                            <label className="text-xs font-normal text-slate-500 ml-1">Security Verification</label>
                            <div className="flex gap-4 h-12">
                                <div className="flex-1 bg-white border border-slate-200 rounded-lg flex items-center justify-center text-lg font-serif tracking-widest text-slate-800 select-none whitespace-nowrap font-normal">
                                    {mockCaptcha}
                                </div>
                                <input
                                    type="text"
                                    placeholder="Enter captcha"
                                    className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-slate-800 outline-none focus:border-saffron-400 transition-all placeholder:text-slate-400 text-center font-normal"
                                    value={captcha}
                                    onChange={(e) => setCaptcha(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* T&C */}
                        <div className="flex items-center gap-3 pt-2">
                            <input
                                type="checkbox"
                                id="terms"
                                checked={isChecked}
                                onChange={(e) => setIsChecked(e.target.checked)}
                                className="w-4 h-4 rounded border-slate-300 text-saffron-500 focus:ring-saffron-500 cursor-pointer accent-saffron-500"
                            />
                            <label htmlFor="terms" className="text-[10px] text-slate-500 cursor-pointer select-none font-light">
                                I have read and agree to the <span className="underline decoration-slate-400">Terms & Conditions</span> and <span className="underline decoration-slate-400">Disclaimer</span>
                            </label>
                        </div>

                        {/* Button */}
                        <button
                            onClick={handleLogin}
                            disabled={!mobile || !isChecked}
                            className={`w-full py-3.5 rounded-full font-medium transition-all duration-300 ${mobile && isChecked
                                ? 'bg-slate-700 hover:bg-slate-800 text-white shadow-lg shadow-slate-300'
                                : 'bg-slate-300 text-white cursor-not-allowed'
                                }`}
                        >
                            Continue
                        </button>
                    </div>


                </div>
                {/* Footer Copyright (Right) */}
                <div className="absolute bottom-8 right-8 text-[10px] text-slate-400 flex items-center gap-2">
                    <span>© 2026 NPCI. All rights reserved</span>
                    <span className="bg-orange-400 text-white px-2 py-0.5 rounded-full text-[8px] font-bold">PILOT LAUNCH</span>
                </div>
            </div>
        </div>
    );
};

export default Login;
