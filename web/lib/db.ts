// Server-only: imported by server components and route handlers, never by "use client" files.
import { Pool } from "pg";

const globalForPool = globalThis as unknown as { pool?: Pool };

function pool() {
  if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is not set");
  // shortcut: TLS without CA pinning (Supabase's CA is not in Node's store); pin the CA before handling real customer data.
  let url = process.env.DATABASE_URL;
  // Serverless spins up many instances; Supabase's session pooler (5432) caps at 15 clients,
  // so on Vercel use its transaction pooler (6543), which is built for this.
  if (process.env.VERCEL) url = url.replace("pooler.supabase.com:5432", "pooler.supabase.com:6543");
  globalForPool.pool ??= new Pool({
    connectionString: url,
    ssl: { rejectUnauthorized: false },
    max: 1,
    idleTimeoutMillis: 5000,
  });
  return globalForPool.pool;
}

export async function query<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  return (await pool().query(sql, params)).rows as T[];
}
