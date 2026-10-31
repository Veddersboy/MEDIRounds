import { betterAuth } from "better-auth";
import { Pool } from "pg";

// Reuse one pool across dev hot reloads instead of opening a new one per reload.
// a pg pool is a type of middleware that establishes a client-server connection
const globalForPg = globalThis as unknown as { authPool?: Pool };
const pool =
  globalForPg.authPool ?? new Pool({ connectionString: process.env.DATABASE_URL });
if (process.env.NODE_ENV !== "production") globalForPg.authPool = pool;

export const auth = betterAuth({
  database: pool,
  emailAndPassword: {
    enabled: true,
  },
});