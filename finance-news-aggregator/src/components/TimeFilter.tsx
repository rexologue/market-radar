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
      <div>
    <div style={{
      backgroundColor: '#ffffff',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
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
            color: '#1e293b'
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
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '12px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'all 0.2s ease-in-out',
            opacity: loading ? 0.6 : 1,
            minWidth: '140px',
            justifyContent: 'center'
          }}
        >
          <RefreshCw size={16} style={{
            animation: loading ? 'spin 1s linear infinite' : 'none'
          }} />
          {loading ? 'Обновление...' : 'Обновить'}
        </button>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'auto 200px 150px auto',
        gap: '16px',
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <label style={{
          fontWeight: '600',
          color: '#1e293b',
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
            border: '2px solid #e2e8f0',
            borderRadius: '12px',
            fontSize: '16px',
            transition: 'all 0.2s ease-in-out',
            width: '100%'
          }}
        />

        <select
          value={timeFilter.unit}
          onChange={handleUnitChange}
          style={{
            padding: '12px 16px',
            border: '2px solid #e2e8f0',
            borderRadius: '12px',
            fontSize: '16px',
            backgroundColor: '#ffffff',
            cursor: 'pointer',
            transition: 'all 0.2s ease-in-out',
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
            backgroundColor: timeFilter.value === 0 ? '#2563eb' : 'transparent',
            color: timeFilter.value === 0 ? 'white' : '#2563eb',
            border: `2px solid ${timeFilter.value === 0 ? '#2563eb' : '#e2e8f0'}`,
            borderRadius: '12px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'all 0.2s ease-in-out',
            whiteSpace: 'nowrap',
            width: '100%'
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

      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
      </div>
  );
};