import { useState } from 'react';
import { NewsItem } from '../types/news';
import { formatTimeFilter } from '../utils/dateFormatter';

const API_BASE_URL = '/api';

// Мок-данные на случай ошибки бэкенда
const getMockNews = (): NewsItem[] => [
  {
    id: '1',
    title: 'ЦБ РФ оставил ключевую ставку без изменения на уровне 16%',
    description: 'Банк России принял решение сохранить ключевую ставку на уровне 16% годовых. Такое решение было ожидаемо большинством аналитиков.',
    link: 'https://www.cbr.ru/press/event/',
    pubDate: new Date().toISOString(),
    source: 'Центральный банк РФ',
    sourceId: 'cbr_press',
    timezone: 'Europe/Moscow',
    imageUrl: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&h=200&fit=crop'
  },
  {
    id: '2',
    title: 'ФРС США обсуждает возможность снижения ставки',
    description: 'По данным протоколов последнего заседания, члены ФРС склоняются к началу цикла смягчения денежно-кредитной политики.',
    link: 'https://www.federalreserve.gov/',
    pubDate: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    source: 'Federal Reserve',
    sourceId: 'fed_press',
    timezone: 'America/New_York',
    imageUrl: 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=400&h=200&fit=crop'
  },
  {
    id: '3',
    title: 'MOEX обновляет исторический максимум',
    description: 'Индекс МосБиржи впервые в истории превысил отметку в 3500 пунктов. Росту способствовало укрепление рубля.',
    link: 'https://www.moex.com/',
    pubDate: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    source: 'Московская Биржа',
    sourceId: 'moex_news',
    timezone: 'Europe/Moscow',
    imageUrl: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=400&h=200&fit=crop'
  }
];

export const useNews = () => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = async (timeFilter: { value: number; unit: 'h' | 'd' | 'w' }) => {
    setLoading(true);
    setError(null);

    try {
      const sinceParam = timeFilter.value === 0 ? 'all' : formatTimeFilter(timeFilter);
      const url = `${API_BASE_URL}/pipeline?since=${sinceParam}`;

      console.log('Fetching from:', url);

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
      });

      console.log('Response status:', response.status);

      if (response.ok) {
        const data: NewsItem[] = await response.json();
        console.log('Received data:', data);
        setNews(data);
      } else {
        // Если бэкенд возвращает ошибку, используем мок-данные
        console.log('Backend error, using mock data');
        setNews(getMockNews());
      }

    } catch (err) {
      console.error('Fetch error, using mock data:', err);
      setNews(getMockNews());
      setError('Бэкенд временно недоступен. Показаны демонстрационные данные.');
    } finally {
      setLoading(false);
    }
  };

  return { news, loading, error, fetchNews };
};