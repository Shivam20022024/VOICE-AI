
import React, { useState, useEffect, useRef } from 'react';
import { Mic, ChevronDown, Menu, X, BarChart2, Phone, Shield } from 'lucide-react';
import Button from './ui/Button';
import { ViewState } from '../types';

interface NavbarProps {
  currentView: ViewState;
  onNavigate: (view: ViewState) => void;
}

const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isProductOpen, setIsProductOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProductOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleProductClick = (view: ViewState) => {
    onNavigate(view);
    setIsProductOpen(false);
    setIsMobileMenuOpen(false);
  };

  return (
    <nav 
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? 'bg-white/80 backdrop-blur-md border-b border-slate-200/50' : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">

          {/* Logo */}
          <div 
            className="flex items-center gap-2 cursor-pointer group" 
            onClick={() => onNavigate('HOME')}
          >
            <div className="bg-primary-600 p-1.5 rounded-lg text-white transform group-hover:scale-110 transition-transform">
              <Mic size={20} />
            </div>
            <span className="font-display font-bold text-xl tracking-tight text-slate-900">
              Voice AI
            </span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <div className="relative" ref={dropdownRef}>
              <button 
                className="flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-primary-600 transition-colors py-2"
                onClick={() => setIsProductOpen(!isProductOpen)}
              >
                Product
                <ChevronDown size={16} className={`transition-transform duration-200 ${isProductOpen ? 'rotate-180' : ''}`} />
              </button>

              {isProductOpen && (
                <div className="absolute top-full left-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-slate-100 p-2 animate-slide-up">
                  
                  <div 
                    className="flex items-start gap-3 p-3 hover:bg-slate-50 rounded-lg cursor-pointer"
                    onClick={() => handleProductClick('ANALYTICS')}
                  >
                    <div className="bg-blue-50 text-blue-600 p-2 rounded-lg">
                      <BarChart2 size={20} />
                    </div>
                    <div>
                      <h4 className="font-semibold text-sm text-slate-900">Speech Analytics</h4>
                      <p className="text-xs text-slate-500 mt-0.5">Unlock insights from conversations.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 p-3 hover:bg-slate-50 rounded-lg cursor-pointer">
                    <div className="bg-green-50 text-green-600 p-2 rounded-lg">
                      <Phone size={20} />
                    </div>
                    <div>
                      <h4 className="font-semibold text-sm text-slate-900">Voice Assistant</h4>
                      <p className="text-xs text-slate-500 mt-0.5">Automate support using AI.</p>
                    </div>
                  </div>

                </div>
              )}
            </div>

            {/* Removed Items Here */}
            {/* ❌ Solutions */}
            {/* ❌ Pricing */}
            {/* ❌ Enterprise */}
          </div>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-4">
            {/* ❌ Sign In Removed */}
            <Button size="sm" onClick={() => onNavigate('ANALYTICS')}>Get Started</Button>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-slate-200 px-4 py-4 shadow-lg animate-slide-up">
          <div className="flex flex-col gap-4">

            <div className="border-b pb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Product</span>

              <button 
                className="flex items-center gap-2 w-full text-left py-2 text-slate-700 font-medium"
                onClick={() => handleProductClick('ANALYTICS')}
              >
                <BarChart2 size={18} className="text-primary-600"/> Speech Analytics
              </button>

              <button className="flex items-center gap-2 w-full text-left py-2 text-slate-700 font-medium">
                <Phone size={18} className="text-green-600"/> Voice Assistant
              </button>
            </div>

            {/* ❌ Removed Solutions */}
            {/* ❌ Removed Pricing */}

            <div className="pt-4 flex flex-col gap-3">
              {/* ❌ Removed Sign In */}
              <Button className="w-full justify-center" onClick={() => handleProductClick('ANALYTICS')}>
                Get Started
              </Button>
            </div>

          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
