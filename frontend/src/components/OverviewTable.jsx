import React from 'react';

const OverviewTable = ({ data }) => {
    if (!data || data.length === 0) {
        return <p>No data available.</p>;
    }

    return (
        <div className="table-container" style={{ overflowX: 'auto' }}>
            <table className="overview-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '2px solid #444' }}>
                        <th style={{ padding: '0.8rem', textAlign: 'left' }}>Symbol</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>Price</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>Change</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>Change %</th>
                        <th style={{ padding: '0.8rem', textAlign: 'center' }}>Signal</th>
                        <th style={{ padding: '0.8rem', textAlign: 'center' }}>Trend</th>
                        <th style={{ padding: '0.8rem', textAlign: 'center' }}>Risk</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right' }} title="Base Horizon">10d</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right', fontStyle: 'italic', color: '#aaa' }} title="Derived Horizon">30d*</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right' }} title="Base Horizon">100d</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right', fontStyle: 'italic', color: '#aaa' }} title="Derived Horizon">200d*</th>
                        <th style={{ padding: '0.8rem', textAlign: 'right', fontStyle: 'italic', color: '#aaa' }} title="Derived Horizon">365d*</th>
                    </tr>
                </thead>
                <tbody>
                    {data.map((item) => (
                        <tr key={item.symbol} style={{ borderBottom: '1px solid #2a2a2a' }}>
                            <td style={{ padding: '0.8rem', fontWeight: 'bold' }}>{item.symbol}</td>
                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                ${item.price?.toFixed(2)}
                            </td>
                            <td style={{
                                padding: '0.8rem',
                                textAlign: 'right',
                                color: item.change > 0 ? '#66ff66' : item.change < 0 ? '#ff6666' : '#888'
                            }}>
                                {item.change > 0 ? '+' : ''}{item.change?.toFixed(2)}
                            </td>
                            <td style={{
                                padding: '0.8rem',
                                textAlign: 'right',
                                color: item.change_pct > 0 ? '#66ff66' : item.change_pct < 0 ? '#ff6666' : '#888'
                            }}>
                                {item.change_pct > 0 ? '+' : ''}{item.change_pct?.toFixed(2)}%
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                <span style={{
                                    padding: '0.3rem 0.6rem',
                                    borderRadius: '12px',
                                    fontSize: '0.8rem',
                                    background: item.signal === 'bullish' ? '#1a4d1a' :
                                        item.signal === 'bearish' ? '#4d1a1a' : '#333',
                                    color: item.signal === 'bullish' ? '#66ff66' :
                                        item.signal === 'bearish' ? '#ff6666' : '#888'
                                }}>
                                    {item.signal || 'neutral'}
                                </span>
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'center', fontWeight: 'bold', color: item.trend_label === 'Uptrend' ? '#66ff66' : item.trend_label === 'Downtrend' ? '#ff6666' : '#aaa' }}>
                                {item.trend_label}
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'center', color: '#ccc' }}>
                                {item.risk_label}
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                {item.forecast_10d_pct != null ? `${item.forecast_10d_pct > 0 ? '+' : ''}${item.forecast_10d_pct.toFixed(2)}%` : '-'}
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                {item.forecast_30d_pct != null ? `${item.forecast_30d_pct > 0 ? '+' : ''}${item.forecast_30d_pct.toFixed(2)}%` : '-'}
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                {item.forecast_100d_pct != null ? `${item.forecast_100d_pct > 0 ? '+' : ''}${item.forecast_100d_pct.toFixed(2)}%` : '-'}
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                {item.forecast_200d_pct != null ? `${item.forecast_200d_pct > 0 ? '+' : ''}${item.forecast_200d_pct.toFixed(2)}%` : '-'}
                            </td>
                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                {item.forecast_365d_pct != null ? `${item.forecast_365d_pct > 0 ? '+' : ''}${item.forecast_365d_pct.toFixed(2)}%` : '-'}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default OverviewTable;
