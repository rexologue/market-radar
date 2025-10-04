import React from 'react';

export const LoadingSpinner: React.FC = () => {
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      padding: '60px 20px',
      flexDirection: 'column',
      gap: '16px'
    }}>
      <div
        style={{
          width: '48px',
          height: '48px',
          border: '4px solid #e2e8f0',
          borderTop: '4px solid #2563eb',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}
        className="animate-spin"
      />
      <p style={{ color: '#64748b', fontSize: '16px' }}>Загрузка новостей...</p>
    </div>
  );
};