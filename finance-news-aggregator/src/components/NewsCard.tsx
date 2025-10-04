import React from 'react';
import { ExternalLink, Calendar, Globe } from 'lucide-react';
import { NewsItem } from '../types/news';
import { formatDate, getFullDate } from '../utils/dateFormatter';

interface NewsCardProps {
  news: NewsItem;
}

export const NewsCard: React.FC<NewsCardProps> = ({ news }) => {
  const sourceIcons: { [key: string]: string } = {
    'kommersant_finance': '📰',
    'vedomosti_finance': '📊',
    'moex_news': '💹',
    'cbr_press': '🏦',
    'fed_press': '🇺🇸',
    'boe_news': '🇬🇧',
    'investing_com': '📈',
    'finam': '💼'
  };

  const getSourceIcon = (sourceId: string) => {
    return sourceIcons[sourceId] || '📰';
  };

  return (
    <article style={{
      backgroundColor: 'var(--surface-color)',
      borderRadius: 'var(--border-radius)',
      boxShadow: 'var(--shadow)',
      overflow: 'hidden',
      transition: 'var(--transition)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      minHeight: '400px'
    }}
    onMouseOver={(e) => {
      e.currentTarget.style.transform = 'translateY(-4px)';
      e.currentTarget.style.boxShadow = 'var(--shadow-hover)';
    }}
    onMouseOut={(e) => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'var(--shadow)';
    }}
    >
      {news.imageUrl && (
        <div style={{
          width: '100%',
          height: '200px',
          overflow: 'hidden',
          flexShrink: 0
        }}>
          <img 
            src={news.imageUrl} 
            alt={news.title}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transition: 'var(--transition)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'scale(1.05)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
            }}
          />
        </div>
      )}
      
      <div style={{
        padding: '24px',
        flex: 1,
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '12px',
          flexWrap: 'wrap'
        }}>
          <span style={{ fontSize: '1.2rem' }}>
            {getSourceIcon(news.sourceId)}
          </span>
          <span style={{
            fontWeight: '600',
            color: 'var(--text-primary)',
            fontSize: '0.9rem'
          }}>
            {news.source}
          </span>
          <span style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            color: 'var(--text-secondary)',
            fontSize: '0.8rem'
          }}>
            <Globe size={12} />
            {news.timezone.split('/')[1]}
          </span>
        </div>
        
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: '600',
          lineHeight: '1.4',
          margin: '0 0 12px 0',
          color: 'var(--text-primary)',
          flex: 1
        }}>
          {news.title}
        </h3>
        
        <p style={{
          color: 'var(--text-secondary)',
          lineHeight: '1.5',
          margin: '0 0 20px 0',
          flex: 1,
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }}>
          {news.description}
        </p>
        
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 'auto',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-color)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--text-secondary)',
            fontSize: '0.875rem'
          }}>
            <Calendar size={16} />
            <span title={getFullDate(news.pubDate, news.timezone)}>
              {formatDate(news.pubDate, news.timezone)}
            </span>
          </div>
          
          <a
            href={news.link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              backgroundColor: 'var(--primary-color)',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: '500',
              transition: 'var(--transition)',
              minWidth: '100px',
              justifyContent: 'center'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--primary-hover)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--primary-color)';
            }}
          >
            <ExternalLink size={16} />
            Читать
          </a>
        </div>
      </div>
    </article>
  );
};