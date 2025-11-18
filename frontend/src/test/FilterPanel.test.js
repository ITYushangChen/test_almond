
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  default: {
    get: jest.fn(),
    post: jest.fn()
  }
}));

jest.mock('../config', () => ({
  default: {
    apiBaseUrl: 'http://localhost:3001/api'
  }
}));

import FilterPanel from '../components/FilterPanel';

describe('FilterPanel Component', () => {
  test('renders FilterPanel without crashing', () => {
    const { container } = render(<FilterPanel />);
    expect(container).toBeInTheDocument();
  });

  test('renders FilterPanel with basic props', () => {
    const mockOnFilterChange = jest.fn();
    const { container } = render(
      <FilterPanel onFilterChange={mockOnFilterChange} />
    );
    
    expect(container).toBeInTheDocument();
    expect(container.textContent).toContain('Filter');
  });

  test('renders FilterPanel with different props', () => {
    const { container } = render(
      <FilterPanel 
        initialDateRange={{ start: '2023-01-01', end: '2023-12-31' }}
        categories={['Product', 'Service', 'Support']}
      />
    );
    
    expect(container).toBeInTheDocument();
  });

  test('renders FilterPanel without external dependencies', () => {
    const { container } = render(<FilterPanel />);
    
    expect(container.firstChild).toBeInTheDocument();
  });

  test('renders FilterPanel with empty props', () => {
    const { container } = render(<FilterPanel />);
    
    expect(container).toBeInTheDocument();
  });
});