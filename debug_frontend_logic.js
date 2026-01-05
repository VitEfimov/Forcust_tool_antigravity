const axios = require('axios');

async function testFrontendLogic() {
    try {
        console.log("Fetching data from API...");
        // Use 127.0.0.1 to force IPv4
        const response = await axios.get('http://127.0.0.1:8000/market/history?limit=30');
        const data = response.data.history || [];
        console.log(`Fetched ${data.length} items.`);

        // Exact logic from Analytics.jsx
        const processed = data.map((item, index) => {
            try {
                const overview = item.data?.overview || [];
                // Check if date parsing works
                const rawDate = item.timestamp || item.date;
                const dateObj = new Date(rawDate);
                const date = dateObj.toLocaleDateString();

                if (date === "Invalid Date") {
                    console.error(`[Item ${index}] Invalid Date from: ${rawDate}`);
                }

                let uptrend = 0;
                let downtrend = 0;
                let highVol = 0;
                let lowVol = 0;
                let moderateVol = 0;

                if (!Array.isArray(overview)) {
                    console.error(`[Item ${index}] Overview is not an array:`, overview);
                    return null;
                }

                overview.forEach(stock => {
                    // Logic from Analytics.jsx
                    if (stock.regime === 'Uptrend') uptrend++;
                    if (stock.regime === 'Downtrend') downtrend++;

                    if (stock.risk_label === 'High Volatility') highVol++;
                    else if (stock.risk_label === 'Low Volatility') lowVol++;
                    else if (stock.risk_label === 'Moderate') moderateVol++;
                });

                return {
                    date,
                    fullDate: rawDate,
                    uptrend,
                    downtrend,
                    highVol,
                    lowVol,
                    moderateVol,
                    total: overview.length,
                    rawOverview: overview
                };
            } catch (e) {
                console.error(`[Item ${index}] process error:`, e);
                throw e;
            }
        }).reverse();

        console.log("Processing successful!");
        if (processed.length > 0) {
            // console.log("First processed item:", JSON.stringify(processed[0], null, 2));
            console.log("First item date:", processed[0].date);
        } else {
            console.log("Processed list is empty.");
        }

    } catch (err) {
        console.error("Frontend Logic Failed:", err.message);
        if (err.response) {
            console.error("Response data:", err.response.data);
        }
    }
}

testFrontendLogic();
