import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import './ThemeToggle.css';

function ThemeToggle() {
  const { isDarkMode, toggleTheme, autoMode, toggleAutoMode, sydneyHour } = useTheme();
  const [showMenu, setShowMenu] = useState(false);

  const handleToggle = (e) => {
    // If right-click or long-press, show menu instead
    if (e.type === 'contextmenu' || (e.type === 'mousedown' && e.button === 2)) {
      e.preventDefault();
      setShowMenu(true);
      return;
    }
    toggleTheme();
  };

  const handleMenuClick = (e) => {
    e.stopPropagation();
  };

  const handleAutoModeToggle = (e) => {
    e.stopPropagation();
    toggleAutoMode();
  };

  // Format Sydney time for display
  const formatSydneyTime = () => {
    try {
      const sydneyTime = new Date().toLocaleString('en-US', {
        timeZone: 'Australia/Sydney',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
      return sydneyTime;
    } catch (error) {
      return `${sydneyHour}:00`;
    }
  };

  return (
    <div className="theme-toggle-container">
    <button 
      className="theme-toggle" 
        onClick={handleToggle}
        onContextMenu={(e) => {
          e.preventDefault();
          setShowMenu(true);
        }}
      aria-label="Toggle theme"
        title={`${isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'} (Right-click for options)`}
    >
      <div className={`toggle-track ${isDarkMode ? 'active' : ''}`}>
        <div className="toggle-thumb">
          {isDarkMode ? '🌙' : '☀️'}
        </div>
      </div>
    </button>
      
      {showMenu && (
        <>
          <div 
            className="theme-menu-overlay"
            onClick={() => setShowMenu(false)}
          />
          <div className="theme-menu" onClick={handleMenuClick}>
            <div className="theme-menu-header">
              <h4>Theme Settings</h4>
              <button 
                className="theme-menu-close"
                onClick={() => setShowMenu(false)}
                aria-label="Close menu"
              >
                ×
              </button>
            </div>
            <div className="theme-menu-content">
              <div className="theme-menu-item">
                <label className="theme-menu-label">
                  <input
                    type="checkbox"
                    checked={autoMode}
                    onChange={handleAutoModeToggle}
                  />
                  <span>Auto mode (Sydney time)</span>
                </label>
                <div className="theme-menu-description">
                  {autoMode 
                    ? `Automatically switches to dark mode after 10 PM Sydney time (Currently: ${formatSydneyTime()})`
                    : 'Manually control theme'}
                </div>
              </div>
              {!autoMode && (
                <div className="theme-menu-item">
                  <button 
                    className="theme-menu-button"
                    onClick={() => {
                      toggleTheme();
                      setShowMenu(false);
                    }}
                  >
                    {isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                  </button>
                </div>
              )}
              {autoMode && (
                <div className="theme-menu-info">
                  <div className="theme-menu-status">
                    Current Sydney time: <strong>{formatSydneyTime()}</strong>
                  </div>
                  <div className="theme-menu-status">
                    Current mode: <strong>{isDarkMode ? 'Dark' : 'Light'}</strong>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ThemeToggle;

