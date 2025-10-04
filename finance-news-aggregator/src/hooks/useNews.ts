import { useState, useEffect } from 'react';
import { NewsItem } from '../types/news';
import { formatTimeFilter } from '../utils/dateFormatter';

// Используем прокси вместо прямого URL
const API_BASE_URL = '/api';

// Реальные мок-данные для тестирования
const getMockNews = (): NewsItem[] => [
  {
    id: '1',
    title: 'ЦБ РФ оставил ключевую ставку без изменения на уровне 16%',
    description: 'Банк России принял решение сохранить ключевую ставку на уровне 16% годовых. Такое решение было ожидаемо большинством аналитиков. Экономисты отмечают, что инфляционное давление продолжает оставаться высоким.',
    link: 'https://www.cbr.ru/press/event/',
    pubDate: new Date().toISOString(),
    source: 'Центральный банк РФ',
    sourceId: 'cbr_press',
    timezone: 'Europe/Moscow'
  },
  {
    id: '2',
    title: 'ФРС США обсуждает возможность снижения ставки в следующем квартале',
    description: 'По данным протоколов последнего заседания, члены ФРС склоняются к началу цикла смягчения денежно-кредитной политики в ближайшие месяцы. Рынки ожидают первых шагов по нормализации политики.',
    link: 'https://www.federalreserve.gov/',
    pubDate: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    source: 'Federal Reserve',
    sourceId: 'fed_press',
    timezone: 'America/New_York'
  },
  {
    id: '3',
    title: 'MOEX обновляет исторический максимум на фоне роста нефтяных котировок',
    description: 'Индекс МосБиржи впервые в истории превысил отметку в 3500 пунктов. Росту способствовало укрепление рубля и рост цен на нефть марки Brent до $85 за баррель.',
    link: 'https://www.moex.com/',
    pubDate: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    source: 'Московская Биржа',
    sourceId: 'moex_news',
    timezone: 'Europe/Moscow'
  },
  {
    id: '4',
    title: 'Коммерсантъ: Крупные компании готовят IPO на российском рынке',
    description: 'Несколько крупных российских компаний из IT-сектора планируют провести первичные публичные размещения акций в 2024 году. Аналитики ожидают повышенный интерес инвесторов.',
    link: 'https://www.kommersant.ru/',
    pubDate: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    source: 'Коммерсантъ',
    sourceId: 'kommersant_finance',
    timezone: 'Europe/Moscow'
  },
  {
    id: '5',
    title: 'Банк Англии сохраняет осторожную позицию по инфляции',
    description: 'Глава Банка Англии заявил о необходимости сохранять жесткую денежно-кредитную политику до уверенного снижения инфляции до целевого уровня. Рынки пересматривают ожидания по срокам снижения ставки.',
    link: 'https://www.bankofengland.co.uk/',
    pubDate: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    source: 'Bank of England',
    sourceId: 'boe_news',
    timezone: 'Europe/London'
  }
];

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
        const url = `${API_BASE_URL}/pipeline?since=${sinceParam}`;

        console.log('Sending POST request via proxy to:', url);

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
          },
        });

        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);

        if (!response.ok) {
          let errorText = '';
          try {
            errorText = await response.text();
          } catch {
            errorText = response.statusText;
          }
          console.error('Backend error:', response.status, errorText);
          throw new Error(`Backend error: ${response.status} ${errorText}`);
        }
        console.log('Response successful, processing...');

        // Обрабатываем FileResponse
        const blob = await response.blob();
        console.log('Blob type:', blob.type, 'size:', blob.size);

        const text = await blob.text();
        console.log('Text length:', text.length);

        try {
          const data: NewsItem[] = JSON.parse(text);
          console.log('Successfully parsed JSON, items:', data.length);
          setNews(data);
        } catch (parseError) {
          console.error('JSON parse error:', parseError);
          throw new Error('Invalid JSON response from server');
        }

      } catch (err) {
        console.error('Error in fetchNews:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch news';
        setError(errorMessage);

        // Используем мок-данные при ошибках
        console.log('Falling back to mock data');
        setNews(getMockNews());
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [timeFilter]);

  return { news, loading, error };
};