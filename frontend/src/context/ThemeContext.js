import React, { createContext, useState, useContext, useEffect, useRef } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

// Get Sydney time
const getSydneyTime = () => {
  try {
    // Create a date object for Sydney timezone
    const sydneyTime = new Date().toLocaleString('en-US', {
      timeZone: 'Australia/Sydney',
      hour: 'numeric',
      hour12: false,
      minute: 'numeric',
      second: 'numeric'
    });
    
    // Extract hour from the formatted string
    const hour = parseInt(sydneyTime.split(':')[0], 10);
    return hour;
  } catch (error) {
    console.error('Error getting Sydney time:', error);
    // Fallback to local time
    return new Date().getHours();
  }
};

// Check if it's night time in Sydney (after 10 PM or before 6 AM)
const isNightTimeInSydney = () => {
  const hour = getSydneyTime();
  return hour >= 22 || hour < 6; // 10 PM to 6 AM
};

export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check if auto mode is enabled
    const autoMode = localStorage.getItem('themeAutoMode');
    const autoModeEnabled = autoMode ? JSON.parse(autoMode) : true; // Default to enabled
    
    if (autoModeEnabled) {
      // Use Sydney time to determine initial theme
      return isNightTimeInSydney();
    } else {
      // Use saved preference
      const saved = localStorage.getItem('darkMode');
      return saved ? JSON.parse(saved) : false;
    }
  });

  const [autoMode, setAutoMode] = useState(() => {
    const saved = localStorage.getItem('themeAutoMode');
    return saved ? JSON.parse(saved) : true; // Default to enabled
  });

  const intervalRef = useRef(null);

  // Function to update theme based on Sydney time
  const updateThemeFromSydneyTime = () => {
    if (autoMode) {
      const shouldBeDark = isNightTimeInSydney();
      setIsDarkMode(shouldBeDark);
    }
  };

  useEffect(() => {
    // Apply theme to document
    if (isDarkMode) {
      document.documentElement.classList.add('dark-mode');
    } else {
      document.documentElement.classList.remove('dark-mode');
    }
    
    // Save preference (only if auto mode is disabled)
    if (!autoMode) {
      localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    }
  }, [isDarkMode, autoMode]);

  // Set up interval to check Sydney time periodically
  useEffect(() => {
    if (autoMode) {
      // Check immediately
      updateThemeFromSydneyTime();
      
      // Then check every minute to catch time changes
      intervalRef.current = setInterval(() => {
        updateThemeFromSydneyTime();
      }, 60000); // Check every minute
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    } else {
      // Clear interval if auto mode is disabled
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [autoMode]);

  const toggleTheme = () => {
    // If auto mode is on, disable it first when user manually toggles
    if (autoMode) {
      setAutoMode(false);
      localStorage.setItem('themeAutoMode', JSON.stringify(false));
    }
    setIsDarkMode(prev => !prev);
  };

  const toggleAutoMode = () => {
    const newAutoMode = !autoMode;
    setAutoMode(newAutoMode);
    localStorage.setItem('themeAutoMode', JSON.stringify(newAutoMode));
    
    if (newAutoMode) {
      // If enabling auto mode, update theme based on Sydney time
      updateThemeFromSydneyTime();
    }
  };

  return (
    <ThemeContext.Provider value={{ 
      isDarkMode, 
      toggleTheme, 
      autoMode, 
      toggleAutoMode,
      sydneyHour: getSydneyTime()
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

