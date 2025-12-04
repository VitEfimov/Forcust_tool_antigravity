import React, { useState } from 'react'
import Dashboard from './components/Dashboard';
import Indices from './components/Indices';
import Archive from './components/Archive';
import MarketOverview from './components/MarketOverview';
import ModelStatus from './components/ModelStatus';
import './App.css';

function App() {
  const [view, setView] = useState('dashboard');

  return (
    <div className="App">
      <div className="navbar">
        <a href="#" onClick={() => setView('dashboard')}>Dashboard</a>
        <a href="#" onClick={() => setView('indices')}>Indices</a>
        <a href="#" onClick={() => setView('archive')}>Archive</a>
        <a href="#" onClick={() => setView('overview')}>Market Overview</a>
        <a href="#" onClick={() => setView('models')}>System Status</a>
      </div>

      <div className="content">
        {view === 'dashboard' && <Dashboard />}
        {view === 'indices' && <Indices />}
        {view === 'archive' && <Archive />}
        {view === 'overview' && <MarketOverview />}
        {view === 'models' && <ModelStatus />}
      </div>
    </div>
  );
}

export default App
