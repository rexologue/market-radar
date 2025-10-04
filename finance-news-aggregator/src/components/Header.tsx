import React from 'react';
import { TrendingUp } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header style={{
      background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
      color: 'white',
      padding: '40px 0',
      boxShadow: 'var(--shadow)',
      marginBottom: '32px'
    }}>
      <div className="container">
        <div className="header-content">
          <div className="header-title">
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