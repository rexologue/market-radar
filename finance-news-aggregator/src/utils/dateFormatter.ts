export const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      const minutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
      return `${minutes} мин. назад`;
    } else if (diffInHours < 24) {
      return `${diffInHours} ч. назад`;
    } else if (diffInHours < 168) {
      const days = Math.floor(diffInHours / 24);
      return `${days} д. назад`;
    } else {
      const weeks = Math.floor(diffInHours / 168);
      return `${weeks} нед. назад`;
    }
  } catch {
    return dateString;
  }
};

export const getFullDate = (dateString: string, timezone: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      timeZone: timezone,
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
};

export const formatTimeFilter = (filter: { value: number; unit: 'h' | 'd' | 'w' }): string => {
  const { value, unit } = filter;

  if (value === 0) {
    return 'all';
  }

  return `${value}${unit}`;
};