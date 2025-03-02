const express = require('express');
const mysql = require('mysql');
const cors = require('cors');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// MySQL Connection
const db = mysql.createConnection({
    host: "localhost",
    user: "root",
    password: "Ict@2022",
    database: "lab5"
});

db.connect(err => {
    if (err) {
        console.error("Database connection failed: " + err.stack);
        return;
    }
    console.log("Connected to MySQL database");
});

// Function to convert DMS to Decimal Degrees
function dmsToDecimal(dms) {
    if (!dms || dms.includes("nan")) return null;

    const regex = /(\d+)°(\d+)'([\d.]+)"([NSEW])/;
    const match = dms.match(regex);

    if (!match) return null;

    let degrees = parseFloat(match[1]);
    let minutes = parseFloat(match[2]);
    let seconds = parseFloat(match[3]);
    let direction = match[4];

    let decimal = degrees + minutes / 60 + seconds / 3600;

    if (direction === "S" || direction === "W") {
        decimal = -decimal; // South and West are negative
    }

    return decimal.toFixed(6); // Keep up to 6 decimal places
}

// API Endpoint to Fetch Well Data (Convert lat/long to decimal)
app.get('/wells', (req, res) => {
    const query = `SELECT * FROM oilwell_data WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND latitude != 'nan' AND longitude != 'nan'`;
    
    db.query(query, (err, results) => {
        if (err) {
            res.status(500).send("Error retrieving data");
        } else {
            // Replace "nan" with NULL or "N/A"
            const cleanedResults = results.map(well => {
                return Object.fromEntries(
                    Object.entries(well).map(([key, value]) =>
                        value === "nan" || value === null || value === "" ? [key, "N/A"] : [key, value]
                    )
                );
            });

            res.json(cleanedResults);
        }
    });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});

