import React from 'react';
import { NewsItem } from '../types/news';
import { NewsCard } from './NewsCard';
import { LoadingSpinner } from './LoadingSpinner';

interface NewsGridProps {
  news: NewsItem[];
  loading: boolean;
  error: string | null;
}

export const NewsGrid: React.FC<NewsGridProps> = ({ news, loading, error }) => {
  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '60px 20px',
        color: 'var(--error-color)'
      }}>
        <h3 style={{ marginBottom: '12px', fontSize: '1.5rem' }}>Ошибка загрузки</h3>
        <p style={{ fontSize: '1rem' }}>{error}</p>
      </div>
    );
  }

  if (news.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '60px 20px',
        color: 'var(--text-secondary)'
      }}>
        <h3 style={{ marginBottom: '12px', fontSize: '1.5rem' }}>Новости не найдены</h3>
        <p style={{ fontSize: '1rem' }}>Попробуйте изменить период обновления</p>
      </div>
    );
  }

  return (
    <div className="news-grid">
      {news.map((item) => (
        <NewsCard key={item.id} news={item} />
      ))}
    </div>
  );
};