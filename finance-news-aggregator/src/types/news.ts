export interface NewsSource {
  id: string;
  type: string;
  timezone: string;
  outfile: string;
  urls: string[];
}

export interface NewsItem {
  id: string;
  title: string;
  description: string;
  link: string;
  pubDate: string;
  source: string;
  sourceId: string;
  timezone: string;
  imageUrl?: string;
}

export interface TimeFilter {
  value: number;
  unit: 'h' | 'd' | 'w';
}