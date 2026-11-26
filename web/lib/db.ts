// Server-only: imported by server components and route handlers, never by "use client" files.
import { Pool } from "pg";

const globalForPool = globalThis as unknown as { pool?: Pool };

function pool() {
  if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is not set");
  // shortcut: TLS without CA pinning (Supabase's CA is not in Node's store); pin the CA before handling real customer data.
  globalForPool.pool ??= new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    max: 3,
  });
  return globalForPool.pool;
}

export async function query<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  return (await pool().query(sql, params)).rows as T[];
}
