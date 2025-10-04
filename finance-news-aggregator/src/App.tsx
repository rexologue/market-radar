import React, { useState } from 'react';
import { Header } from './components/Header';
import { TimeFilter } from './components/TimeFilter';
import { NewsGrid } from './components/NewsGrid';
import { useNews } from './hooks/useNews';
import { TimeFilter as TimeFilterType } from './types/news';
import './styles/globals.css';

function App() {
  // Дефолтное значение - 24 часа
  const [timeFilter, setTimeFilter] = useState<TimeFilterType>({ value: 24, unit: 'h' });
  const [hasSearched, setHasSearched] = useState(false);

  const { news, loading, error, fetchNews } = useNews();

  const handleRefresh = async () => {
    setHasSearched(true);
    await fetchNews(timeFilter);
  };

  const handleTimeFilterChange = (filter: TimeFilterType) => {
    setTimeFilter(filter);
    // Только меняем фильтр, не запускаем поиск
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f8fafc',
      fontFamily: 'Arial, sans-serif'
    }}>
      <Header />

      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 40px' }}>
        <TimeFilter
          timeFilter={timeFilter}
          onTimeFilterChange={handleTimeFilterChange}
          onRefresh={handleRefresh}
          loading={loading}
        />

        <NewsGrid
          news={news}
          loading={loading}
          error={error}
          hasSearched={hasSearched}
        />
      </main>

      <footer style={{
        backgroundColor: '#ffffff',
        borderTop: '1px solid #e2e8f0',
        padding: '32px 0',
        marginTop: '60px'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 40px' }}>
          <div style={{
            textAlign: 'center',
            color: '#64748b'
          }}>
            <p style={{ marginBottom: '8px' }}>
              © 2025 AdequacyOFF
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