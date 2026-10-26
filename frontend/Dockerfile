FROM node:20-alpine

WORKDIR /app

# Enable yarn & pnpm via corepack, and install bun
RUN corepack enable && npm install -g bun

# Copy package.json and whichever lockfile exists
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* bun.lockb* bun.lock* ./

# Auto-detect lockfile and install dependencies
RUN if [ -f yarn.lock ]; then yarn install; \
    elif [ -f pnpm-lock.yaml ]; then pnpm install; \
    elif [ -f bun.lockb ] || [ -f bun.lock ]; then bun install; \
    else npm install; \
    fi

COPY . .

EXPOSE 3000

# Auto-detect lockfile and run Next.js dev server
CMD ["sh", "-c", "if [ -f yarn.lock ]; then yarn dev; elif [ -f pnpm-lock.yaml ]; then pnpm dev; elif [ -f bun.lockb ] || [ -f bun.lock ]; then bun dev; else npm run dev; fi"]