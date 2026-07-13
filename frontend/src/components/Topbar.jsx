import React from 'react';
import { Bell, Menu, Activity } from 'lucide-react';
import { useLocation } from 'react-router-dom';

export default function Topbar() {
  const location = useLocation();
  const pathName = location.pathname.substring(1) || 'dashboard';
  const pageTitle = pathName.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

  return (
    <header className="h-16 bg-background/80 backdrop-blur-xl border-b border-glass-border flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <button className="lg:hidden text-gray-400 hover:text-white transition-colors">
          <Menu className="w-6 h-6" />
        </button>
        <h1 className="text-lg font-semibold text-gray-100">{pageTitle}</h1>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 border border-success/20 text-success text-xs font-medium">
          <Activity className="w-3.5 h-3.5" />
          System Online
        </div>
        
        <button className="relative p-2 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-danger rounded-full shadow-[0_0_8px_rgba(239,68,68,0.8)]"></span>
        </button>
      </div>
    </header>
  );
}
