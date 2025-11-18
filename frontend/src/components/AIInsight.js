import React, { useState, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import { useTheme } from '../context/ThemeContext';
import './AIInsight.css';

function AIInsight({ filters }) {
  const { isDarkMode } = useTheme();
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Debounce API call to avoid too many requests
    const timer = setTimeout(() => {
      fetchInsights();
    }, 500); // Wait 500ms after filter change

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const fetchInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${config.API_URL}/api/dashboard/ai-insights`, filters);
      
      if (response.data.insights && response.data.insights.length > 0) {
        setInsights(response.data.insights);
      } else {
        setInsights([]);
        if (response.data.error) {
          setError(response.data.error);
        } else if (response.data.message) {
          setError(null); // No data is not an error
        }
      }
    } catch (err) {
      console.error('Error fetching AI insights:', err);
      setError('Failed to load AI insights');
      setInsights([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="ai-insight card">
        <div className="ai-insight-header">
          <h3>
            <span className="ai-icon">🤖</span>
            AI Insights
          </h3>
        </div>
        <div className="ai-insight-loading">
          <div className="loading-spinner"></div>
          <span>Analyzing data...</span>
        </div>
      </div>
    );
  }

  // Don't show component if API key is not configured or no insights available
  if (error === 'OpenAI API key not configured' || (insights.length === 0 && !error)) {
    return null;
  }

  if (error) {
    return (
      <div className="ai-insight card">
        <div className="ai-insight-header">
          <h3>
            <span className="ai-icon">🤖</span>
            AI Insights
          </h3>
        </div>
        <div className="ai-insight-error">
          <span>⚠️ {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-insight card">
      <div className="ai-insight-header">
        <h3>
          <span className="ai-icon">🤖</span>
          AI Insights
        </h3>
        <span className="ai-badge">Powered by AI</span>
      </div>
      <div className="ai-insight-content">
        {insights.map((insight, index) => (
          <div key={index} className="insight-item" style={{ animationDelay: `${index * 0.1}s` }}>
            <div className="insight-header">
              <span className="insight-number">{index + 1}</span>
              <h4 className="insight-title">{insight.title}</h4>
            </div>
            <div className="insight-body">
              <p>{insight.content}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AIInsight;

