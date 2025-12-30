import React, { useState } from 'react';
import { cheatsheets } from '../data/cheatsheets';
import '../App.css'; // Ensure we can reuse styles or add new ones

const Cheatsheets = () => {
    // Default to the first key in the cheatsheets object (e.g. Java)
    const topics = Object.keys(cheatsheets);
    const [activeTopic, setActiveTopic] = useState(topics[0] || '');
    const [searchQuery, setSearchQuery] = useState('');

    const activeData = cheatsheets[activeTopic] || [];

    // Filter based on search query
    const filteredData = activeData.filter(item =>
        item.topic.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.code.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="cheatsheets-container">
            <div className="cheatsheets-sidebar">
                <h3>Topics</h3>
                <ul className="topic-list">
                    {topics.map(topic => (
                        <li
                            key={topic}
                            className={activeTopic === topic ? 'active' : ''}
                            onClick={() => setActiveTopic(topic)}
                        >
                            {topic}
                        </li>
                    ))}
                </ul>
            </div>

            <div className="cheatsheets-content">
                <div className="cheatsheets-header">
                    <h2>{activeTopic} Cheatsheet</h2>
                    <input
                        type="text"
                        placeholder="Search topics..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="cheatsheet-search"
                    />
                </div>

                <div className="cheatsheets-grid">
                    {filteredData.map((item, index) => (
                        <div key={index} className="cheatsheet-card">
                            <div className="card-header">{item.topic}</div>
                            <pre className="card-code">
                                <code>{item.code}</code>
                            </pre>
                        </div>
                    ))}

                    {filteredData.length === 0 && (
                        <div className="no-results">No results found for "{searchQuery}"</div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Cheatsheets;
