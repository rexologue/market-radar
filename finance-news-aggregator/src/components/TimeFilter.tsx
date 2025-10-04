import React from 'react';
import { Clock, RefreshCw } from 'lucide-react';
import { TimeFilter as TimeFilterType } from '../types/news';

interface TimeFilterProps {
  timeFilter: TimeFilterType;
  onTimeFilterChange: (filter: TimeFilterType) => void;
  onRefresh: () => void;
  loading: boolean;
}

export const TimeFilter: React.FC<TimeFilterProps> = ({
  timeFilter,
  onTimeFilterChange,
  onRefresh,
  loading
}) => {
  const handleValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value) || 0;
    onTimeFilterChange({ ...timeFilter, value: Math.max(0, value) });
  };

  const handleUnitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onTimeFilterChange({ 
      ...timeFilter, 
      unit: e.target.value as 'h' | 'd' | 'w' 
    });
  };

  const handleSetAllTime = () => {
    onTimeFilterChange({ value: 0, unit: 'h' });
  };

  const getDisplayText = () => {
    if (timeFilter.value === 0) {
      return 'Все новости';
    }
    const unitLabel = timeFilter.unit === 'h' ? 'часов' : timeFilter.unit === 'd' ? 'дней' : 'недель';
    return `Новости за последние ${timeFilter.value} ${unitLabel}`;
  };

  return (
    <div style={{
      backgroundColor: 'var(--surface-color)',
      padding: '24px',
      borderRadius: 'var(--border-radius)',
      boxShadow: 'var(--shadow)',
      marginBottom: '32px'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '20px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <Clock size={24} color="#2563eb" />
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: '600',
            margin: 0,
            color: 'var(--text-primary)'
          }}>
            Период обновления
          </h2>
        </div>
        
        <button
          onClick={onRefresh}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            backgroundColor: 'var(--primary-color)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--border-radius)',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'var(--transition)',
            opacity: loading ? 0.6 : 1,
            minWidth: '140px',
            justifyContent: 'center'
          }}
          onMouseOver={(e) => {
            if (!loading) {
              e.currentTarget.style.backgroundColor = 'var(--primary-hover)';
            }
          }}
          onMouseOut={(e) => {
            if (!loading) {
              e.currentTarget.style.backgroundColor = 'var(--primary-color)';
            }
          }}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Обновление...' : 'Обновить'}
        </button>
      </div>

      <div className="time-filter-grid">
        <label style={{
          fontWeight: '600',
          color: 'var(--text-primary)',
          whiteSpace: 'nowrap',
          fontSize: '16px'
        }}>
          Показать новости за:
        </label>
        
        <input
          type="number"
          value={timeFilter.value === 0 ? '' : timeFilter.value}
          onChange={handleValueChange}
          placeholder="Введите число"
          min="0"
          style={{
            padding: '12px 16px',
            border: '2px solid var(--border-color)',
            borderRadius: 'var(--border-radius)',
            fontSize: '16px',
            transition: 'var(--transition)',
            width: '100%'
          }}
        />
        
        <select
          value={timeFilter.unit}
          onChange={handleUnitChange}
          style={{
            padding: '12px 16px',
            border: '2px solid var(--border-color)',
            borderRadius: 'var(--border-radius)',
            fontSize: '16px',
            backgroundColor: 'var(--surface-color)',
            cursor: 'pointer',
            transition: 'var(--transition)',
            width: '100%'
          }}
        >
          <option value="h">часов</option>
          <option value="d">дней</option>
          <option value="w">недель</option>
        </select>
        
        <button
          onClick={handleSetAllTime}
          style={{
            padding: '12px 20px',
            backgroundColor: timeFilter.value === 0 ? 'var(--primary-color)' : 'transparent',
            color: timeFilter.value === 0 ? 'white' : 'var(--primary-color)',
            border: `2px solid ${timeFilter.value === 0 ? 'var(--primary-color)' : 'var(--border-color)'}`,
            borderRadius: 'var(--border-radius)',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'var(--transition)',
            whiteSpace: 'nowrap',
            width: '100%'
          }}
          onMouseOver={(e) => {
            if (timeFilter.value !== 0) {
              e.currentTarget.style.backgroundColor = 'var(--primary-color)';
              e.currentTarget.style.color = 'white';
            }
          }}
          onMouseOut={(e) => {
            if (timeFilter.value !== 0) {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--primary-color)';
            }
          }}
        >
          Все время
        </button>
      </div>

      <div style={{
        padding: '12px 16px',
        backgroundColor: '#f0f9ff',
        border: '1px solid #bae6fd',
        borderRadius: '8px',
        color: '#0369a1',
        fontSize: '14px',
        marginTop: '16px'
      }}>
        <strong>Текущий период:</strong> {getDisplayText()}
      </div>
    </div>
  );
};