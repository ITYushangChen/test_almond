import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import KPICard from '../components/KPICard';

describe('KPICard Component', () => {
  test('renders KPICard without crashing', () => {
    const { container } = render(<KPICard title="Test" value="123" icon="test" />);
    expect(container).toBeInTheDocument();
  });

  test('renders KPICard with basic props', () => {
    const { container } = render(<KPICard title="Total Comments" value="1,234" icon="comment" />);
    
    expect(container.textContent).toContain('Total Comments');
    expect(container.textContent).toContain('1,234');
  });

  test('renders KPICard with title and value', () => {
    const { container } = render(<KPICard title="Average eNPS" value="35" icon="trending-up" />);
    
    expect(container.textContent).toContain('Average eNPS');
    expect(container.textContent).toContain('35');
  });

  test('renders KPICard with additional props', () => {
    const { container } = render(
      <KPICard 
        title="Test KPI" 
        value="42" 
        icon="test"
      />
    );
    
    expect(container.textContent).toContain('Test KPI');
    expect(container.textContent).toContain('42');
  });

  test('renders KPICard with different title and value', () => {
    const { container } = render(<KPICard title="Response Time" value="5.2s" icon="clock" />);
    
    expect(container.textContent).toContain('Response Time');
    expect(container.textContent).toContain('5.2s');
  });
});