// src/views/Home.tsx
import React from 'react';
import { ArrowRight, Play, CheckCircle2 } from 'lucide-react';
import Button from '../components/ui/Button';
import { ViewState } from '../types';

interface HomeProps {
  onNavigate: (view: ViewState) => void;
}

const Home: React.FC<HomeProps> = ({ onNavigate }) => {
  return (
    <div className="min-h-screen pt-16">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-32 lg:pt-32">
        {/* Background Gradients */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 pointer-events-none">
          <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-blue-100/50 rounded-full blur-[100px]" />
          <div className="absolute top-[10%] right-[10%] w-[400px] h-[400px] bg-purple-100/30 rounded-full blur-[80px]" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-medium mb-8 animate-fade-in">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            New: Real-time Sentiment Analysis 2.0
          </div>

          <h1 
            className="text-5xl md:text-7xl font-display font-bold text-slate-900 tracking-tight mb-6 animate-slide-up"
            style={{ animationDelay: '0.1s' }}
          >
            Understand every voice <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-purple-600">
              in your business.
            </span>
          </h1>

          <p 
            className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto mb-10 animate-slide-up leading-relaxed"
            style={{ animationDelay: '0.2s' }}
          >
            Transform raw audio into actionable insights. Our AI-powered speech analytics platform helps you monitor compliance, improve agent performance, and boost customer satisfaction.
          </p>

          <div 
            className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up"
            style={{ animationDelay: '0.3s' }}
          >
            <Button 
              size="lg" 
              className="w-full sm:w-auto gap-2 group"
              onClick={() => onNavigate('ANALYTICS')}
            >
              Try for free
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </Button>

            <Button variant="outline" size="lg" className="w-full sm:w-auto gap-2">
              <Play size={18} className="fill-slate-700" />
              Watch Demo
            </Button>
          </div>

          {/* Social Proof */}
          <div 
            className="mt-16 pt-8 border-t border-slate-100 flex flex-wrap justify-center gap-x-8 gap-y-4 text-sm text-slate-500 animate-fade-in"
            style={{ animationDelay: '0.5s' }}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-primary-600" />
              <span>99% Transcription Accuracy</span>
            </div>

            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-primary-600" />
              <span>Real-time Processing</span>
            </div>

            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-primary-600" />
              <span>GDPR & SOC2 Compliant</span>
            </div>
          </div>
        </div>
      </section>

      {/* Visualization Section */}
      <section className="px-4 pb-24">
        <div className="max-w-6xl mx-auto relative rounded-2xl overflow-hidden shadow-2xl border border-slate-200 bg-slate-900 aspect-video flex items-center justify-center group">
          <div className="absolute inset-0 bg-gradient-to-tr from-slate-900 via-slate-800 to-slate-900 z-0"></div>

          {/* Animated Bars */}
          <div className="flex items-center gap-1 z-10 h-32">
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="w-3 bg-gradient-to-t from-blue-500 to-purple-500 rounded-full animate-pulse"
                style={{
                  height: `${Math.random() * 100}%`,
                  animationDuration: `${0.5 + Math.random()}s`,
                  opacity: 0.8,
                }}
              />
            ))}
          </div>

          <div className="absolute bottom-8 left-8 z-20">
            <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-xl flex items-center gap-4 max-w-sm">
              <div className="h-10 w-10 rounded-full bg-green-500/20 flex items-center justify-center text-green-400">
                <CheckCircle2 size={20} />
              </div>
              <div>
                <div className="text-white text-sm font-medium">Insight Detected</div>
                <div className="text-slate-300 text-xs">
                  Customer expressed high satisfaction regarding the quick resolution.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
