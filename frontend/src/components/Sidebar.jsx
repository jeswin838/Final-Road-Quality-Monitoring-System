import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Map, 
  Image as ImageIcon, 
  Activity, 
  Wrench, 
  AlertTriangle, 
  Settings,
  ShieldCheck,
  LogOut,
  ClipboardList,
  Camera
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Safe Navigation', path: '/navigation', icon: Map },
  { name: 'Image Logs', path: '/image-logs', icon: ImageIcon },
  { name: 'Analytics', path: '/analytics', icon: Activity },
  { name: 'Maintenance', path: '/maintenance', icon: Wrench },
  { name: 'Alerts', path: '/alerts', icon: AlertTriangle },
  { name: 'User Reports', path: '/user-reports', icon: ClipboardList },
  { name: 'Report Pothole', path: '/report', icon: Camera },
  { name: 'Admin Panel', path: '/admin', icon: ShieldCheck },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-72 bg-secondary backdrop-blur-[20px] border-r border-glass-border flex flex-col z-[100] shadow-[10px_0_40px_rgba(0,0,0,0.3)]">
      <div className="flex items-center gap-4 p-8 mb-4">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-accent to-blue-600 flex items-center justify-center shadow-[0_0_25px_rgba(56,189,248,0.4)] border border-white/20">
          <ShieldCheck className="text-slate-900 w-7 h-7" />
        </div>
        <div>
          <span className="text-xl font-black text-title block leading-none">PotholePro</span>
          <span className="text-[10px] font-bold text-accent uppercase tracking-[0.2em] mt-1 block">AI MONITORING</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 custom-scrollbar flex flex-col gap-1.5">
        <div className="text-[10px] font-black text-muted-text uppercase tracking-[0.2em] mb-4 px-4 mt-4">
          Control Center
        </div>
        
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3.5 rounded-2xl text-sm font-bold transition-all duration-300 group ${
                  isActive
                    ? 'bg-accent/15 text-accent border border-accent/20 shadow-[0_0_20px_rgba(56,189,248,0.1)]'
                    : 'text-muted-text hover:bg-white/5 hover:text-title border border-transparent'
                }`
              }
            >
              <Icon className={`w-5 h-5 transition-transform duration-300 group-hover:scale-110`} />
              {item.name}
              {/* Active Indicator Glow */}
              <div className="ml-auto opacity-0 group-[.active]:opacity-100 transition-opacity">
                <div className="w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_10px_#38BDF8]" />
              </div>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-6 mt-auto">
        <div className="p-4 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center gap-3 group hover:bg-white/[0.05] transition-all cursor-pointer">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center border border-white/10 group-hover:border-accent/30 transition-colors">
            <span className="text-sm font-black text-white">A</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-black text-title truncate">System Admin</p>
            <p className="text-[10px] text-muted-text font-bold truncate uppercase tracking-tighter">Verified Profile</p>
          </div>
          <button className="text-muted-text hover:text-danger transition-colors p-2 rounded-xl hover:bg-danger/10">
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
