import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GlassCard from '../components/GlassCard';
import { 
  Activity, 
  BarChart3, 
  PieChart, 
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Filter,
  Download,
  Info
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, Legend
} from 'recharts';
import { motion } from 'framer-motion';

const COLORS = ['#38BDF8', '#10B981', '#F59E0B', '#F43F5E', '#A855F7'];

export default function Analytics() {
  const [data, setData] = useState({
    severity_distribution: [],
    monthly_trends: []
  });

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await axios.get('/api/analytics');
        setData(res.data);
      } catch (err) {
        console.error("Failed to fetch analytics", err);
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div className="space-y-8 pb-20">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/5 pb-6">
        <div>
          <h2 className="text-2xl font-black text-title flex items-center gap-3">
            <Activity className="w-8 h-8 text-accent" />
            Performance Analytics
          </h2>
          <p className="text-xs text-muted-text font-bold uppercase tracking-widest mt-1">Comprehensive Road Quality Metrics</p>
        </div>
        <div className="flex gap-3">
           <button className="btn btn-secondary text-[10px] px-4 py-2">
             <Calendar className="w-4 h-4" />
             Custom Range
           </button>
           <button className="btn btn-primary text-[10px] px-4 py-2">
             <Download className="w-4 h-4" />
             Export PDF
           </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <GlassCard className="lg:col-span-2 p-8">
           <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="text-sm font-black text-title uppercase tracking-widest flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-accent" />
                  Severity Distribution
                </h3>
              </div>
              <Info className="w-4 h-4 text-gray-700" />
           </div>
           
           <div className="h-[350px] w-full">
             <ResponsiveContainer width="100%" height="100%">
               <BarChart data={data.severity_distribution}>
                 <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                 <XAxis 
                   dataKey="name" 
                   stroke="#94A3B8" 
                   fontSize={10} 
                   tickLine={false} 
                   axisLine={false}
                   tickFormatter={(val) => val.toUpperCase()}
                 />
                 <YAxis stroke="#94A3B8" fontSize={10} tickLine={false} axisLine={false} />
                 <Tooltip 
                   cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                   contentStyle={{ 
                     backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                     borderRadius: '16px', 
                     border: '1px solid rgba(255,255,255,0.1)',
                     boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                   }}
                   itemStyle={{ color: '#F8FAFC', fontWeight: 'bold', fontSize: '12px' }}
                   labelStyle={{ color: '#94A3B8', fontSize: '10px', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '900' }}
                 />
                 <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                   {data.severity_distribution.map((entry, index) => (
                     <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                   ))}
                 </Bar>
               </BarChart>
             </ResponsiveContainer>
           </div>
        </GlassCard>

        <GlassCard className="p-8">
           <div className="flex items-center justify-between mb-8">
              <h3 className="text-sm font-black text-title uppercase tracking-widest flex items-center gap-2">
                <PieChart className="w-4 h-4 text-accent" />
                Category Split
              </h3>
           </div>
           
           <div className="h-[350px] w-full">
             <ResponsiveContainer width="100%" height="100%">
               <RePieChart>
                 <Pie
                   data={data.severity_distribution}
                   cx="50%"
                   cy="50%"
                   innerRadius={80}
                   outerRadius={110}
                   paddingAngle={8}
                   dataKey="count"
                 >
                   {data.severity_distribution.map((entry, index) => (
                     <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="rgba(255,255,255,0.05)" strokeWidth={2} />
                   ))}
                 </Pie>
                 <Tooltip 
                   contentStyle={{ 
                     backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                     borderRadius: '16px', 
                     border: '1px solid rgba(255,255,255,0.1)'
                   }}
                 />
                 <Legend verticalAlign="bottom" height={36} iconType="circle" />
               </RePieChart>
             </ResponsiveContainer>
           </div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
         <GlassCard className="p-8 border-l-4 border-l-accent">
            <div className="flex items-center gap-4">
              <div className="p-4 rounded-2xl bg-accent/10 text-accent">
                 <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-black text-title uppercase tracking-widest">High Risk Sectors</h4>
                <p className="text-3xl font-black text-title mt-1">04</p>
                <p className="text-xs text-muted-text mt-1 font-bold">Dharmapuri District Central</p>
              </div>
            </div>
         </GlassCard>

         <GlassCard className="p-8 border-l-4 border-l-success">
            <div className="flex items-center gap-4">
              <div className="p-4 rounded-2xl bg-success/10 text-success">
                 <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-black text-title uppercase tracking-widest">Resolution Rate</h4>
                <p className="text-3xl font-black text-title mt-1">94%</p>
                <p className="text-xs text-muted-text mt-1 font-bold">Compared to 86% last quarter</p>
              </div>
            </div>
         </GlassCard>
      </div>
    </div>
  );
}
