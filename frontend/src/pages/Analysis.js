import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, Area, AreaChart
} from 'recharts';
import { useTheme } from '../context/ThemeContext';
import AIChat from '../components/AIChat';
import config from '../config';
import './Analysis.css';

function Analysis() {
  const { isDarkMode } = useTheme();
  const [hotTopics, setHotTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [aiInsights, setAiInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [currentView, setCurrentView] = useState('default'); // 'default' or 'ai_generated'
  const [viewConfig, setViewConfig] = useState(null);
  const [customQueryData, setCustomQueryData] = useState(null);
  const [showAIChat, setShowAIChat] = useState(false);
  
  // Risk themes data
  const [riskyThemesData, setRiskyThemesData] = useState(null);
  // Positive themes data
  const [positiveThemesData, setPositiveThemesData] = useState(null);
  const [hoveredColumn, setHoveredColumn] = useState(null);
  const [themeInsights, setThemeInsights] = useState({});
  const [loadingInsights, setLoadingInsights] = useState(new Set());
  const [activeTheme, setActiveTheme] = useState(null);

  // Column descriptions for Analysis page
  const analysisColumnDescriptions = {
    'risk_score': {
      description: 'Risk level based on negative sentiment and volume.',
      calculation: '(Negative rate × 0.7) + (Volume factor × 0.3)'
    },
    'positive_score': {
      description: 'Positive rating based on positive sentiment and volume.',
      calculation: '(Positive rate × 0.7) + (Volume factor × 0.3)'
    },
    'enps': {
      description: 'Percentage of positive comments.',
      calculation: '(Positive / Total) × 100'
    },
    'total_comments': {
      description: 'Total comment count.',
      calculation: 'Comment count'
    },
    'yoy_comments': {
      description: 'Year-over-year change in comment count.',
      calculation: '((2025 - 2024) / 2024) × 100'
    },
    'yoy_enps': {
      description: 'Year-over-year change in eNPS.',
      calculation: '((2025 eNPS - 2024 eNPS) / 2024 eNPS) × 100'
    },
    'theme': {
      description: 'Comment topic category.',
      calculation: 'Database field'
    }
  };

  // Theme-aware colors
  const chartColors = {
    positive: isDarkMode ? '#81C784' : '#4CAF50',
    negative: isDarkMode ? '#e57373' : '#f44336',
    neutral: isDarkMode ? '#808080' : '#9e9e9e',
    primary: isDarkMode ? '#64B5F6' : '#2196F3',
    secondary: isDarkMode ? '#BA68C8' : '#9C27B0',
    warning: isDarkMode ? '#FFB74D' : '#FF9800',
    grid: isDarkMode ? '#3a3a3a' : '#e0e0e0',
    text: isDarkMode ? '#b3b3b3' : '#757575'
  };

  useEffect(() => {
    fetchRiskyThemes();
    fetchPositiveThemes();
  }, []);

  const fetchRiskyThemes = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${config.API_URL}/api/analysis/risky-themes`);
      setRiskyThemesData(response.data);
      setCurrentView('default');
    } catch (error) {
      console.error('Error fetching risky themes:', error);
    }
    setLoading(false);
  };

  const fetchPositiveThemes = async () => {
    try {
      const response = await axios.get(`${config.API_URL}/api/analysis/positive-themes`);
      setPositiveThemesData(response.data);
    } catch (error) {
      console.error('Error fetching positive themes:', error);
    }
  };

  const fetchThemeInsights = async (themeType, themeName) => {
    const insightKey = `${themeType}_${themeName}`;

    if (themeInsights[insightKey] || loadingInsights.has(insightKey)) {
      return;
    }

    setLoadingInsights(prev => new Set(prev).add(insightKey));

    try {
      const response = await axios.post(`${config.API_URL}/api/analysis/theme-insights`, {
        theme_type: themeType,
        theme_name: themeName
      });

      setThemeInsights(prev => ({
        ...prev,
        [insightKey]: response.data
      }));
    } catch (error) {
      console.error('Error fetching theme insights:', error);
      setThemeInsights(prev => ({
        ...prev,
        [insightKey]: {
          positive_summary: 'Unable to load insights.',
          negative_summary: 'Unable to load insights.',
          positive_recommendations: [],
          negative_recommendations: []
        }
      }));
    } finally {
      setLoadingInsights(prev => {
        const newSet = new Set(prev);
        newSet.delete(insightKey);
        return newSet;
      });
    }
  };

  const handleThemeInsightClick = (themeType, themeName, event) => {
    if (event) {
      event.stopPropagation();
    }
    const insightKey = `${themeType}_${themeName}`;
    setActiveTheme(insightKey);

    if (!themeInsights[insightKey] && !loadingInsights.has(insightKey)) {
      fetchThemeInsights(themeType, themeName);
    }
  };

  const handleCloseInsight = () => {
    setActiveTheme(null);
  };

  const fetchHotTopics = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${config.API_URL}/api/ai-analysis/hot-topics-sentiment`);
      setHotTopics(response.data.topics);
      // Select first topic by default
      if (response.data.topics.length > 0) {
        setSelectedTopic(response.data.topics[0]);
      }
      setCurrentView('hot_topics');
    } catch (error) {
      console.error('Error fetching hot topics:', error);
    }
    setLoading(false);
  };

  // AI Chat callback - update page data
  const handleAnalysisUpdate = (analysisData, visualizationConfig) => {
    if (!analysisData) return;
    
    setViewConfig(visualizationConfig);
    setCurrentView('ai_generated');
    
    // If AI generated insights, use them directly
    if (analysisData.ai_insights && analysisData.ai_insights.length > 0) {
      // Assign recommendations to each insight if insight doesn't have its own recommendations
      const recommendations = analysisData.recommendations || [];
      setAiInsights({
        insights: analysisData.ai_insights.map((insight, index) => ({
          theme: insight.title || 'General',
          key_findings: [insight.description || ''],
          recommendations: recommendations.length > 0 ? recommendations : [],
          risk_level: insight.importance === 'high' ? 'high' : insight.importance === 'low' ? 'low' : 'medium'
        })),
        generated_at: new Date().toISOString()
      });
    }
    
    // Handle custom SQL query results
    if (analysisData.raw_results && visualizationConfig?.query_type === 'custom') {
      // Convert custom query results to topic format
      const convertedTopics = convertRawResultsToTopics(analysisData.raw_results);
      setHotTopics(convertedTopics);
      if (convertedTopics.length > 0 && visualizationConfig?.auto_select_first) {
        setSelectedTopic(convertedTopics[0]);
      }
      // Custom query data stored but not displayed (removed Custom Query Results section)
    } 
    // Handle standard topic data
    else if (analysisData.topics) {
      setHotTopics(analysisData.topics);
      
      // Auto-select topic based on configuration
      if (visualizationConfig?.auto_select_first && analysisData.topics.length > 0) {
        setSelectedTopic(analysisData.topics[0]);
      }
      
      // If no AI insights but insights are needed
      if (!analysisData.ai_insights && visualizationConfig?.view_type === 'insights') {
        generateInsightsForTopics(analysisData.topics);
      }
    }
  };

  // Convert raw SQL results to topic format
  const convertRawResultsToTopics = (rawResults) => {
    if (!rawResults || rawResults.length === 0) return [];
    
    // Try to identify common query result formats
    const topics = [];
    
    rawResults.forEach((row, index) => {
      // If result contains base_theme, use it
      if (row.base_theme) {
        topics.push({
          theme: row.base_theme,
          hotness_score: row.count || row.total || index + 1,
          total_comments: row.count || row.total || 0,
          total_likes: row.likes || row.likes_sum || 0,
          sentiment_distribution: {
            positive: row.positive || row.positive_count || 0,
            negative: row.negative || row.negative_count || 0,
            neutral: row.neutral || row.neutral_count || 0,
            positive_rate: row.positive_rate || 0,
            negative_rate: row.negative_rate || 0,
            neutral_rate: row.neutral_rate || 0
          },
          daily_trends: [],
          sample_contents: []
        });
      } else {
        // Generic format: display all fields
        const themeName = Object.keys(row).find(k => k.includes('theme')) || 
                         Object.keys(row).find(k => k.includes('name')) || 
                         `Result ${index + 1}`;
        topics.push({
          theme: row[themeName] || themeName,
          hotness_score: row.count || row.total || index + 1,
          total_comments: row.count || row.total || 0,
          total_likes: row.likes || row.likes_sum || 0,
          sentiment_distribution: {
            positive: row.positive || row.positive_count || 0,
            negative: row.negative || row.negative_count || 0,
            neutral: row.neutral || row.neutral_count || 0,
            positive_rate: row.positive_rate || 0,
            negative_rate: row.negative_rate || 0,
            neutral_rate: row.neutral_rate || 0
          },
          daily_trends: [],
          sample_contents: [],
          raw_data: row // Save original data
        });
      }
    });
    
    return topics;
  };

  const generateInsightsForTopics = async (topics) => {
    setInsightsLoading(true);
    try {
      const response = await axios.post(`${config.API_URL}/api/ai-analysis/generate-insights`, {
        topics: topics
      });
      setAiInsights(response.data);
    } catch (error) {
      console.error('Error generating insights:', error);
    }
    setInsightsLoading(false);
  };

  const generateInsights = async () => {
    generateInsightsForTopics(hotTopics);
  };

  const formatSentimentData = (dailyTrends) => {
    return dailyTrends.map(day => ({
      date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      positive: day.positive_rate,
      negative: day.negative_rate,
      neutral: day.neutral_rate,
      total: day.total
    }));
  };

  const resetToDefault = () => {
    fetchHotTopics();
    setAiInsights(null);
    setViewConfig(null);
  };

  // Get risk color based on score
  const getRiskColor = (score) => {
    if (score >= 50) return '#d32f2f'; // Very High - dark red
    if (score >= 40) return '#f44336'; // High - red
    if (score >= 35) return '#FF5722'; // Moderate-High - orange
    if (score >= 25) return '#FF9800'; // Moderate - yellow-orange
    if (score >= 20) return '#FFC107'; // Low-Moderate - yellow
    if (score >= 5) return '#8BC34A'; // Low - yellow-green
    return '#4CAF50'; // Very Low - green
  };

  const getRiskLevelLabel = (score) => {
    if (score >= 50) return 'Very High';
    if (score >= 40) return 'High';
    if (score >= 35) return 'Moderate-High';
    if (score >= 25) return 'Moderate';
    if (score >= 20) return 'Low-Moderate';
    if (score >= 5) return 'Low';
    return 'Very Low';
  };

  // Get positive color based on score (inverse of risk color)
  const getPositiveColor = (score) => {
    if (score >= 50) return '#4CAF50'; // Very High - green
    if (score >= 40) return '#66BB6A'; // High - light green
    if (score >= 35) return '#81C784'; // Moderate-High - lighter green
    if (score >= 25) return '#A5D6A7'; // Moderate - very light green
    if (score >= 20) return '#C8E6C9'; // Low-Moderate - pale green
    if (score >= 5) return '#E8F5E9'; // Low - very pale green
    return '#F1F8E9'; // Very Low - almost white green
  };

  return (
    <div className="analysis-ai">
      <div className="page-header">
        <h2>Analysis</h2>
        {/* <p>Summary of results – Risk Assessment Dashboard</p> */}
        {currentView !== 'default' && (
          <button className="reset-btn" onClick={fetchRiskyThemes}>
            ↻ Back to Risk View
          </button>
        )}
        {/* {currentView === 'default' && (
          <button className="reset-btn" onClick={fetchHotTopics} style={{ marginLeft: '1rem' }}>
            View Hot Topics
          </button>
        )} */}
      </div>

      <div className="analysis-layout">
        {/* Analysis Content Section */}
        <div className="content-section">
          {loading ? (
            <div className="loading">Loading analysis data...</div>
          ) : (
            <>
              {/* Default Risk View */}
              {currentView === 'default' && riskyThemesData && (
                <div className="risk-dashboard">
                  {/* Top Section: Overall Metrics */}
                  <div className="risk-overview card">
                    <div className="overview-left">
                      <div className="metric-box">
                        <div className="metric-label">Number of posts & comments</div>
                        <div className="metric-value metric-purple">{riskyThemesData.total_responses}</div>
                      </div>
                      {/* <div className="metric-box">
                        <div className="metric-label">Overall risk rating</div>
                        <div className="metric-value metric-high">
                          {riskyThemesData.risk_level} ({riskyThemesData.overall_risk_rating} / 100)
                        </div>
                        <div className="metric-note">
                          This risk rating is calculated by assessing the cumulative risk of multiple psychosocial hazards.
                        </div>
                      </div> */}
                    </div>
                  </div>

                  {/* Main Content: Top 10 Positive Themes First, Then Negative Themes */}
                  <div className="risk-main-content">
                    {/* Top 10 Positive Themes */}
                    {positiveThemesData && (
                      <div className="risky-themes-list card">
                        <h3>Top 10 positive themes</h3>
                        <div className="themes-header">
                          <span className="header-hazards">
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              Themes
                              <span
                                className="column-info-icon"
                                onMouseEnter={() => setHoveredColumn('theme')}
                                onMouseLeave={() => setHoveredColumn(null)}
                              >
                                ℹ️
                              </span>
                              {hoveredColumn === 'theme' && (
                                <div className="column-info-tooltip">
                                  <p>{analysisColumnDescriptions.theme.description}</p>
                                  <p className="calculation">{analysisColumnDescriptions.theme.calculation}</p>
                                </div>
                              )}
                            </span>
                          </span>
                          <span className="header-rating">
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              Positive rating (n = {positiveThemesData.total_responses})
                              <span
                                className="column-info-icon"
                                onMouseEnter={() => setHoveredColumn('positive_score')}
                                onMouseLeave={() => setHoveredColumn(null)}
                              >
                                ℹ️
                              </span>
                              {hoveredColumn === 'positive_score' && (
                                <div className="column-info-tooltip">
                                  <p>{analysisColumnDescriptions.positive_score.description}</p>
                                  <p className="calculation">{analysisColumnDescriptions.positive_score.calculation}</p>
                                </div>
                              )}
                            </span>
                          </span>
                          <span className="header-comments">
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              Total Comments
                              <span
                                className="column-info-icon"
                                onMouseEnter={() => setHoveredColumn('total_comments')}
                                onMouseLeave={() => setHoveredColumn(null)}
                              >
                                ℹ️
                              </span>
                              {hoveredColumn === 'total_comments' && (
                                <div className="column-info-tooltip">
                                  <p>{analysisColumnDescriptions.total_comments.description}</p>
                                  <p className="calculation">{analysisColumnDescriptions.total_comments.calculation}</p>
                                </div>
                              )}
                            </span>
                          </span>
                          <span className="header-enps">
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              eNPS
                              <span
                                className="column-info-icon"
                                onMouseEnter={() => setHoveredColumn('enps')}
                                onMouseLeave={() => setHoveredColumn(null)}
                              >
                                ℹ️
                              </span>
                              {hoveredColumn === 'enps' && (
                                <div className="column-info-tooltip">
                                  <p>{analysisColumnDescriptions.enps.description}</p>
                                  <p className="calculation">{analysisColumnDescriptions.enps.calculation}</p>
                                </div>
                              )}
                            </span>
                          </span>
                        </div>
                        <div className="themes-list">
                          {positiveThemesData.positive_themes.map((theme, index) => {
                            // Use green gradient for positive scores
                            const positiveColor = getPositiveColor(theme.positive_score);
                            const commentsChangeColor = theme.comments_yoy_change >= 0 ? chartColors.positive : chartColors.negative;
                            const enpsChangeColor = theme.enps_yoy_change >= 0 ? chartColors.positive : chartColors.negative;
                            return (
                              <div key={index} className="theme-item">
                                <div className="theme-name">
                                  {theme.sub_theme}
                                  <span
                                    className="theme-insight-icon"
                                    onClick={(e) => handleThemeInsightClick('sub_theme', theme.sub_theme, e)}
                                    role="button"
                                    aria-label={`View insights for ${theme.sub_theme}`}
                                  >
                                    💡
                                  </span>
                                </div>
                                <div className="theme-rating-container">
                                  <div className="theme-rating-bar-container">
                                    <div 
                                      className="theme-rating-bar"
                                      style={{
                                        width: `${theme.positive_score}%`,
                                        backgroundColor: positiveColor
                                      }}
                                    />
                                  </div>
                                  <span className="theme-rating-value">{theme.positive_score}</span>
                                </div>
                                <div className="theme-comments">
                                  <span className="metric-value-number">{theme.total_count}</span>
                                  <span 
                                    className="yoy-change"
                                    style={{ color: commentsChangeColor }}
                                  >
                                    {theme.comments_yoy_change >= 0 ? '↑' : '↓'} {Math.abs(theme.comments_yoy_change)}%
                                  </span>
                                </div>
                                <div className="theme-enps">
                                  <span className="metric-value-number">{theme.enps}%</span>
                                  <span 
                                    className="yoy-change"
                                    style={{ color: enpsChangeColor }}
                                  >
                                    {theme.enps_yoy_change >= 0 ? '↑' : '↓'} {Math.abs(theme.enps_yoy_change)}%
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        <div className="risk-legend">
                          <div className="legend-title">Score Ranges:</div>
                          <div className="legend-items">
                            <span>Very Low: &lt;5</span>
                            <span>Low: 5-19</span>
                            <span>Low-moderate: 20-24</span>
                            <span>Moderate: 25-34</span>
                            <span>Moderate-high: 35-39</span>
                            <span>High: 40-50</span>
                            <span>Very high: &gt;50</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Top 10 Negative Themes (Hazards) */}
                    <div className="risky-themes-list card" style={{ marginTop: positiveThemesData ? '2rem' : '0' }}>
                      <h3>Top 10 negative themes</h3>
                      <div className="themes-header">
                        <span className="header-hazards">
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            Themes
                            <span
                              className="column-info-icon"
                              onMouseEnter={() => setHoveredColumn('theme')}
                              onMouseLeave={() => setHoveredColumn(null)}
                            >
                              ℹ️
                            </span>
                            {hoveredColumn === 'theme' && (
                              <div className="column-info-tooltip">
                                <p>{analysisColumnDescriptions.theme.description}</p>
                                <p className="calculation">{analysisColumnDescriptions.theme.calculation}</p>
                              </div>
                            )}
                          </span>
                        </span>
                        <span className="header-rating">
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            Overall rating (n = {riskyThemesData.total_responses})
                            <span
                              className="column-info-icon"
                              onMouseEnter={() => setHoveredColumn('risk_score')}
                              onMouseLeave={() => setHoveredColumn(null)}
                            >
                              ℹ️
                            </span>
                            {hoveredColumn === 'risk_score' && (
                              <div className="column-info-tooltip">
                                <p>{analysisColumnDescriptions.risk_score.description}</p>
                                <p className="calculation">{analysisColumnDescriptions.risk_score.calculation}</p>
                              </div>
                            )}
                          </span>
                        </span>
                        <span className="header-comments">
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            Total Comments
                            <span
                              className="column-info-icon"
                              onMouseEnter={() => setHoveredColumn('total_comments')}
                              onMouseLeave={() => setHoveredColumn(null)}
                            >
                              ℹ️
                            </span>
                            {hoveredColumn === 'total_comments' && (
                              <div className="column-info-tooltip">
                                <p>{analysisColumnDescriptions.total_comments.description}</p>
                                <p className="calculation">{analysisColumnDescriptions.total_comments.calculation}</p>
                              </div>
                            )}
                          </span>
                        </span>
                        <span className="header-enps">
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            eNPS
                            <span
                              className="column-info-icon"
                              onMouseEnter={() => setHoveredColumn('enps')}
                              onMouseLeave={() => setHoveredColumn(null)}
                            >
                              ℹ️
                            </span>
                            {hoveredColumn === 'enps' && (
                              <div className="column-info-tooltip">
                                <p>{analysisColumnDescriptions.enps.description}</p>
                                <p className="calculation">{analysisColumnDescriptions.enps.calculation}</p>
                              </div>
                            )}
                          </span>
                        </span>
                      </div>
                      <div className="themes-list">
                        {riskyThemesData.risky_themes.map((theme, index) => {
                          const riskColor = getRiskColor(theme.risk_score);
                          const commentsChangeColor = theme.comments_yoy_change >= 0 ? chartColors.negative : chartColors.positive;
                          const enpsChangeColor = theme.enps_yoy_change >= 0 ? chartColors.positive : chartColors.negative;
                          return (
                            <div key={index} className="theme-item">
                              <div className="theme-name">
                                {theme.sub_theme}
                                <span
                                  className="theme-insight-icon"
                                  onClick={(e) => handleThemeInsightClick('sub_theme', theme.sub_theme, e)}
                                  role="button"
                                  aria-label={`View insights for ${theme.sub_theme}`}
                                >
                                  💡
                                </span>
                              </div>
                              <div className="theme-rating-container">
                                <div className="theme-rating-bar-container">
                                  <div 
                                    className="theme-rating-bar"
                                    style={{
                                      width: `${theme.risk_score}%`,
                                      backgroundColor: riskColor
                                    }}
                                  />
                                </div>
                                <span className="theme-rating-value">{theme.risk_score}</span>
                              </div>
                              <div className="theme-comments">
                                <span className="metric-value-number">{theme.total_count}</span>
                                <span 
                                  className="yoy-change"
                                  style={{ color: commentsChangeColor }}
                                >
                                  {theme.comments_yoy_change >= 0 ? '↑' : '↓'} {Math.abs(theme.comments_yoy_change)}%
                                </span>
                              </div>
                              <div className="theme-enps">
                                <span className="metric-value-number">{theme.enps}%</span>
                                <span 
                                  className="yoy-change"
                                  style={{ color: enpsChangeColor }}
                                >
                                  {theme.enps_yoy_change >= 0 ? '↑' : '↓'} {Math.abs(theme.enps_yoy_change)}%
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div className="risk-legend">
                        <div className="legend-title">Score Ranges:</div>
                        <div className="legend-items">
                          <span>Very Low: &lt;5</span>
                          <span>Low: 5-19</span>
                          <span>Low-moderate: 20-24</span>
                          <span>Moderate: 25-34</span>
                          <span>Moderate-high: 35-39</span>
                          <span>High: 40-50</span>
                          <span>Very high: &gt;50</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Hot Topics Section - Only show when not in default risk view */}
              {(currentView === 'hot_topics' || currentView === 'ai_generated') && (
              <div className="hot-topics-section">
                <div className="section-header">
                  <h3>
                    {currentView === 'ai_generated' 
                      ? `${viewConfig?.view_type === 'comparison' ? 'Comparison' : viewConfig?.view_type === 'sentiment_trend' ? 'Sentiment Trends' : viewConfig?.view_type === 'insights' ? 'AI Insights' : viewConfig?.view_type === 'custom_query' ? 'Custom Query Results' : 'Filtered Topics'}`
                      : 'Hot Topics (Last 30 Days)'}
                  </h3>
                  {/* {currentView === 'hot_topics' && (
                    <button 
                      className="btn-generate-insights"
                      onClick={generateInsights}
                      disabled={insightsLoading}
                    >
                      {insightsLoading ? '🔄 Generating...' : '✨ Generate AI Insights'}
                    </button>
                  )} */}
                </div>

                <div className="topics-grid">
                  <div className="topics-list card">
                    <h4>
                      {viewConfig?.highlight_sentiment 
                        ? `Top Topics by ${viewConfig.highlight_sentiment === 'negative' ? 'Negative' : 'Positive'} Sentiment`
                        : 'Top Topics by Engagement'}
                    </h4>
                    <div className="topics-container">
                      {hotTopics.map((topic, index) => (
                        <div
                          key={topic.theme}
                          className={`topic-item ${selectedTopic?.theme === topic.theme ? 'selected' : ''} ${
                            viewConfig?.highlight_sentiment === 'negative' && topic.sentiment_distribution.negative_rate > 40 ? 'high-negative' :
                            viewConfig?.highlight_sentiment === 'positive' && topic.sentiment_distribution.positive_rate > 60 ? 'high-positive' : ''
                          }`}
                          onClick={() => setSelectedTopic(topic)}
                        >
                          <div className="topic-rank">#{index + 1}</div>
                          <div className="topic-info">
                            <div className="topic-name">{topic.theme}</div>
                            <div className="topic-stats">
                              <span className="stat">
                                💬 {topic.total_comments} comments
                              </span>
                              <span className="stat">
                                👍 {topic.total_likes} likes
                              </span>
                            </div>
                          </div>
                          <div className="topic-score">
                            <div className="score-label">
                              {viewConfig?.highlight_sentiment === 'negative' ? 'Negative' :
                               viewConfig?.highlight_sentiment === 'positive' ? 'Positive' : 'Score'}
                            </div>
                            <div className="score-value">
                              {viewConfig?.highlight_sentiment === 'negative' 
                                ? `${topic.sentiment_distribution.negative_rate}%` :
                               viewConfig?.highlight_sentiment === 'positive'
                                ? `${topic.sentiment_distribution.positive_rate}%` :
                                topic.hotness_score}
                            </div>
                          </div>
                        </div>
                      ))}
                      {hotTopics.length === 0 && (
                        <div className="no-topics">
                          No topics found for the selected criteria. Try adjusting your search.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Selected Topic Details */}
                  {selectedTopic && (
                    <div className="topic-details card">
                      <h4>{selectedTopic.theme} - Detailed Analysis</h4>
                      
                      {/* Sentiment Distribution Pie Chart */}
                      <div className="chart-container">
                        <h5>Sentiment Distribution</h5>
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={[
                                { name: 'Positive', value: selectedTopic.sentiment_distribution.positive_rate },
                                { name: 'Negative', value: selectedTopic.sentiment_distribution.negative_rate },
                                { name: 'Neutral', value: selectedTopic.sentiment_distribution.neutral_rate }
                              ]}
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({name, value}) => `${name}: ${value}%`}
                              outerRadius={80}
                              fill="#8884d8"
                              dataKey="value"
                            >
                              <Cell fill={chartColors.positive} />
                              <Cell fill={chartColors.negative} />
                              <Cell fill={chartColors.neutral} />
                            </Pie>
                            <Tooltip />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>

                      {/* Sample Comments */}
                      <div className="sample-comments">
                        <h5>Sample Comments</h5>
                        <div className="comments-list">
                          {selectedTopic.sample_contents.map((content, idx) => (
                            <div key={idx} className="sample-comment">
                              "{content}..."
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Sentiment Trend Chart */}
                {selectedTopic && selectedTopic.daily_trends && selectedTopic.daily_trends.length > 0 && (
                  <div className="sentiment-trend card">
                    <h4>{selectedTopic.theme} - Sentiment Trend Over Time</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={formatSentimentData(selectedTopic.daily_trends)}>
                        <defs>
                          <linearGradient id="colorPositive" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={chartColors.positive} stopOpacity={0.8}/>
                            <stop offset="95%" stopColor={chartColors.positive} stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="colorNegative" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={chartColors.negative} stopOpacity={0.8}/>
                            <stop offset="95%" stopColor={chartColors.negative} stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="colorNeutral" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={chartColors.neutral} stopOpacity={0.8}/>
                            <stop offset="95%" stopColor={chartColors.neutral} stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                        <XAxis dataKey="date" stroke={chartColors.text} />
                        <YAxis stroke={chartColors.text} label={{ value: 'Percentage (%)', angle: -90, position: 'insideLeft' }} />
                        <Tooltip />
                        <Legend />
                        <Area 
                          type="monotone" 
                          dataKey="positive" 
                          stackId="1"
                          stroke={chartColors.positive} 
                          fillOpacity={1}
                          fill="url(#colorPositive)" 
                          name="Positive %"
                        />
                        <Area 
                          type="monotone" 
                          dataKey="negative" 
                          stackId="1"
                          stroke={chartColors.negative} 
                          fillOpacity={1}
                          fill="url(#colorNegative)" 
                          name="Negative %"
                        />
                        <Area 
                          type="monotone" 
                          dataKey="neutral" 
                          stackId="1"
                          stroke={chartColors.neutral} 
                          fillOpacity={1}
                          fill="url(#colorNeutral)" 
                          name="Neutral %"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
              )}

              {/* AI Insights Section */}
              {/* {(aiInsights || (currentView === 'ai_generated' && viewConfig?.view_type === 'insights')) && (
                <div className="ai-insights-section">
                  <div className="section-header">
                    <h3>🧠 AI-Generated Insights</h3>
                    {aiInsights && (
                      <span className="insight-meta">
                        Generated at {new Date(aiInsights.generated_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  
                  {insightsLoading ? (
                    <div className="loading">Generating insights...</div>
                  ) : aiInsights ? (
                    <div className="insights-grid">
                      {aiInsights.insights.map((insight, index) => (
                        <div key={index} className={`insight-card card risk-${insight.risk_level}`}>
                          <div className="insight-header">
                            <h4>{insight.theme}</h4>
                            <span className={`risk-badge ${insight.risk_level}`}>
                              {insight.risk_level === 'high' ? '🔴' : insight.risk_level === 'medium' ? '🟡' : '🟢'} 
                              {insight.risk_level} priority
                            </span>
                          </div>
                          
                          <div className="insight-content">
                            <div className="findings">
                              <h5>Key Findings:</h5>
                              <ul>
                                {insight.key_findings.map((finding, idx) => (
                                  <li key={idx}>{finding}</li>
                                ))}
                              </ul>
                            </div>
                            
                            {insight.recommendations && insight.recommendations.length > 0 && (
                              <div className="recommendations">
                                <h5>Recommendations:</h5>
                                <ul>
                                  {insight.recommendations.map((rec, idx) => (
                                    <li key={idx}>{rec}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              )} */}
            </>
          )}
        </div>
      </div>

      {/* Floating AI Chat Button */}
      {!showAIChat && (
        <button 
          className="floating-ai-button"
          onClick={() => setShowAIChat(true)}
          title="Open AI Assistant"
        >
          🤖
        </button>
      )}

      {/* Floating Draggable AI Chat */}
      {showAIChat && (
        <AIChat 
          onAnalysisUpdate={handleAnalysisUpdate}
          onClose={() => setShowAIChat(false)}
          isFloating={true}
        />
      )}
      {/* Insight Modal */}
      {activeTheme && (
        <>
          <div 
            className="insight-modal-overlay"
            onClick={handleCloseInsight}
          />
          <div className="insight-modal">
            <div className="insight-modal-header">
              <h3>AI Insights</h3>
              <button 
                className="insight-modal-close"
                onClick={handleCloseInsight}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="insight-modal-content">
              {loadingInsights.has(activeTheme) ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>Loading insights...</div>
              ) : themeInsights[activeTheme] ? (
                <div>
                  {themeInsights[activeTheme].positive_summary && (
                    <div className="insight-section positive">
                      <h4>✅ Strengths</h4>
                      <p>{themeInsights[activeTheme].positive_summary}</p>
                      {themeInsights[activeTheme].positive_recommendations?.length > 0 && (
                        <ul>
                          {themeInsights[activeTheme].positive_recommendations.map((rec, idx) => (
                            <li key={idx}>{rec}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {themeInsights[activeTheme].negative_summary && (
                    <div className="insight-section negative">
                      <h4>⚠️ Opportunities</h4>
                      <p>{themeInsights[activeTheme].negative_summary}</p>
                      {themeInsights[activeTheme].negative_recommendations?.length > 0 && (
                        <ul>
                          {themeInsights[activeTheme].negative_recommendations.map((rec, idx) => (
                            <li key={idx}>{rec}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '2rem' }}>No insights available</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Analysis;