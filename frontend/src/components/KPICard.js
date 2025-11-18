import React from 'react';
import './KPICard.css';

function KPICard({ title, value, icon, color }) {
  return (
    <div className="kpi-card" style={{ '--accent-color': color }}>
      <div className="kpi-background"></div>
      <div className="kpi-icon" style={{ backgroundColor: `${color}15` }}>
        <span style={{ fontSize: '2rem' }}>{icon}</span>
      </div>
      <div className="kpi-content">
        <div className="kpi-title">{title}</div>
        <div className="kpi-value" style={{ color }}>
          {value}
        </div>
      </div>
      <div className="kpi-shine"></div>
    </div>
  );
}

export default KPICard;
