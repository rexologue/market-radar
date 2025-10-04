import React, { useState } from 'react';
import { Header } from './components/Header';
import { TimeFilter } from './components/TimeFilter';
import { NewsGrid } from './components/NewsGrid';
import { useNews } from './hooks/useNews';
import { TimeFilter as TimeFilterType } from './types/news';
import './styles/globals.css';

function App() {
  const [timeFilter, setTimeFilter] = useState<TimeFilterType>({ value: 24, unit: 'h' });
  const [refreshKey, setRefreshKey] = useState(0);
  
  const { news, loading, error } = useNews(timeFilter);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--background-color)' }}>
      <Header />
      
      <main className="container">
        <TimeFilter 
          timeFilter={timeFilter}
          onTimeFilterChange={setTimeFilter}
          onRefresh={handleRefresh}
          loading={loading}
        />
        
        <NewsGrid 
          news={news}
          loading={loading}
          error={error}
        />
      </main>
      
      <footer style={{
        backgroundColor: 'var(--surface-color)',
        borderTop: '1px solid var(--border-color)',
        padding: '32px 0',
        marginTop: '60px'
      }}>
        <div className="container">
          <div style={{
            textAlign: 'center',
            color: 'var(--text-secondary)'
          }}>
            <p style={{ marginBottom: '8px' }}>
              © 2024 Finance News Aggregator
            </p>
            <p style={{ fontSize: '0.875rem' }}>
              Агрегатор финансовых новостей из проверенных источников
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;