import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import './Layout.css';

function Layout() {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path ? 'active' : '';
  };

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="nav-container">
          <div className="nav-brand">
            <div className="logo-container">
              <h1>Corporate Culture Monitor</h1>
            </div>
          </div>
          <div className="nav-links">
            <Link to="/" className={isActive('/')}>
              Dashboard
            </Link>
            <Link to="/analysis" className={isActive('/analysis')}>
              Analysis
            </Link>
            <Link to="/benchmark" className={isActive('/benchmark')}>
              Benchmark
            </Link>
          </div>
          <div className="nav-actions">
            <ThemeToggle />
          </div>
        </div>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;

