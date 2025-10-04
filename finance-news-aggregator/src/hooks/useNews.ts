import { useState, useEffect } from 'react';
import { NewsItem } from '../types/news';
import { formatTimeFilter } from '../utils/dateFormatter';

const API_BASE_URL = 'http://localhost:8000';

export const useNews = (timeFilter: { value: number; unit: 'h' | 'd' | 'w' }) => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNews = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const sinceParam = timeFilter.value === 0 ? 'all' : formatTimeFilter(timeFilter);
        const response = await fetch(`${API_BASE_URL}/pipeline?since=${sinceParam}`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: NewsItem[] = await response.json();
        setNews(data);
      } catch (err) {
        console.error('Error fetching news:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch news';
        setError(errorMessage);
        setNews([]);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [timeFilter]);

  return { news, loading, error };
};