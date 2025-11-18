import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
} from 'recharts';
import { useTheme } from '../context/ThemeContext';
import config from '../config';
import './Benchmark.css';

function Benchmark() {
  const { isDarkMode } = useTheme();
  // Dimension: 'time', 'source', or 'language'
  const [dimension, setDimension] = useState('time');
  // Comparison type: 'year' or 'month' (only used when dimension is 'time')
  const [comparisonType, setComparisonType] = useState('year');
  
  // Year comparison defaults
  const currentYear = new Date().getFullYear();
  const previousYear = currentYear - 1;
  const [yearA, setYearA] = useState(currentYear.toString());
  const [yearB, setYearB] = useState(previousYear.toString());
  
  // Month comparison defaults
  const currentDate = new Date();
  const currentMonth = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}`;
  const previousMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
  const previousMonthStr = `${previousMonth.getFullYear()}-${String(previousMonth.getMonth() + 1).padStart(2, '0')}`;
  const [monthA, setMonthA] = useState(currentMonth);
  const [monthB, setMonthB] = useState(previousMonthStr);
  
  // Source and Language options
  const [sources, setSources] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [sourceA, setSourceA] = useState('');
  const [sourceB, setSourceB] = useState('');
  const [languageA, setLanguageA] = useState('');
  const [languageB, setLanguageB] = useState('');
  
  const [radarDataCount, setRadarDataCount] = useState(null);
  const [radarDataEnps, setRadarDataEnps] = useState(null);
  const [flowData, setFlowData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Function to apply square root scaling to comment volume data
  // This helps visualize data when there are extreme outliers
  const applySqrtScaling = (data, labelA, labelB) => {
    // Extract all values to find the maximum
    const allValues = [];
    data.forEach(item => {
      if (item[labelA] !== undefined) allValues.push(item[labelA]);
      if (item[labelB] !== undefined) allValues.push(item[labelB]);
    });
    
    const maxValue = Math.max(...allValues, 1); // Avoid division by zero
    
    // Apply square root scaling: sqrt(value / max) * 100
    // This compresses large values while maintaining relative relationships
    const scaledData = data.map(item => ({
      ...item,
      [`${labelA}_original`]: item[labelA], // Store original for tooltip
      [`${labelB}_original`]: item[labelB], // Store original for tooltip
      [labelA]: Math.sqrt((item[labelA] || 0) / maxValue) * 100,
      [labelB]: Math.sqrt((item[labelB] || 0) / maxValue) * 100,
    }));
    
    return {
      scaledData,
      maxValue,
      scaleType: 'sqrt'
    };
  };
  
  const chartColors = {
    monthA: isDarkMode ? '#64B5F6' : '#2196F3',
    monthB: isDarkMode ? '#81C784' : '#4CAF50',
    increase: isDarkMode ? '#81C784' : '#4CAF50',
    decrease: isDarkMode ? '#e57373' : '#f44336',
    grid: isDarkMode ? '#3a3a3a' : '#e0e0e0',
    text: isDarkMode ? '#b3b3b3' : '#757575'
  };

  // Load filter options on mount
  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const response = await axios.get(`${config.API_URL}/api/dashboard/filters/options`);
        setSources(response.data.sources || []);
        setLanguages(response.data.languages || []);
        // Set default values
        if (response.data.sources && response.data.sources.length >= 2) {
          setSourceA(response.data.sources[0]);
          setSourceB(response.data.sources[1]);
        }
        if (response.data.languages && response.data.languages.length >= 2) {
          setLanguageA(response.data.languages[0]);
          setLanguageB(response.data.languages[1]);
        }
      } catch (error) {
        console.error('Error fetching filter options:', error);
      }
    };
    fetchOptions();
    handleGenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = async () => {
    // Validate inputs based on dimension
    if (dimension === 'time') {
    if (comparisonType === 'year') {
      if (!yearA || !yearB) {
        setError('Please select both years');
        return;
      }
    } else {
      if (!monthA || !monthB) {
        setError('Please select both months');
          return;
        }
      }
    } else if (dimension === 'source') {
      if (!sourceA || !sourceB) {
        setError('Please select both sources');
        return;
      }
    } else if (dimension === 'language') {
      if (!languageA || !languageB) {
        setError('Please select both languages');
        return;
      }
    }

    setError('');
    setLoading(true);

    try {
      let radarCountResponse, radarEnpsResponse, flowResponse;
      
      if (dimension === 'time') {
        // Time-based comparison (existing logic)
      if (comparisonType === 'year') {
        [radarCountResponse, radarEnpsResponse, flowResponse] = await Promise.all([
          axios.post(`${config.API_URL}/api/benchmark/year-data`, {
            year_a: yearA,
            year_b: yearB,
            metric: 'count',
          }),
          axios.post(`${config.API_URL}/api/benchmark/year-data`, {
            year_a: yearA,
            year_b: yearB,
            metric: 'enps',
          }),
          axios.post(`${config.API_URL}/api/benchmark/year-flow`, {
            year_a: yearA,
            year_b: yearB,
          })
        ]);

        const themesCount = radarCountResponse.data.themes;
        const rawChartDataCount = themesCount.map((theme, index) => ({
          theme: theme,
          [radarCountResponse.data.year_a.label]: radarCountResponse.data.year_a.values[index],
          [radarCountResponse.data.year_b.label]: radarCountResponse.data.year_b.values[index],
        }));

        // Apply square root scaling to comment volume data
        const scalingResult = applySqrtScaling(
          rawChartDataCount,
          radarCountResponse.data.year_a.label,
          radarCountResponse.data.year_b.label
        );

        setRadarDataCount({
          data: scalingResult.scaledData,
          labelA: radarCountResponse.data.year_a.label,
          labelB: radarCountResponse.data.year_b.label,
          maxValue: scalingResult.maxValue,
          scaleType: scalingResult.scaleType,
        });

        const themesEnps = radarEnpsResponse.data.themes;
        const chartDataEnps = themesEnps.map((theme, index) => ({
          theme: theme,
          [radarEnpsResponse.data.year_a.label]: radarEnpsResponse.data.year_a.values[index],
          [radarEnpsResponse.data.year_b.label]: radarEnpsResponse.data.year_b.values[index],
        }));

        setRadarDataEnps({
          data: chartDataEnps,
          labelA: radarEnpsResponse.data.year_a.label,
          labelB: radarEnpsResponse.data.year_b.label,
        });
      } else {
        [radarCountResponse, radarEnpsResponse, flowResponse] = await Promise.all([
          axios.post(`${config.API_URL}/api/benchmark/radar-data`, {
            month_a: monthA,
            month_b: monthB,
            metric: 'count',
          }),
          axios.post(`${config.API_URL}/api/benchmark/radar-data`, {
            month_a: monthA,
            month_b: monthB,
            metric: 'enps',
          }),
          axios.post(`${config.API_URL}/api/benchmark/theme-flow`, {
            month_a: monthA,
            month_b: monthB,
          })
        ]);

        const themesCount = radarCountResponse.data.themes;
        const rawChartDataCount = themesCount.map((theme, index) => ({
          theme: theme,
          [radarCountResponse.data.month_a.label]: radarCountResponse.data.month_a.values[index],
          [radarCountResponse.data.month_b.label]: radarCountResponse.data.month_b.values[index],
        }));

        // Apply square root scaling to comment volume data
        const scalingResult = applySqrtScaling(
          rawChartDataCount,
          radarCountResponse.data.month_a.label,
          radarCountResponse.data.month_b.label
        );

        setRadarDataCount({
          data: scalingResult.scaledData,
          labelA: radarCountResponse.data.month_a.label,
          labelB: radarCountResponse.data.month_b.label,
          maxValue: scalingResult.maxValue,
          scaleType: scalingResult.scaleType,
        });

        const themesEnps = radarEnpsResponse.data.themes;
        const chartDataEnps = themesEnps.map((theme, index) => ({
          theme: theme,
          [radarEnpsResponse.data.month_a.label]: radarEnpsResponse.data.month_a.values[index],
          [radarEnpsResponse.data.month_b.label]: radarEnpsResponse.data.month_b.values[index],
        }));

        setRadarDataEnps({
          data: chartDataEnps,
          labelA: radarEnpsResponse.data.month_a.label,
          labelB: radarEnpsResponse.data.month_b.label,
          });
        }
      } else {
        // Dimension-based comparison (source or language)
        [radarCountResponse, radarEnpsResponse, flowResponse] = await Promise.all([
          axios.post(`${config.API_URL}/api/benchmark/dimension-data`, {
            dimension: dimension,
            value_a: dimension === 'source' ? sourceA : languageA,
            value_b: dimension === 'source' ? sourceB : languageB,
            metric: 'count',
          }),
          axios.post(`${config.API_URL}/api/benchmark/dimension-data`, {
            dimension: dimension,
            value_a: dimension === 'source' ? sourceA : languageA,
            value_b: dimension === 'source' ? sourceB : languageB,
            metric: 'enps',
          }),
          axios.post(`${config.API_URL}/api/benchmark/dimension-flow`, {
            dimension: dimension,
            value_a: dimension === 'source' ? sourceA : languageA,
            value_b: dimension === 'source' ? sourceB : languageB,
          })
        ]);

        const themesCount = radarCountResponse.data.themes;
        const rawChartDataCount = themesCount.map((theme, index) => ({
          theme: theme,
          [radarCountResponse.data.value_a.label]: radarCountResponse.data.value_a.values[index],
          [radarCountResponse.data.value_b.label]: radarCountResponse.data.value_b.values[index],
        }));

        // Apply square root scaling to comment volume data
        const scalingResult = applySqrtScaling(
          rawChartDataCount,
          radarCountResponse.data.value_a.label,
          radarCountResponse.data.value_b.label
        );

        setRadarDataCount({
          data: scalingResult.scaledData,
          labelA: radarCountResponse.data.value_a.label,
          labelB: radarCountResponse.data.value_b.label,
          maxValue: scalingResult.maxValue,
          scaleType: scalingResult.scaleType,
        });

        const themesEnps = radarEnpsResponse.data.themes;
        const chartDataEnps = themesEnps.map((theme, index) => ({
          theme: theme,
          [radarEnpsResponse.data.value_a.label]: radarEnpsResponse.data.value_a.values[index],
          [radarEnpsResponse.data.value_b.label]: radarEnpsResponse.data.value_b.values[index],
        }));

        setRadarDataEnps({
          data: chartDataEnps,
          labelA: radarEnpsResponse.data.value_a.label,
          labelB: radarEnpsResponse.data.value_b.label,
        });
      }
      
      setFlowData(flowResponse.data);
    } catch (err) {
      setError('Failed to generate benchmark data');
      console.error(err);
    }

    setLoading(false);
  };

  return (
    <div className="benchmark">
      <div className="page-header">
        <h2>Benchmark</h2>
        {/* <p>Compare themes across different time periods using radar visualization</p> */}
      </div>

      <div className="benchmark-controls card">
        <h3>Select Comparison Parameters</h3>
        <div className="control-grid">
          <div className="control-group">
            <label htmlFor="dimension">Comparison Dimension</label>
            <select
              id="dimension"
              className="select"
              value={dimension}
              onChange={(e) => setDimension(e.target.value)}
            >
              <option value="time">Time</option>
              <option value="source">Source</option>
              <option value="language">Language</option>
            </select>
          </div>

          {dimension === 'time' ? (
            <>
              <div className="control-group">
                <label htmlFor="comparison-type">Time Type</label>
                <select
                  id="comparison-type"
                  className="select"
                  value={comparisonType}
                  onChange={(e) => setComparisonType(e.target.value)}
                >
                  <option value="year">Year</option>
                  <option value="month">Month</option>
                </select>
              </div>

          {comparisonType === 'year' ? (
            <>
              <div className="control-group">
                <label htmlFor="year-a">Year A</label>
                <input
                  id="year-a"
                  type="number"
                  className="input"
                  value={yearA}
                  onChange={(e) => setYearA(e.target.value)}
                  min="2020"
                  max="2030"
                />
              </div>

              <div className="control-group">
                <label htmlFor="year-b">Year B</label>
                <input
                  id="year-b"
                  type="number"
                  className="input"
                  value={yearB}
                  onChange={(e) => setYearB(e.target.value)}
                  min="2020"
                  max="2030"
                />
              </div>
            </>
          ) : (
            <>
              <div className="control-group">
                <label htmlFor="month-a">Month A</label>
                <input
                  id="month-a"
                  type="month"
                  className="input"
                  value={monthA}
                  onChange={(e) => setMonthA(e.target.value)}
                />
              </div>

              <div className="control-group">
                <label htmlFor="month-b">Month B</label>
                <input
                  id="month-b"
                  type="month"
                  className="input"
                  value={monthB}
                  onChange={(e) => setMonthB(e.target.value)}
                />
                  </div>
                </>
              )}
            </>
          ) : dimension === 'source' ? (
            <>
              <div className="control-group">
                <label htmlFor="source-a">Source A</label>
                <select
                  id="source-a"
                  className="select"
                  value={sourceA}
                  onChange={(e) => setSourceA(e.target.value)}
                >
                  <option value="">Select Source</option>
                  {sources.map((source) => (
                    <option key={source} value={source}>
                      {source}
                    </option>
                  ))}
                </select>
              </div>

              <div className="control-group">
                <label htmlFor="source-b">Source B</label>
                <select
                  id="source-b"
                  className="select"
                  value={sourceB}
                  onChange={(e) => setSourceB(e.target.value)}
                >
                  <option value="">Select Source</option>
                  {sources.map((source) => (
                    <option key={source} value={source}>
                      {source}
                    </option>
                  ))}
                </select>
              </div>
            </>
          ) : (
            <>
              <div className="control-group">
                <label htmlFor="language-a">Language A</label>
                <select
                  id="language-a"
                  className="select"
                  value={languageA}
                  onChange={(e) => setLanguageA(e.target.value)}
                >
                  <option value="">Select Language</option>
                  {languages.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>

              <div className="control-group">
                <label htmlFor="language-b">Language B</label>
                <select
                  id="language-b"
                  className="select"
                  value={languageB}
                  onChange={(e) => setLanguageB(e.target.value)}
                >
                  <option value="">Select Language</option>
                  {languages.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div className="control-group">
            <label>&nbsp;</label>
            <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
              {loading ? 'Generating...' : 'Generate Comparison'}
            </button>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}
      </div>

      {radarDataCount && (
        <div className="radar-section card">
          <h3>Comment Count Comparison</h3>
          {radarDataCount.scaleType && (
            <p style={{ 
              fontSize: '12px', 
              color: chartColors.text, 
              marginBottom: '10px',
              fontStyle: 'italic'
            }}>
              Note: Data uses square root scaling to better visualize differences. Hover to see actual values.
            </p>
          )}
          <ResponsiveContainer width="100%" height={500}>
            <RadarChart data={radarDataCount.data}>
              <PolarGrid stroke={chartColors.grid} />
              <PolarAngleAxis 
                dataKey="theme" 
                tick={{ fill: chartColors.text, fontSize: 12 }}
              />
              <PolarRadiusAxis tick={{ fill: chartColors.text, fontSize: 10 }} />
              <Radar
                name={radarDataCount.labelA}
                dataKey={radarDataCount.labelA}
                stroke={chartColors.monthA}
                fill={chartColors.monthA}
                fillOpacity={0.3}
              />
              <Radar
                name={radarDataCount.labelB}
                dataKey={radarDataCount.labelB}
                stroke={chartColors.monthB}
                fill={chartColors.monthB}
                fillOpacity={0.3}
              />
              <Legend />
              <Tooltip 
                contentStyle={{
                  backgroundColor: isDarkMode ? '#1e1e1e' : '#ffffff',
                  border: `1px solid ${chartColors.grid}`,
                  borderRadius: '8px',
                }}
                formatter={(value, name, props) => {
                  // Show original value if available
                  const originalKey = `${name}_original`;
                  const originalValue = props.payload && props.payload[originalKey];
                  if (originalValue !== undefined && originalValue !== null) {
                    return [`${originalValue.toLocaleString()} (scaled: ${Number(value).toFixed(1)})`, name];
                  }
                  return [Number(value).toFixed(1), name];
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {radarDataEnps && (
        <div className="radar-section card">
          <h3>eNPS Score Comparison</h3>
          <ResponsiveContainer width="100%" height={500}>
            <RadarChart data={radarDataEnps.data}>
              <PolarGrid stroke={chartColors.grid} />
              <PolarAngleAxis 
                dataKey="theme" 
                tick={{ fill: chartColors.text, fontSize: 12 }}
              />
              <PolarRadiusAxis tick={{ fill: chartColors.text, fontSize: 10 }} />
              <Radar
                name={radarDataEnps.labelA}
                dataKey={radarDataEnps.labelA}
                stroke={chartColors.monthA}
                fill={chartColors.monthA}
                fillOpacity={0.3}
              />
              <Radar
                name={radarDataEnps.labelB}
                dataKey={radarDataEnps.labelB}
                stroke={chartColors.monthB}
                fill={chartColors.monthB}
                fillOpacity={0.3}
              />
              <Legend />
              <Tooltip 
                contentStyle={{
                  backgroundColor: isDarkMode ? '#1e1e1e' : '#ffffff',
                  border: `1px solid ${chartColors.grid}`,
                  borderRadius: '8px',
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {flowData && (
        <div className="flow-section card">
          <h3>Theme Flow: {dimension === 'time' 
            ? (comparisonType === 'year' ? `${flowData.year_a || flowData.month_a} → ${flowData.year_b || flowData.month_b}` : `${flowData.month_a} → ${flowData.month_b}`)
            : `${flowData.value_a} → ${flowData.value_b}`}
          </h3>
          <p className="section-description">
            Compare comment volume for each theme across the two selected {dimension === 'time' 
              ? (comparisonType === 'year' ? 'years' : 'months')
              : dimension === 'source' ? 'sources' : 'languages'}
          </p>
          <ResponsiveContainer width="100%" height={600}>
            <BarChart 
              data={flowData.data.slice(0, 15)} 
              layout="vertical"
              margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
            >
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke={chartColors.grid} 
                strokeOpacity={0.2}
                horizontal={false}
              />
              <XAxis 
                type="number"
                stroke={chartColors.text}
                tick={{ fill: chartColors.text, fontSize: 12 }}
                tickLine={{ stroke: chartColors.grid }}
                axisLine={{ stroke: chartColors.grid }}
              />
              <YAxis 
                type="category"
                dataKey="theme"
                stroke={chartColors.text}
                tick={{ fill: chartColors.text, fontSize: 12 }}
                tickLine={{ stroke: chartColors.grid }}
                axisLine={{ stroke: chartColors.grid }}
                width={90}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: isDarkMode ? '#1e1e1e' : '#ffffff',
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
                formatter={(value, name) => {
                  if (dimension === 'time') {
                  if (comparisonType === 'year') {
                    if (name === 'year_a') return [value, flowData.year_a];
                    if (name === 'year_b') return [value, flowData.year_b];
                  } else {
                    if (name === 'month_a') return [value, flowData.month_a];
                    if (name === 'month_b') return [value, flowData.month_b];
                    }
                  } else {
                    if (name === 'value_a') return [value, flowData.value_a];
                    if (name === 'value_b') return [value, flowData.value_b];
                  }
                  return value;
                }}
              />
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="square"
              />
              <Bar 
                dataKey={dimension === 'time' ? (comparisonType === 'year' ? 'year_a' : 'month_a') : 'value_a'} 
                fill={chartColors.monthA}
                name={dimension === 'time' ? (comparisonType === 'year' ? flowData.year_a : flowData.month_a) : flowData.value_a}
                radius={[0, 4, 4, 0]}
              />
              <Bar 
                dataKey={dimension === 'time' ? (comparisonType === 'year' ? 'year_b' : 'month_b') : 'value_b'} 
                fill={chartColors.monthB}
                name={dimension === 'time' ? (comparisonType === 'year' ? flowData.year_b : flowData.month_b) : flowData.value_b}
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
          
          {/* Flow indicators */}
          <div className="flow-indicators">
            <h4>Key Changes</h4>
            <div className="indicators-grid">
              {flowData.data
                .filter(item => Math.abs(item.change) > 0)
                .slice(0, 5)
                .map((item, index) => (
                  <div 
                    key={index} 
                    className={`indicator-item ${item.change > 0 ? 'increase' : 'decrease'}`}
                  >
                    <span className="theme-name">{item.theme}</span>
                    <span className="change-value">
                      {item.change > 0 ? '↑' : '↓'} {Math.abs(item.change)}
                    </span>
                    <span className="change-percent">
                      ({item.change_percent > 0 ? '+' : ''}{item.change_percent.toFixed(1)}%)
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* <div className="benchmark-info card">
        <h3>How to Use</h3>
        <ol>
          <li>Choose comparison dimension: <strong>Time</strong>, <strong>Source</strong>, or <strong>Language</strong></li>
          {dimension === 'time' ? (
            <>
              <li>Select time type: <strong>Year</strong> or <strong>Month</strong></li>
              <li>Select two different {comparisonType === 'year' ? 'years' : 'months'} to compare</li>
            </>
          ) : dimension === 'source' ? (
            <li>Select two different sources to compare</li>
          ) : (
            <li>Select two different languages to compare</li>
          )}
          <li>Click "Generate Comparison" to visualize both radar charts (Comment Count and eNPS Score)</li>
          <li>Each axis represents a different theme</li>
          <li>Compare the shapes to identify areas of change between the selected {dimension === 'time' 
            ? (comparisonType === 'year' ? 'years' : 'months')
            : dimension === 'source' ? 'sources' : 'languages'}</li>
        </ol>
      </div> */}
    </div>
  );
}

export default Benchmark;

