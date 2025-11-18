import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Dashboard from './pages/Dashboard';
import Analysis from './pages/Analysis';
import Benchmark from './pages/Benchmark';
import Layout from './components/Layout';
import './styles/theme.css';

function App() {
  return (
    <ThemeProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="analysis" element={<Analysis />} />
            <Route path="benchmark" element={<Benchmark />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;

