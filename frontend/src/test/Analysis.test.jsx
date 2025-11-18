// __tests__/Analysis.test.jsx
import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock axios with a factory so Jest never imports the real ESM module
jest.mock('axios', () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn() },
  get: jest.fn(),
  post: jest.fn(),
}));
import axios from 'axios';

// ---- 1) Base mocks ----
jest.mock('../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../config', () => ({
  __esModule: true,
  default: { API_URL: 'http://localhost:3000' },
}));

jest.mock('./Analysis.css', () => ({}), { virtual: true });

// Recharts' ResponsiveContainer has no size in JSDOM; provide a lightweight mock.
jest.mock('recharts', () => {
  const Recharts = jest.requireActual('recharts');
  const MockResponsiveContainer = ({ width, height, children }) => (
    <div data-testid="mock-responsive" style={{ width: width || 800, height: height || 300 }}>
      {children}
    </div>
  );
  return {
    ...Recharts,
    ResponsiveContainer: MockResponsiveContainer,
  };
});

// ---- 2) Mock AIChat: expose a button to call onAnalysisUpdate to test Analysis view switching ----
jest.mock('../components/AIChat', () => {
  return function MockAIChat({ onAnalysisUpdate, onClose }) {
    const aiPayload = {
      topics: [
        {
          theme: 'Workload',
          hotness_score: 95,
          total_comments: 30,
          total_likes: 120,
          sentiment_distribution: {
            positive: 5, negative: 20, neutral: 5,
            positive_rate: 20, negative_rate: 60, neutral_rate: 20
          },
          daily_trends: [],
          sample_contents: ['Too many tasks', 'No time for breaks'],
        },
        {
          theme: 'Belonging',
          hotness_score: 70,
          total_comments: 18,
          total_likes: 40,
          sentiment_distribution: {
            positive: 50, negative: 20, neutral: 30,
            positive_rate: 50, negative_rate: 20, neutral_rate: 30
          },
          daily_trends: [],
          sample_contents: ['Great team vibe'],
        }
      ],
      recommendations: ['Improve workload balance', 'Increase headcount'],
      ai_insights: [
        { title: 'Workload', description: 'High workload risk', importance: 'high' },
      ],
      generated_at: new Date().toISOString(),
    };
    const viewConfig = { view_type: 'insights', highlight_sentiment: 'negative', auto_select_first: true };

    return (
      <div data-testid="mock-aichat">
        <button
          data-testid="mock-aichat-update"
          onClick={() => onAnalysisUpdate && onAnalysisUpdate(aiPayload, viewConfig)}
        >
          Trigger Page Update
        </button>
        <button data-testid="mock-aichat-close" onClick={onClose}>Close</button>
      </div>
    );
  };
});

// SUT
import Analysis from '../pages/Analysis';

// ---- 3) Fixtures ----
const mockRiskyThemes = {
  total_responses: 123,
  risk_level: 'High',
  overall_risk_rating: 42,
  risky_themes: [
    {
      sub_theme: 'Workload',
      risk_score: 45,
      total_count: 50,
      comments_yoy_change: 12,
      enps: 20,
      enps_yoy_change: -5,
    },
    {
      sub_theme: 'Role Clarity',
      risk_score: 28,
      total_count: 22,
      comments_yoy_change: -7,
      enps: 35,
      enps_yoy_change: 10,
    },
  ],
};

const mockPositiveThemes = {
  total_responses: 123,
  positive_themes: [
    {
      sub_theme: 'Team Support',
      positive_score: 44,
      total_count: 30,
      comments_yoy_change: 5,
      enps: 55,
      enps_yoy_change: 8,
    },
  ],
};

// Order: component mount will call get risky-themes -> get positive-themes
function setupAxiosSuccess() {
  axios.get
    .mockResolvedValueOnce({ data: mockRiskyThemes })
    .mockResolvedValueOnce({ data: mockPositiveThemes });
  // .mockResolvedValueOnce({ data: { topics: [] } });
}

describe('Analysis Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('initial render: shows overall risk and top lists; positive themes appear', async () => {
    setupAxiosSuccess();
    render(<Analysis />);

    // Loading state
    expect(screen.getByText(/Loading analysis data/i)).toBeInTheDocument();

    // Wait for data to render
    await waitFor(() => {
      expect(screen.getByText('Analysis')).toBeInTheDocument();
      expect(screen.getByText(/Overall risk rating/i)).toBeInTheDocument();
      expect(screen.getByText(/High \(42 \/ 100\)/)).toBeInTheDocument();
    });

    // Risky themes
    expect(screen.getByText(/Top 10 hazards/i)).toBeInTheDocument();
    expect(screen.getByText('Workload')).toBeInTheDocument();
    expect(screen.getByText('Role Clarity')).toBeInTheDocument();

    // Positive themes
    expect(await screen.findByText(/Top 10 positive themes/i)).toBeInTheDocument();
    expect(screen.getByText('Team Support')).toBeInTheDocument();

    // Default view should not show "Back to Risk View"
    expect(screen.queryByText(/Back to Risk View/i)).not.toBeInTheDocument();
  });

  test('when positive-themes API fails, default risk view still renders', async () => {
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    axios.get
      .mockResolvedValueOnce({ data: mockRiskyThemes })
      .mockRejectedValueOnce(new Error('positive failed'));
    render(<Analysis />);

    await waitFor(() => {
      expect(screen.getByText(/Overall risk rating/i)).toBeInTheDocument();
    });

    // Positive themes block should not appear
    expect(screen.queryByText(/Top 10 positive themes/i)).not.toBeInTheDocument();

    errSpy.mockRestore();
  });

  test('open floating AI, trigger onAnalysisUpdate to switch to ai_generated view, then return to risk view', async () => {
    setupAxiosSuccess();
    render(<Analysis />);

    await waitFor(() => {
      expect(screen.getByText(/Overall risk rating/i)).toBeInTheDocument();
    });

    // Keep the emoji button name
    const floatBtn = screen.getByRole('button', { name: '🤖' });
    fireEvent.click(floatBtn);

    // Mocked AIChat appears
    const aiChat = await screen.findByTestId('mock-aichat');
    expect(aiChat).toBeInTheDocument();

    // Trigger onAnalysisUpdate (simulate AI returning data)
    const updateBtn = within(aiChat).getByTestId('mock-aichat-update');
    fireEvent.click(updateBtn);

    // Title switches to AI Insights (driven by viewConfig.view_type)
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: /AI Insights/i })).toBeInTheDocument();
    });

    // Topics list exists and includes "Workload"
    expect(screen.getByText(/Top Topics by Negative Sentiment/i)).toBeInTheDocument();
    expect(screen.getAllByText('Workload')[0]).toBeInTheDocument();

    // Click topic to show details on the right
    fireEvent.click(screen.getAllByText('Workload')[0]);
    expect(await screen.findByText(/Workload - Detailed Analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/Sentiment Distribution/i)).toBeInTheDocument();

    axios.get
      .mockResolvedValueOnce({ data: mockRiskyThemes })
      .mockResolvedValueOnce({ data: mockPositiveThemes });

    // "Back to Risk View" should appear; click to return to default
    const backBtn = screen.getByRole('button', { name: /Back to Risk View/i });
    fireEvent.click(backBtn);

    await waitFor(() => {
      expect(screen.getByText(/Top 10 hazards/i)).toBeInTheDocument();
    });
    // After returning, AI view title should be gone
    expect(screen.queryByRole('heading', { level: 3, name: /AI Insights/i })).not.toBeInTheDocument();
  });
});
