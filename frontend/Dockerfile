FROM node:24-bookworm-slim AS deps

WORKDIR /app
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
RUN corepack enable \
    && corepack prepare pnpm@11.2.2 --activate \
    && pnpm config set registry https://registry.npmmirror.com

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:24-bookworm-slim AS builder

WORKDIR /app
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com \
    NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
RUN corepack enable \
    && corepack prepare pnpm@11.2.2 --activate \
    && pnpm config set registry https://registry.npmmirror.com

COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN pnpm build

FROM node:24-bookworm-slim AS runner

WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
