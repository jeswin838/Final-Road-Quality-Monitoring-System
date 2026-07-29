import React from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';

export default function AlertToolbar({ searchTerm, setSearchTerm, onRefresh }) {
  return (
    <div className="flex flex-col md:flex-row items-center gap-4 mb-6">
      <div className="relative w-full md:w-96">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          className="block w-full pl-10 pr-3 py-2 border border-white/10 rounded-xl leading-5 bg-black/40 text-gray-300 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-danger focus:border-danger sm:text-sm transition-colors"
          placeholder="Search by Road, Village, Landmark..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="flex w-full md:w-auto items-center gap-2 overflow-x-auto pb-1 md:pb-0 hide-scrollbar">
        <select className="bg-black/40 border border-white/10 text-gray-300 text-sm rounded-xl focus:ring-danger focus:border-danger block p-2 outline-none">
          <option value="">Priority: All</option>
          <option value="Emergency">Emergency</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
        </select>

        <select className="bg-black/40 border border-white/10 text-gray-300 text-sm rounded-xl focus:ring-danger focus:border-danger block p-2 outline-none">
          <option value="">Status: All</option>
          <option value="Not Assigned">Not Assigned</option>
          <option value="Assigned">Assigned</option>
          <option value="Verified">Verified</option>
        </select>
        
        <button className="bg-black/40 hover:bg-white/10 border border-white/10 text-gray-300 rounded-xl p-2 transition-colors ml-auto md:ml-0 flex items-center gap-2" onClick={onRefresh}>
           <RefreshCw className="w-4 h-4" />
           <span className="hidden sm:inline text-sm">Refresh</span>
        </button>
      </div>
    </div>
  );
}
