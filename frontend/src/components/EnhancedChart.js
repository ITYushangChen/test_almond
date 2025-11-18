import React from 'react';
import { useTheme } from '../context/ThemeContext';

/**
 * Enhanced Chart wrapper that provides theme-aware styling for Recharts
 */
function EnhancedChart({ children }) {
  const { isDarkMode } = useTheme();

  // Define theme-specific colors
  const chartTheme = {
    grid: isDarkMode ? '#334155' : '#e5e7eb',
    text: isDarkMode ? '#94a3b8' : '#6b7280',
    tooltip: {
      bg: isDarkMode ? '#1e293b' : '#ffffff',
      text: isDarkMode ? '#f1f5f9' : '#1f2937',
      border: isDarkMode ? '#475569' : '#e5e7eb'
    }
  };

  // Clone children and inject theme props
  const enhancedChildren = React.Children.map(children, child => {
    if (!React.isValidElement(child)) return child;

    // Safely access children
    const childChildren = child.props?.children;
    if (!childChildren) {
      return child;
    }

    // Recursively enhance children
    const enhancedGrandChildren = React.Children.map(childChildren, grandChild => {
      if (!React.isValidElement(grandChild)) return grandChild;

      const componentName = grandChild.type?.displayName || grandChild.type?.name || '';

      // Enhance CartesianGrid
      if (componentName === 'CartesianGrid' || grandChild.type === 'CartesianGrid') {
        return React.cloneElement(grandChild, {
          stroke: chartTheme.grid,
          strokeOpacity: 0.3,
          ...grandChild.props
        });
      }

      // Enhance XAxis and YAxis
      if (componentName === 'XAxis' || componentName === 'YAxis') {
        return React.cloneElement(grandChild, {
          stroke: chartTheme.text,
          tick: { fill: chartTheme.text, fontSize: 12 },
          ...grandChild.props
        });
      }

      // Enhance Tooltip
      if (componentName === 'Tooltip') {
        return React.cloneElement(grandChild, {
          contentStyle: {
            backgroundColor: chartTheme.tooltip.bg,
            border: `1px solid ${chartTheme.tooltip.border}`,
            borderRadius: '8px',
            boxShadow: isDarkMode 
              ? '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
              : '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            ...grandChild.props.contentStyle
          },
          labelStyle: {
            color: chartTheme.tooltip.text,
            fontWeight: 600,
            ...grandChild.props.labelStyle
          },
          itemStyle: {
            color: chartTheme.tooltip.text,
            ...grandChild.props.itemStyle
          },
          ...grandChild.props
        });
      }

      // Enhance Legend
      if (componentName === 'Legend') {
        return React.cloneElement(grandChild, {
          wrapperStyle: {
            color: chartTheme.text,
            ...grandChild.props.wrapperStyle
          },
          ...grandChild.props
        });
      }

      return grandChild;
    });

    return React.cloneElement(child, {}, enhancedGrandChildren);
  });

  return <>{enhancedChildren}</>;
}

export default EnhancedChart;

