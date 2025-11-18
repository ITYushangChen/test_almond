import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';


jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn() },
  get: jest.fn(),
}));
import axios from 'axios';

jest.mock('../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false, toggleTheme: jest.fn() }),
}));

jest.mock('../config', () => ({
  __esModule: true,
  default: { API_URL: 'http://localhost:3000' },
}));


jest.mock('../components/FilterPanel', () => {
  return function MockFilterPanel({ filters, onFilterChange }) {
    return (
      <div data-testid="filter-panel">
        <span>Filter Panel</span>
        <button onClick={() => onFilterChange({ time_range: 'last_30_days' })}>Set 30 days</button>
      </div>
    );
  };
});

jest.mock('../components/KPICard', () => {
  return function MockKPICard({ title, value, change, icon, className }) {
    return (
      <div data-testid="kpi-card" className={className}>
        <span data-testid="kpi-title">{title}</span>
        <span data-testid="kpi-value">{value}</span>
        {change !== undefined && <span data-testid="kpi-change">{change}</span>}
      </div>
    );
  };
});

jest.mock('../components/EnhancedChart', () => {
  return function MockEnhancedChart({ title, type, data }) {
    return (
      <div data-testid="enhanced-chart" data-title={title}>
        <div>{title}</div>
      </div>
    );
  };
});


jest.mock('recharts', () => {
  return {
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
    AreaChart: () => <div data-testid="area-chart" />,
    Area: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
    CartesianGrid: () => <div />,
    Legend: () => <div />,
  };
});


import Dashboard from '../pages/Dashboard';


const mockKpis = [
  { id: '1', name: 'Total Comments', value: 1000, change: '+10%', icon: 'comment' },
  { id: '2', name: 'Average eNPS', value: 35, change: '-5%', icon: 'trending-up' },
];

const mockMonthlyComments = [
  { month: 'Jan', comments: 120 },
  { month: 'Feb', comments: 150 },
  { month: 'Mar', comments: 180 },
];

const mockMonthlyEnps = [
  { month: 'Jan', enps: 40 },
  { month: 'Feb', enps: 38 },
  { month: 'Mar', enps: 35 },
];

const mockTopicHotness = [
  {
    theme: 'Workload',
    hotness_score: 90,
    enps: 20,
    comment_count: 150,
    sub_themes: [
      { name: 'Work-Life Balance', score: 85, enps: 15, comment_count: 80 },
      { name: 'Task Volume', score: 95, enps: 25, comment_count: 70 },
    ],
  },
  {
    theme: 'Team Collaboration',
    hotness_score: 75,
    enps: 40,
    comment_count: 100,
    sub_themes: [],
  },
];

function setupAxiosSuccess() {
  axios.get
    .mockResolvedValueOnce({ data: mockKpis })
    .mockResolvedValueOnce({ data: mockMonthlyComments })
    .mockResolvedValueOnce({ data: mockMonthlyEnps })
    .mockResolvedValueOnce({ data: mockTopicHotness });
}

describe('Dashboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders Dashboard component without crashing', () => {
    const { container } = render(<Dashboard />);
    expect(container).toBeInTheDocument();
  });

  test('renders Dashboard with all data successfully', async () => {
    setupAxiosSuccess();
    const { container } = render(<Dashboard />);

    
    await waitFor(() => {
      expect(screen.queryByText(/loading data.../i)).not.toBeInTheDocument();
    });

    
    expect(container).toBeInTheDocument();
  });

  test('handles API errors gracefully', async () => {
    
    axios.get.mockRejectedValue(new Error('API Error'));
    
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    render(<Dashboard />);

    
    await waitFor(() => {
      expect(screen.queryByText(/loading data.../i)).not.toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  test('renders filter panel correctly', async () => {
    setupAxiosSuccess();
    render(<Dashboard />);

    
    expect(await screen.findByTestId('filter-panel')).toBeInTheDocument();
    expect(screen.getByText('Filter Panel')).toBeInTheDocument();
  });

  test('renders empty state when no data is available', async () => {
    
    axios.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.queryByText(/loading data.../i)).not.toBeInTheDocument();
    });
  });
});