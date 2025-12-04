import React from 'react';

const OverviewTable = ({ data }) => {
    if (!data || data.length === 0) {
        return <p>No data available.</p>;
    }

    return (
        <div className="table-container" style={{ overflowX: 'auto' }}>
            <table className="overview-table">
                <thead>
                    <tr>
                        <th style={{ position: 'sticky', left: 0, zIndex: 1, backgroundColor: '#333' }}>Symbol</th>
                        <th>Date</th>
                        <th>Close</th>
                        <th>10d %</th>
                        <th>10d Price</th>
                        <th>100d %</th>
                        <th>100d Price</th>
                        <th>1yr %</th>
                        <th>1yr Price</th>
                        <th>1.5yr %</th>
                        <th>1.5yr Price</th>
                        <th>2yr %</th>
                        <th>2yr Price</th>
                    </tr>
                </thead>
                <tbody>
                    {data.map((item) => (
                        <tr key={item.symbol}>
                            <td className="symbol-cell" style={{ position: 'sticky', left: 0, zIndex: 1, backgroundColor: '#2a2a2a' }}>{item.symbol}</td>
                            <td>{item.date}</td>
                            <td>${item.today_close.toFixed(2)}</td>

                            <td className={item.forecast_10d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                {item.forecast_10d_pct ? `${item.forecast_10d_pct > 0 ? '+' : ''}${item.forecast_10d_pct.toFixed(2)}%` : 'N/A'}
                            </td>
                            <td>${item.forecast_10d_price ? item.forecast_10d_price.toFixed(2) : 'N/A'}</td>

                            <td className={item.forecast_100d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                {item.forecast_100d_pct ? `${item.forecast_100d_pct > 0 ? '+' : ''}${item.forecast_100d_pct.toFixed(2)}%` : 'N/A'}
                            </td>
                            <td>${item.forecast_100d_price ? item.forecast_100d_price.toFixed(2) : 'N/A'}</td>

                            <td className={item.forecast_365d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                {item.forecast_365d_pct ? `${item.forecast_365d_pct > 0 ? '+' : ''}${item.forecast_365d_pct.toFixed(2)}%` : 'N/A'}
                            </td>
                            <td>${item.forecast_365d_price ? item.forecast_365d_price.toFixed(2) : 'N/A'}</td>

                            <td className={item.forecast_547d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                {item.forecast_547d_pct ? `${item.forecast_547d_pct > 0 ? '+' : ''}${item.forecast_547d_pct.toFixed(2)}%` : 'N/A'}
                            </td>
                            <td>${item.forecast_547d_price ? item.forecast_547d_price.toFixed(2) : 'N/A'}</td>

                            <td className={item.forecast_730d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                {item.forecast_730d_pct ? `${item.forecast_730d_pct > 0 ? '+' : ''}${item.forecast_730d_pct.toFixed(2)}%` : 'N/A'}
                            </td>
                            <td>${item.forecast_730d_price ? item.forecast_730d_price.toFixed(2) : 'N/A'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default OverviewTable;
