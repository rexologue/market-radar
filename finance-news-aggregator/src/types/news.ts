export interface NewsItem {
  source: string;
  source_domain: string;
  published_at: string;
  url: string;
  title: string | null;
  summary: string;
  time_coef: number;
  density_coef: number;
  domain_coef: number;
  hotness: number;
}

export interface TimeFilter {
  value: number;
  unit: 'h' | 'd' | 'w';
}