import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const LiveDataContext = createContext();

export const useLiveData = () => useContext(LiveDataContext);

export const LiveDataProvider = ({ children }) => {
  const [data, setData] = useState({
    stats: { total: 0, today: 0, fixed: 0, pending: 0 },
    alerts: [],
    approved: [],
    pending: [],
    map: [],
    timestamp: null
  });
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    let timeoutId;

    const fetchLiveData = async () => {
      try {
        const response = await axios.get('/api/live-data');
        if (isMounted) {
          setData(prev => ({
            stats: response.data.stats_error ? prev.stats : response.data.stats,
            alerts: response.data.alerts_error ? prev.alerts : response.data.alerts,
            approved: response.data.approved_error ? prev.approved : response.data.approved,
            pending: response.data.pending_error ? prev.pending : response.data.pending,
            map: response.data.map_error ? prev.map : response.data.map,
            timestamp: response.data.timestamp
          }));
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Failed to fetch live data:", err);
          setError(err.message);
        }
      } finally {
        if (isMounted) {
          timeoutId = setTimeout(fetchLiveData, 5000); // 5 seconds interval, wait until previous finishes
        }
      }
    };

    fetchLiveData();

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
    };
  }, []);

  return (
    <LiveDataContext.Provider value={{ data, loading, error }}>
      {children}
    </LiveDataContext.Provider>
  );
};
