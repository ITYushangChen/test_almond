import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useTheme } from '../context/ThemeContext';
import FilterPanel from '../components/FilterPanel';
import KPICard from '../components/KPICard';
import EnhancedChart from '../components/EnhancedChart';
// import AIInsight from '../components/AIInsight'; // Temporarily disabled
import config from '../config';
import './Dashboard.css';

function Dashboard() {
  const { isDarkMode } = useTheme();
  const [filters, setFilters] = useState({
    base_themes: [],
    sub_themes: [],
    languages: [],
    start_date: '',
    end_date: '',
  });
  const [kpis, setKpis] = useState({
    total_comments: 0,
    positive_comments: 0,
    negative_comments: 0,
    enps: 0,
  });
  const [monthlyComments, setMonthlyComments] = useState([]);
  const [monthlyEnps, setMonthlyEnps] = useState([]);
  const [topicHotness, setTopicHotness] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedThemes, setExpandedThemes] = useState(new Set());
  const [subThemeData, setSubThemeData] = useState({});
  const [loadingSubThemes, setLoadingSubThemes] = useState(new Set());
  const [themeInsights, setThemeInsights] = useState({});
  const [loadingInsights, setLoadingInsights] = useState(new Set());
  const [activeTheme, setActiveTheme] = useState(null);
  const [hoveredColumn, setHoveredColumn] = useState(null);

  // Column descriptions
  const columnDescriptions = {
    'hotness_score': {
      description: 'Sum of all likes. Higher = more engagement.',
      calculation: 'Sum of likes'
    },
    'enps': {
      description: 'Percentage of positive comments.',
      calculation: '(Positive / Total) × 100'
    },
    'total_comments': {
      description: 'Total comment count.',
      calculation: 'Comment count'
    },
    'theme': {
      description: 'Comment topic category.',
      calculation: 'Database field'
    }
  };

  // Theme-aware chart colors
  const chartColors = {
    blue: isDarkMode ? '#64B5F6' : '#2196F3',
    green: isDarkMode ? '#81C784' : '#4CAF50',
    purple: isDarkMode ? '#BA68C8' : '#9C27B0',
    grid: isDarkMode ? '#3a3a3a' : '#e0e0e0',
    text: isDarkMode ? '#b3b3b3' : '#757575'
  };

  useEffect(() => {
    fetchAllData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [kpisRes, commentsRes, enpsRes, hotnessRes] = await Promise.all([
        axios.post(`${config.API_URL}/api/dashboard/kpis`, filters),
        axios.post(`${config.API_URL}/api/analysis/monthly-comments`, filters),
        axios.post(`${config.API_URL}/api/analysis/monthly-enps`, filters),
        axios.post(`${config.API_URL}/api/analysis/topic-hotness`, filters),
      ]);

      setKpis(kpisRes.data);
      setMonthlyComments(commentsRes.data || []);
      setMonthlyEnps(enpsRes.data || []);
      setTopicHotness(hotnessRes.data || []);
      
      // Debug: Log data to check if it's being received
      console.log('Monthly Comments:', commentsRes.data);
      console.log('Monthly eNPS:', enpsRes.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      // Set empty arrays on error to prevent undefined errors
      setMonthlyComments([]);
      setMonthlyEnps([]);
      setTopicHotness([]);
    }
    setLoading(false);
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    // Clear expanded themes and sub-theme data when filters change
    setExpandedThemes(new Set());
    setSubThemeData({});
    // Clear insights cache when filters change
    setThemeInsights({});
    setActiveTheme(null);
  };

  const handleThemeClick = async (baseTheme) => {
    const isExpanded = expandedThemes.has(baseTheme);
    
    if (isExpanded) {
      // Collapse: remove from expanded set
      const newExpanded = new Set(expandedThemes);
      newExpanded.delete(baseTheme);
      setExpandedThemes(newExpanded);
    } else {
      // Expand: add to expanded set and fetch sub_theme data
      const newExpanded = new Set(expandedThemes);
      newExpanded.add(baseTheme);
      setExpandedThemes(newExpanded);
      
      // If data not already loaded, fetch it
      if (!subThemeData[baseTheme]) {
        setLoadingSubThemes(prev => new Set(prev).add(baseTheme));
        try {
          const response = await axios.post(`${config.API_URL}/api/analysis/sub-theme-hotness`, {
            base_theme: baseTheme,
            filters: filters
          });
          setSubThemeData(prev => ({
            ...prev,
            [baseTheme]: response.data
          }));
        } catch (error) {
          console.error('Error fetching sub-theme data:', error);
          setSubThemeData(prev => ({
            ...prev,
            [baseTheme]: []
          }));
        } finally {
          setLoadingSubThemes(prev => {
            const newSet = new Set(prev);
            newSet.delete(baseTheme);
            return newSet;
          });
        }
      }
    }
  };

  const fetchThemeInsights = async (themeType, themeName) => {
    const insightKey = `${themeType}_${themeName}`;
    
    // If already loaded, don't fetch again
    if (themeInsights[insightKey]) {
      return;
    }
    
    // If already loading, don't fetch again
    if (loadingInsights.has(insightKey)) {
      return;
    }
    
    setLoadingInsights(prev => new Set(prev).add(insightKey));
    
    try {
      const response = await axios.post(`${config.API_URL}/api/analysis/theme-insights`, {
        theme_type: themeType,
        theme_name: themeName,
        filters: filters
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

  const handleThemeIconClick = (themeType, themeName, event) => {
    event.stopPropagation(); // Prevent row click
    const insightKey = `${themeType}_${themeName}`;
    setActiveTheme(insightKey);
    
    // Fetch insights if not already loaded
    if (!themeInsights[insightKey] && !loadingInsights.has(insightKey)) {
      fetchThemeInsights(themeType, themeName);
    }
  };

  const handleCloseInsight = () => {
    setActiveTheme(null);
  };

  return (
    <div className="dashboard">
      <div className="page-header">
        <h2>Dashboard</h2>
        {/* <p>Track key sentiment metrics and employee engagement</p> */}
      </div>

      <FilterPanel onFilterChange={handleFilterChange} />

      {/* <AIInsight filters={filters} /> */}

      {loading ? (
        <div className="loading">Loading dashboard data...</div>
      ) : (
        <>
          {/* KPI Cards Section */}
          <div className="kpi-grid">
            <KPICard
              title="Total Comments"
              value={kpis.total_comments}
              icon="💬"
              color="#3b82f6"
            />
            <KPICard
              title="Positive Comments"
              value={kpis.positive_comments}
              icon="👍"
              color="#10b981"
            />
            <KPICard
              title="Negative Comments"
              value={kpis.negative_comments}
              icon="👎"
              color="#ef4444"
            />
            <KPICard
              title="eNPS Score"
              value={`${kpis.enps}%`}
              icon="📊"
              color="#8b5cf6"
            />
          </div>

          {/* Charts Section */}
          <div className="charts-section">
            <div className="chart-card card">
              <h3>Monthly Comment Volume</h3>
              {monthlyComments.length > 0 ? (
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={monthlyComments} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorCommentsGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartColors.blue} stopOpacity={0.8}/>
                        <stop offset="95%" stopColor={chartColors.blue} stopOpacity={0.15}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid 
                      strokeDasharray="3 3" 
                      stroke={chartColors.grid} 
                      strokeOpacity={0.2}
                      vertical={false}
                    />
                    <XAxis 
                      dataKey="month" 
                      stroke={chartColors.text}
                      tick={{ fill: chartColors.text, fontSize: 12 }}
                      tickLine={{ stroke: chartColors.grid }}
                      axisLine={{ stroke: chartColors.grid }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis 
                      stroke={chartColors.text}
                      tick={{ fill: chartColors.text, fontSize: 12 }}
                      tickLine={{ stroke: chartColors.grid }}
                      axisLine={{ stroke: chartColors.grid }}
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
                        border: `1px solid ${chartColors.grid}`,
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                        padding: '12px'
                      }}
                      labelStyle={{
                        color: chartColors.text,
                        fontWeight: 600,
                        marginBottom: '8px'
                      }}
                      itemStyle={{
                        color: chartColors.text
                      }}
                    />
                    <Legend 
                      wrapperStyle={{ paddingTop: '20px' }}
                      iconType="circle"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="count" 
                      stroke={chartColors.blue}
                      strokeWidth={3}
                      fill="url(#colorCommentsGradient)"
                      name="Comments"
                      dot={{ r: 4, fill: chartColors.blue, strokeWidth: 2, stroke: '#fff' }}
                      activeDot={{ r: 7, fill: chartColors.blue, strokeWidth: 2, stroke: '#fff' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: chartColors.text }}>
                  No data available
                </div>
              )}
            </div>

            <div className="chart-card card">
              <h3>Monthly eNPS Trend</h3>
              {monthlyEnps.length > 0 ? (
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={monthlyEnps} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorEnpsGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartColors.green} stopOpacity={0.8}/>
                        <stop offset="95%" stopColor={chartColors.green} stopOpacity={0.15}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid 
                      strokeDasharray="3 3" 
                      stroke={chartColors.grid} 
                      strokeOpacity={0.2}
                      vertical={false}
                    />
                    <XAxis 
                      dataKey="month" 
                      stroke={chartColors.text}
                      tick={{ fill: chartColors.text, fontSize: 12 }}
                      tickLine={{ stroke: chartColors.grid }}
                      axisLine={{ stroke: chartColors.grid }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis 
                      stroke={chartColors.text}
                      tick={{ fill: chartColors.text, fontSize: 12 }}
                      tickLine={{ stroke: chartColors.grid }}
                      axisLine={{ stroke: chartColors.grid }}
                      domain={[0, 100]}
                      label={{ value: 'eNPS %', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: chartColors.text } }}
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
                        border: `1px solid ${chartColors.grid}`,
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                        padding: '12px'
                      }}
                      labelStyle={{
                        color: chartColors.text,
                        fontWeight: 600,
                        marginBottom: '8px'
                      }}
                      itemStyle={{
                        color: chartColors.text
                      }}
                      formatter={(value) => [`${value}%`, 'eNPS']}
                    />
                    <Legend 
                      wrapperStyle={{ paddingTop: '20px' }}
                      iconType="circle"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="enps" 
                      stroke={chartColors.green}
                      strokeWidth={3}
                      fill="url(#colorEnpsGradient)"
                      name="eNPS %"
                      dot={{ r: 4, fill: chartColors.green, strokeWidth: 2, stroke: '#fff' }}
                      activeDot={{ r: 7, fill: chartColors.green, strokeWidth: 2, stroke: '#fff' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: chartColors.text }}>
                  No data available
                </div>
              )}
            </div>
          </div>

          {/* Topic Hotness Table */}
          <div className="hotness-section card">
            <h3>Topic Hotness vs Sentiment Drop</h3>
            {/* <p className="section-description">
              High engagement topics with sentiment analysis.
            </p> */}
            <div className="table-container">
              <table className="hotness-table">
                <thead>
                  <tr>
                    <th>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        Theme
                        <span
                          className="column-info-icon"
                          onMouseEnter={() => setHoveredColumn('theme')}
                          onMouseLeave={() => setHoveredColumn(null)}
                        >
                          ℹ️
                        </span>
                        {hoveredColumn === 'theme' && (
                          <div className="column-info-tooltip">
                            <p>{columnDescriptions.theme.description}</p>
                            <p className="calculation">{columnDescriptions.theme.calculation}</p>
                          </div>
                        )}
                      </span>
                    </th>
                    <th>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        Hotness Score
                        <span
                          className="column-info-icon"
                          onMouseEnter={() => setHoveredColumn('hotness_score')}
                          onMouseLeave={() => setHoveredColumn(null)}
                        >
                          ℹ️
                        </span>
                        {hoveredColumn === 'hotness_score' && (
                          <div className="column-info-tooltip">
                            <p>{columnDescriptions.hotness_score.description}</p>
                            <p className="calculation">{columnDescriptions.hotness_score.calculation}</p>
                          </div>
                        )}
                      </span>
                    </th>
                    <th>
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
                            <p>{columnDescriptions.enps.description}</p>
                            <p className="calculation">{columnDescriptions.enps.calculation}</p>
                          </div>
                        )}
                      </span>
                    </th>
                    <th>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        Number of Comments
                        <span
                          className="column-info-icon"
                          onMouseEnter={() => setHoveredColumn('total_comments')}
                          onMouseLeave={() => setHoveredColumn(null)}
                        >
                          ℹ️
                        </span>
                        {hoveredColumn === 'total_comments' && (
                          <div className="column-info-tooltip">
                            <p>{columnDescriptions.total_comments.description}</p>
                            <p className="calculation">{columnDescriptions.total_comments.calculation}</p>
                          </div>
                        )}
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {topicHotness.length > 0 ? (
                    topicHotness.map((topic, index) => {
                      const isExpanded = expandedThemes.has(topic.base_theme);
                      const subThemes = subThemeData[topic.base_theme] || [];
                      const isLoadingSubThemes = loadingSubThemes.has(topic.base_theme);
                      
                      return (
                        <React.Fragment key={index}>
                          <tr 
                            style={{ cursor: 'pointer' }}
                            onClick={() => handleThemeClick(topic.base_theme)}
                            className={isExpanded ? 'expanded-row' : ''}
                          >
                        <td style={{ position: 'relative' }}>
                              <span style={{ marginRight: '0.5rem' }}>
                                {isExpanded ? '▼' : '▶'}
                              </span>
                          {topic.base_theme}
                          <span
                            className="theme-insight-icon"
                            onClick={(e) => handleThemeIconClick('base_theme', topic.base_theme, e)}
                            style={{
                              marginLeft: '0.5rem',
                              cursor: 'pointer',
                              fontSize: '0.875rem',
                              opacity: 0.7,
                              transition: 'opacity 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                            onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                          >
                            💡
                          </span>
                        </td>
                        <td>{topic.hotness_score}</td>
                        <td>{topic.enps_now}%</td>
                            <td>{topic.total_comments}</td>
                          </tr>
                          {isExpanded && (
                            <tr>
                              <td colSpan="4" style={{ padding: 0, borderTop: 'none' }}>
                                <div style={{ 
                                  padding: '1rem', 
                                  background: isDarkMode ? 'var(--bg-tertiary)' : '#f9fafb',
                                  borderLeft: '3px solid var(--accent-blue)'
                                }}>
                                  {isLoadingSubThemes ? (
                                    <div style={{ textAlign: 'center', padding: '1rem', color: chartColors.text }}>
                                      Loading sub-themes...
                                    </div>
                                  ) : subThemes.length > 0 ? (
                                    <table style={{ 
                                      width: '100%', 
                                      borderCollapse: 'collapse',
                                      fontSize: '0.875rem'
                                    }}>
                                      <thead>
                                        <tr style={{ 
                                          borderBottom: `2px solid ${chartColors.grid}`,
                                          textAlign: 'left'
                                        }}>
                                          <th style={{ padding: '0.75rem', fontWeight: 600, color: chartColors.text }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                              Sub Theme
                                              <span
                                                className="column-info-icon"
                                                onMouseEnter={() => setHoveredColumn('theme')}
                                                onMouseLeave={() => setHoveredColumn(null)}
                                                style={{ fontSize: '0.75rem' }}
                                              >
                                                ℹ️
                                              </span>
                                              {hoveredColumn === 'theme' && (
                                                <div className="column-info-tooltip">
                                                  <p>{columnDescriptions.theme.description}</p>
                                                  <p className="calculation">{columnDescriptions.theme.calculation}</p>
                                                </div>
                                              )}
                                            </span>
                                          </th>
                                          <th style={{ padding: '0.75rem', fontWeight: 600, color: chartColors.text }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                              Hotness Score
                                              <span
                                                className="column-info-icon"
                                                onMouseEnter={() => setHoveredColumn('hotness_score')}
                                                onMouseLeave={() => setHoveredColumn(null)}
                                                style={{ fontSize: '0.75rem' }}
                                              >
                                                ℹ️
                                              </span>
                                              {hoveredColumn === 'hotness_score' && (
                                                <div className="column-info-tooltip">
                                                  <p>{columnDescriptions.hotness_score.description}</p>
                                                  <p className="calculation">{columnDescriptions.hotness_score.calculation}</p>
                                                </div>
                                              )}
                                            </span>
                                          </th>
                                          <th style={{ padding: '0.75rem', fontWeight: 600, color: chartColors.text }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                              eNPS
                                              <span
                                                className="column-info-icon"
                                                onMouseEnter={() => setHoveredColumn('enps')}
                                                onMouseLeave={() => setHoveredColumn(null)}
                                                style={{ fontSize: '0.75rem' }}
                                              >
                                                ℹ️
                                              </span>
                                              {hoveredColumn === 'enps' && (
                                                <div className="column-info-tooltip">
                                                  <p>{columnDescriptions.enps.description}</p>
                                                  <p className="calculation">{columnDescriptions.enps.calculation}</p>
                                                </div>
                                              )}
                                            </span>
                                          </th>
                                          <th style={{ padding: '0.75rem', fontWeight: 600, color: chartColors.text }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                              Number of Comments
                                              <span
                                                className="column-info-icon"
                                                onMouseEnter={() => setHoveredColumn('total_comments')}
                                                onMouseLeave={() => setHoveredColumn(null)}
                                                style={{ fontSize: '0.75rem' }}
                                              >
                                                ℹ️
                                              </span>
                                              {hoveredColumn === 'total_comments' && (
                                                <div className="column-info-tooltip">
                                                  <p>{columnDescriptions.total_comments.description}</p>
                                                  <p className="calculation">{columnDescriptions.total_comments.calculation}</p>
                                                </div>
                                              )}
                                            </span>
                                          </th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {subThemes.map((subTheme, subIndex) => (
                                          <tr 
                                            key={subIndex}
                                            style={{ 
                                              borderBottom: `1px solid ${chartColors.grid}`,
                                              transition: 'background-color 0.2s'
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = isDarkMode ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)'}
                                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                          >
                                            <td style={{ padding: '0.75rem', color: chartColors.text, position: 'relative' }}>
                                              {subTheme.sub_theme}
                                              <span
                                                className="theme-insight-icon"
                                                onClick={(e) => handleThemeIconClick('sub_theme', subTheme.sub_theme, e)}
                                                style={{
                                                  marginLeft: '0.5rem',
                                                  cursor: 'pointer',
                                                  fontSize: '0.875rem',
                                                  opacity: 0.7,
                                                  transition: 'opacity 0.2s'
                                                }}
                                                onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                                                onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                                              >
                                                💡
                                              </span>
                                            </td>
                                            <td style={{ padding: '0.75rem', color: chartColors.text }}>
                                              {subTheme.hotness_score}
                                            </td>
                                            <td style={{ padding: '0.75rem', color: chartColors.text }}>
                                              {subTheme.enps_now}%
                                            </td>
                                            <td style={{ padding: '0.75rem', color: chartColors.text }}>
                                              {subTheme.total_comments}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  ) : (
                                    <div style={{ textAlign: 'center', padding: '1rem', color: chartColors.text }}>
                                      No sub-themes available
                                    </div>
                                  )}
                                </div>
                        </td>
                      </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="4" style={{ textAlign: 'center' }}>No data available</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
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

export default Dashboard;

