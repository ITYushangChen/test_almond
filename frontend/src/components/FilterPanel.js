import React, { useState, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import './FilterPanel.css';

function FilterPanel({ onFilterChange }) {
  const [options, setOptions] = useState({
    base_themes: [],
    sub_themes: [],
    languages: [],
    sources: [],
    theme_mapping: {}, // Mapping of base_theme to sub_themes
    date_range: null, // Actual date range from database
  });
  const [selectedFilters, setSelectedFilters] = useState({
    base_themes: [],
    sub_themes: [],
    languages: [],
    sources: [],
    start_date: '',
    end_date: '',
  });
  const [dateRange, setDateRange] = useState({
    startYear: '',
    startMonth: '',
    endYear: '',
    endMonth: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchFilterOptions();
  }, []);

  const fetchFilterOptions = async () => {
    try {
      const response = await axios.get(`${config.API_URL}/api/dashboard/filters/options`);
      setOptions(response.data);
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  };

  // Generate year options based on actual date range from database
  const getYearOptions = () => {
    if (!options.date_range) {
      // Fallback: last 5 years to next year if no date range available
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let i = currentYear - 5; i <= currentYear + 1; i++) {
        years.push(i);
      }
      return years;
    }

    const { min_year, max_year } = options.date_range;
    const years = [];
    for (let i = min_year; i <= max_year; i++) {
      years.push(i);
    }
    return years;
  };

  // Generate month options based on selected year and date range
  const getMonthOptions = (year, isStartDate = true) => {
    const allMonths = [
      { value: '01', label: 'January', num: 1 },
      { value: '02', label: 'February', num: 2 },
      { value: '03', label: 'March', num: 3 },
      { value: '04', label: 'April', num: 4 },
      { value: '05', label: 'May', num: 5 },
      { value: '06', label: 'June', num: 6 },
      { value: '07', label: 'July', num: 7 },
      { value: '08', label: 'August', num: 8 },
      { value: '09', label: 'September', num: 9 },
      { value: '10', label: 'October', num: 10 },
      { value: '11', label: 'November', num: 11 },
      { value: '12', label: 'December', num: 12 },
    ];

    if (!options.date_range || !year) {
      return allMonths.map(({ value, label }) => ({ value, label }));
    }

    const { min_year, min_month, max_year, max_month } = options.date_range;
    
    // Filter months based on year and date range
    return allMonths
      .filter(({ num }) => {
        if (isStartDate) {
          // For start date: if year is min_year, only include months >= min_month
          if (year === min_year && num < min_month) return false;
          // If year is max_year, only include months <= max_month
          if (year === max_year && num > max_month) return false;
        } else {
          // For end date: if year is min_year, only include months >= min_month
          if (year === min_year && num < min_month) return false;
          // If year is max_year, only include months <= max_month
          if (year === max_year && num > max_month) return false;
        }
        return true;
      })
      .map(({ value, label }) => ({ value, label }));
  };

  // Helper function to get available sub_themes for given base_themes
  const getAvailableSubThemesForBaseThemes = (baseThemes) => {
    if (baseThemes.length === 0) {
      return options.sub_themes;
    }
    
    const availableSubThemes = new Set();
    baseThemes.forEach(baseTheme => {
      const subThemes = options.theme_mapping[baseTheme] || [];
      subThemes.forEach(subTheme => availableSubThemes.add(subTheme));
    });
    
    return Array.from(availableSubThemes).sort();
  };

  // Get available sub_themes based on selected base_themes
  const getAvailableSubThemes = () => {
    return getAvailableSubThemesForBaseThemes(selectedFilters.base_themes);
  };

  const handleMultiSelectChange = (field, value) => {
    const current = selectedFilters[field];
    const updated = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    
    let newFilters = { ...selectedFilters, [field]: updated };
    
    // If base_themes changed, filter sub_themes to only include those under selected base_themes
    if (field === 'base_themes') {
      const availableSubThemes = getAvailableSubThemesForBaseThemes(updated);
      // Remove any selected sub_themes that are not in the available list
      const filteredSubThemes = selectedFilters.sub_themes.filter(
        subTheme => availableSubThemes.includes(subTheme)
      );
      newFilters = { ...newFilters, sub_themes: filteredSubThemes };
    }
    
    setSelectedFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleYearMonthChange = (field, value) => {
    let newDateRange = { ...dateRange, [field]: value };
    
    // If year changed, check if current month is still valid
    if (field === 'startYear' && newDateRange.startYear && newDateRange.startMonth) {
      const availableMonths = getMonthOptions(parseInt(newDateRange.startYear), true);
      const isMonthValid = availableMonths.some(m => m.value === newDateRange.startMonth);
      if (!isMonthValid) {
        newDateRange.startMonth = ''; // Clear invalid month
      }
    }
    
    if (field === 'endYear' && newDateRange.endYear && newDateRange.endMonth) {
      const availableMonths = getMonthOptions(parseInt(newDateRange.endYear), false);
      const isMonthValid = availableMonths.some(m => m.value === newDateRange.endMonth);
      if (!isMonthValid) {
        newDateRange.endMonth = ''; // Clear invalid month
      }
    }
    
    setDateRange(newDateRange);

    // Convert year-month to date format for API
    let startDate = '';
    let endDate = '';

    if (newDateRange.startYear && newDateRange.startMonth) {
      startDate = `${newDateRange.startYear}-${newDateRange.startMonth}-01`;
    }

    if (newDateRange.endYear && newDateRange.endMonth) {
      // Get last day of the month
      const year = parseInt(newDateRange.endYear);
      const month = parseInt(newDateRange.endMonth);
      const lastDay = new Date(year, month, 0).getDate();
      endDate = `${newDateRange.endYear}-${newDateRange.endMonth}-${lastDay.toString().padStart(2, '0')}`;
    }

    const newFilters = {
      ...selectedFilters,
      start_date: startDate,
      end_date: endDate,
    };
    setSelectedFilters(newFilters);
    onFilterChange(newFilters);
  };

  const clearFilters = () => {
    const emptyFilters = {
      base_themes: [],
      sub_themes: [],
      languages: [],
      sources: [],
      start_date: '',
      end_date: '',
    };
    const emptyDateRange = {
      startYear: '',
      startMonth: '',
      endYear: '',
      endMonth: '',
    };
    setSelectedFilters(emptyFilters);
    setDateRange(emptyDateRange);
    onFilterChange(emptyFilters);
  };

  const activeFilterCount = 
    selectedFilters.base_themes.length +
    selectedFilters.sub_themes.length +
    selectedFilters.languages.length +
    selectedFilters.sources.length +
    (selectedFilters.start_date ? 1 : 0) +
    (selectedFilters.end_date ? 1 : 0);

  return (
    <div className="filter-panel card">
      <div className="filter-header">
        <button
          className="filter-toggle btn btn-primary"
          onClick={() => setShowFilters(!showFilters)}
        >
          🔍 Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
        </button>
        {activeFilterCount > 0 && (
          <button className="btn btn-secondary" onClick={clearFilters}>
            Clear All
          </button>
        )}
      </div>

      {showFilters && (
        <div className="filter-content">
          <div className="filter-group">
            <label>Base Themes</label>
            <div className="checkbox-group">
              {options.base_themes.map((theme) => (
                <label key={theme} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedFilters.base_themes.includes(theme)}
                    onChange={() => handleMultiSelectChange('base_themes', theme)}
                  />
                  <span>{theme}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label>Sub Themes</label>
            {selectedFilters.base_themes.length === 0 && (
              <div style={{ 
                padding: '0.75rem', 
                marginBottom: '0.5rem', 
                fontSize: '0.875rem', 
                color: 'var(--text-tertiary)',
                fontStyle: 'italic',
                background: 'var(--bg-tertiary)',
                borderRadius: '0.5rem'
              }}>
                Select base themes first to see related sub themes
              </div>
            )}
            <div className="checkbox-group">
              {getAvailableSubThemes().map((theme) => (
                <label key={theme} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedFilters.sub_themes.includes(theme)}
                    onChange={() => handleMultiSelectChange('sub_themes', theme)}
                  />
                  <span>{theme}</span>
                </label>
              ))}
              {getAvailableSubThemes().length === 0 && selectedFilters.base_themes.length > 0 && (
                <div style={{ 
                  padding: '1rem', 
                  textAlign: 'center', 
                  color: 'var(--text-tertiary)',
                  fontSize: '0.875rem'
                }}>
                  No sub themes available for selected base themes
                </div>
              )}
            </div>
          </div>

          <div className="filter-group">
            <label>Languages</label>
            <div className="checkbox-group">
              {options.languages.map((lang) => (
                <label key={lang} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedFilters.languages.includes(lang)}
                    onChange={() => handleMultiSelectChange('languages', lang)}
                  />
                  <span>{lang}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <label>Source</label>
            <div className="checkbox-group">
              {options.sources.map((source) => (
                <label key={source} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedFilters.sources.includes(source)}
                    onChange={() => handleMultiSelectChange('sources', source)}
                  />
                  <span>{source}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="filter-group date-range-group">
            <label>Date Range</label>
            <div className="date-range-selectors">
              <div className="year-month-selector">
                <label className="selector-label">From</label>
                <div className="select-wrapper">
                  <select
                    className="select-input"
                    value={dateRange.startYear}
                    onChange={(e) => handleYearMonthChange('startYear', e.target.value)}
                  >
                    <option value="">Year</option>
                    {getYearOptions().map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </select>
                  <select
                    className="select-input"
                    value={dateRange.startMonth}
                    onChange={(e) => handleYearMonthChange('startMonth', e.target.value)}
                    disabled={!dateRange.startYear}
                  >
                    <option value="">Month</option>
                    {getMonthOptions(parseInt(dateRange.startYear), true).map((month) => (
                      <option key={month.value} value={month.value}>
                        {month.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="year-month-selector">
                <label className="selector-label">To</label>
                <div className="select-wrapper">
                  <select
                    className="select-input"
                    value={dateRange.endYear}
                    onChange={(e) => handleYearMonthChange('endYear', e.target.value)}
                  >
                    <option value="">Year</option>
                    {getYearOptions().map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </select>
                  <select
                    className="select-input"
                    value={dateRange.endMonth}
                    onChange={(e) => handleYearMonthChange('endMonth', e.target.value)}
                    disabled={!dateRange.endYear}
                  >
                    <option value="">Month</option>
                    {getMonthOptions(parseInt(dateRange.endYear), false).map((month) => (
                      <option key={month.value} value={month.value}>
                        {month.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FilterPanel;

