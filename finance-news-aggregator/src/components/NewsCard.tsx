import React from 'react';
import { ExternalLink, Calendar, Globe } from 'lucide-react';
import { NewsItem } from '../types/news';
import { formatDate, getFullDate } from '../utils/dateFormatter';

interface NewsCardProps {
  news: NewsItem;
}

export const NewsCard: React.FC<NewsCardProps> = ({ news }) => {
  const sourceIcons: Record<string, string> = {
    'kommersant_finance': '📰',
    'vedomosti_finance': '📊',
    'moex_news': '💹',
    'cbr_press': '🏦',
    'fed_press': '🇺🇸',
    'boe_news': '🇬🇧',
    'investing_com': '📈',
    'finam': '💼'
  };

  const getSourceIcon = (sourceId: string): string => {
    return sourceIcons[sourceId] || '📰';
  };

  const getSourceName = (sourceId: string): string => {
    const sourceNames: Record<string, string> = {
      'kommersant_finance': 'Коммерсантъ',
      'vedomosti_finance': 'Ведомости',
      'moex_news': 'Московская Биржа',
      'cbr_press': 'ЦБ РФ',
      'fed_press': 'ФРС США',
      'boe_news': 'Банк Англии',
      'investing_com': 'Investing.com',
      'finam': 'Финам'
    };
    return sourceNames[sourceId] || sourceId;
  };

  // Проверяем, есть ли заголовок и нормальное описание
  const hasValidTitle = news.title && news.title !== 'null' && news.title.trim().length > 0;
  const hasValidSummary = news.summary && !news.summary.includes('Информация отсутствует');

  return (
    <article
      style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden',
        transition: 'all 0.2s ease-in-out',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '300px'
      }}
      onMouseOver={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)';
        e.currentTarget.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)';
      }}
      onMouseOut={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)';
      }}
    >
      <div
        style={{
          padding: '20px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Заголовок источника */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '12px',
            flexWrap: 'wrap'
          }}
        >
          <span style={{ fontSize: '1.2rem' }}>
            {getSourceIcon(news.source)}
          </span>
          <span
            style={{
              fontWeight: '600',
              color: '#1e293b',
              fontSize: '0.9rem'
            }}
          >
            {getSourceName(news.source)}
          </span>
          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              color: '#64748b',
              fontSize: '0.8rem'
            }}
          >
            <Globe size={12} />
            {news.source_domain}
          </span>
        </div>
        
        {/* Заголовок новости */}
        <h3
          style={{
            fontSize: '1.1rem',
            fontWeight: '600',
            lineHeight: '1.4',
            margin: '0 0 12px 0',
            color: '#1e293b',
            flex: 1
          }}
        >
          {hasValidTitle ? news.title : 'Без заголовка'}
        </h3>
        
        {/* Описание новости */}
        <p
          style={{
            color: '#64748b',
            lineHeight: '1.5',
            margin: '0 0 20px 0',
            flex: 1,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'auto'
          }}
        >
          {hasValidSummary ? news.summary : 'Описание недоступно'}
        </p>
      {/* Показатели релевантности */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            marginBottom: '16px',
            fontSize: '0.75rem',
            color: '#64748b'
          }}
        >
          <span title="Коэффициент времени">⏱ {news.time_coef.toFixed(2)}</span>
          <span title="Коэффициент плотности">📊 {news.density_coef.toFixed(2)}</span>
          <span title="Коэффициент домена">🌐 {news.domain_coef.toFixed(2)}</span>
          <span title="Общая релевантность">🔥 {news.hotness.toFixed(2)}</span>
        </div>

        {/* Футер с датой и ссылкой */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 'auto',
            paddingTop: '16px',
            borderTop: '1px solid #e2e8f0'
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#64748b',
              fontSize: '0.875rem'
            }}
          >
            <Calendar size={16} />
            <span title={getFullDate(news.published_at)}>
              {formatDate(news.published_at)}
            </span>
          </div>

          <a
            href={news.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              backgroundColor: '#2563eb',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: '500',
              transition: 'all 0.2s ease-in-out',
              minWidth: '100px',
              justifyContent: 'center'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = '#1d4ed8';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = '#2563eb';
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