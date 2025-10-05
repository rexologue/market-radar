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
        color: 'var(--error-color)',
        backgroundColor: 'var(--surface-color)',
        borderRadius: 'var(--border-radius)',
        boxShadow: 'var(--shadow)',
        margin: '20px 0'
      }}>
        <h3 style={{ marginBottom: '16px', fontSize: '1.5rem' }}>Ошибка загрузки новостей</h3>
        <p style={{
          marginBottom: '20px',
          fontSize: '1rem',
          lineHeight: '1.5'
        }}>
          {error}
        </p>
      </div>
    );
  }

  if (news.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '60px 20px',
        color: 'var(--text-secondary)',
        backgroundColor: 'var(--surface-color)',
        borderRadius: 'var(--border-radius)',
        boxShadow: 'var(--shadow)',
        margin: '20px 0'
      }}>
        <h3 style={{ marginBottom: '12px', fontSize: '1.5rem' }}>Новости не найдены</h3>
        <p style={{ fontSize: '1rem' }}>
          Попробуйте изменить период обновления
        </p>
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