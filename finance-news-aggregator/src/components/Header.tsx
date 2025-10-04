import React from 'react';
import { TrendingUp } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header style={{
      background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
      color: 'white',
      padding: '40px 0',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
      marginBottom: '32px'
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 40px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          justifyContent: 'center',
          flexDirection: 'column',
          textAlign: 'center'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <TrendingUp size={40} />
            <h1 style={{
              fontSize: '2.5rem',
              fontWeight: '700',
              margin: 0
            }}>
              Finance News
            </h1>
          </div>
          <p style={{
            fontSize: '1.2rem',
            opacity: 0.9,
            margin: 0,
            maxWidth: '600px'
          }}>
            Агрегатор финансовых новостей из мировых источников в реальном времени
          </p>
        </div>
      </div>
    </header>
  );
};