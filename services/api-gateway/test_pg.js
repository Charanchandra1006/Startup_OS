require('dotenv').config({ path: '../../.env' });
const { Pool } = require('pg');

let dbUrl = process.env.DATABASE_URL;
if (dbUrl) {
  dbUrl = dbUrl.replace('postgresql+asyncpg://', 'postgresql://');
  if (dbUrl.includes('?')) {
    dbUrl = dbUrl.split('?')[0];
  }
}

console.log('Connecting to:', dbUrl.replace(/:[^:@]+@/, ':***@'));

const pool = new Pool({
  connectionString: dbUrl,
  ssl: { rejectUnauthorized: false }
});

pool.query('SELECT NOW()')
  .then(res => {
    console.log('✅ Connection successful:', res.rows);
    process.exit(0);
  })
  .catch(err => {
    console.error('❌ Connection failed:', err);
    process.exit(1);
  });
